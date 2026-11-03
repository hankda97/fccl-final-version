from pathlib import Path

from streamlit.testing.v1 import AppTest

from fccl_testline.generation import SCENARIOS


ROOT=Path(__file__).resolve().parents[1]


def text(app):
    groups=(app.markdown,app.caption,app.info,app.warning,app.success,app.header,app.subheader)
    values=[str(x.value) for g in groups for x in g]
    values.extend(f"{x.label} {x.value} {x.delta}" for x in app.metric)
    return "\n".join(values)


def new_app():
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=45).run()
    assert not app.exception
    return app


def test_formal_home_runs_ticks_and_shows_predictions_without_legacy_modes() -> None:
    app=new_app(); body=text(app)
    assert "Synthetic v3 本機模擬" in body and "FCCL-DEMO-001" in body
    assert "模式 A" not in body and "模式 C" not in body and "Mock" not in body and "SHAP" not in body
    assert len(app.number_input)==10 and not app.slider
    advance=next(b for b in app.button if b.label=="前進 12 點（60 秒）")
    advance.click().run(); advance=next(b for b in app.button if b.label=="前進 12 點（60 秒）"); advance.click().run()
    assert not app.exception
    assert app.session_state.testline_engine.simulator.clock.sequence==24
    assert len(app.session_state.testline_engine.tables["quality_predictions"])==4
    assert all(label in text(app) for label in ("抗剝離度","尺寸安定性 MD","尺寸安定性 TD","耐熱度"))
    assert len(app.get("vega_lite_chart"))==3


def test_all_scenarios_can_start_and_update_without_ui_error() -> None:
    app=new_app()
    for scenario in SCENARIOS:
        app.selectbox[0].set_value(scenario).run()
        next(b for b in app.button if b.label=="新 Run").click().run()
        next(b for b in app.button if b.label=="前進 1 點（5 秒）").click().run()
        assert not app.exception
        assert app.session_state.testline_engine.simulator.scenario==scenario
        assert app.session_state.testline_engine.simulator.clock.sequence==1


def test_spc_navigation_shows_all_five_charts_and_alarm_center() -> None:
    app=new_app(); next(b for b in app.button if b.label=="前進 12 點（60 秒）").click().run()
    app.button(key="testline_nav_SPC 詳細監控").click().run()
    assert not app.exception and len(app.get("vega_lite_chart"))==5
    body=text(app)
    for title in ("乾膠厚度 X-bar／R","熟化溫度 I-MR","排風量 EWMA","線速 I-MR","壓合壓力 I-MR"): assert title in body
    assert "AI Alarm 事件群" in body


def test_whatif_return_only_prefills_candidate_and_never_creates_live_event() -> None:
    app=new_app()
    for _ in range(2): next(b for b in app.button if b.label=="前進 12 點（60 秒）").click().run()
    engine=app.session_state.testline_engine; assert len(engine.simulator.events)==0
    app.button(key="testline_nav_What-if／Heatmap").click().run(); assert not app.exception
    next(b for b in app.button if b.label=="計算四目標比較").click().run(); assert not app.exception
    assert app.session_state.whatif_result["non_causal"] is True and len(engine.simulator.events)==0
    next(b for b in app.button if b.label=="帶回生產控制台再確認").click().run(); assert not app.exception
    assert app.session_state.testline_page=="生產控制台" and len(engine.simulator.events)==0
    assert "candidate_line_speed_m_min" in app.session_state
