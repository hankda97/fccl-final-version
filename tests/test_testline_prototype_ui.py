"""Gate 0 acceptance tests for the isolated static test-line prototype."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "testline_prototype.py"


def new_app():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not app.exception
    return app


def all_text(app) -> str:
    kinds = (app.markdown, app.caption, app.info, app.warning, app.success, app.subheader, app.header)
    return "\n".join(str(item.value) for group in kinds for item in group)


def navigate(app, page: str):
    index = ["生產控制台", "SPC 詳細監控", "What-if／Heatmap", "Run 紀錄"].index(page)
    app.button(key=f"prototype_nav_{index}").click().run()
    assert not app.exception
    return app


def test_prototype_entry_is_explicitly_static_and_has_only_four_page_buttons():
    app = new_app()
    text = all_text(app)
    assert "Gate 0 靜態 UI 原型" in text
    assert "不會啟動模型、模擬器或真實設備" in text
    labels = [app.button(key=f"prototype_nav_{index}").label for index in range(4)]
    assert labels == ["生產控制台", "SPC 詳細監控", "What-if／Heatmap", "Run 紀錄"]
    assert all("SHAP" not in label for label in labels)
    assert "模式 A" not in text and "模式 C" not in text


def test_production_page_has_line_product_recipe_numeric_inputs_and_five_charts():
    app = new_app()
    text = all_text(app)
    assert "模擬產線與材料位置" in text
    assert "FCCL-DEMO-001" in text and "SIM-RECIPE-3.0" in text
    thickness = next(metric for metric in app.metric if metric.label == "乾膠厚度目標")
    assert thickness.value == "25.0 μm" and thickness.delta == "允收 23.0–27.0 μm"
    assert len(app.number_input) == 10
    assert not app.slider
    assert len(app.get("vega_lite_chart")) == 5
    assert "目前追蹤區段" in text and "SEG-019" in text and "SEG-017" in text and "SEG-016" in text
    assert all(label in text for label in ("抗剝離度", "尺寸安定性 MD", "尺寸安定性 TD", "耐熱度"))
    assert text.count("符合規格") >= 2 and "高於規格下限 0.11 N/mm" in text
    assert "2 項警告" in text and "0 項嚴重" in text
    assert "fixture_event_id=PROTO-AIRFLOW-001" not in text  # technical detail is collapsed


def test_candidate_does_not_apply_until_form_submit_then_updates_fixture_only():
    app = new_app()
    widget = app.number_input(key="prototype_input_line_speed")
    widget.set_value(5.1)
    assert app.session_state.prototype_applied["line_speed"] == 4.8
    app.button(key="FormSubmitter:prototype_parameter_form-確認套用至靜態 fixture").click().run()
    assert app.session_state.prototype_applied["line_speed"] == 5.1
    assert any("未建立 ParameterEvent" in item.value for item in app.success)


def test_spc_page_shows_all_signals_separates_limits_and_keeps_details_collapsed():
    app = navigate(new_app(), "SPC 詳細監控")
    text = all_text(app)
    assert "全部 5 項製程訊號同頁顯示" in text
    assert "產品規格、配方範圍與統計管制界限是三種不同界線" in text
    assert "製程失控" in text and "產品超規" in text
    assert not app.selectbox
    assert len(app.get("vega_lite_chart")) == 5
    markdown_text = "\n".join(item.value for item in app.markdown)
    for title in ("乾膠厚度 X-bar／R", "熟化溫度 I-MR", "排風量 EWMA", "線速 I-MR", "壓合壓力 I-MR"):
        assert title in markdown_text
    assert "PROTO-AIRFLOW-001" not in text
    assert "SPC 製程警報" in text and "品質預測警示" in text


def test_alarm_summary_and_detail_link_between_spc_and_parameter_page():
    app = new_app()
    app.button(key="prototype_open_spc_alarm").click().run()
    assert not app.exception
    assert app.session_state.prototype_active_page == "SPC 詳細監控"
    assert any("異常警報中心" in item.value for item in app.subheader)
    app.button(key="prototype_alarm_to_parameters").click().run()
    assert not app.exception
    assert app.session_state.prototype_active_page == "生產控制台"
    assert any("由 SPC 警報中心返回" in item.value for item in app.success)


def test_whatif_heatmap_readiness_and_candidate_return_are_interactive():
    app = navigate(new_app(), "What-if／Heatmap")
    app.button(key="prototype_calculate_whatif").click().run()
    assert not app.exception
    assert any("靜態 fixture，不是正式推論" in item.value for item in app.caption)
    app.button(key="prototype_return_candidate").click().run()
    assert any("再次確認" in item.value for item in app.success)
    app.selectbox(key="prototype_heatmap_source").set_value("目前 Run fixture（18 個完成區段）").run()
    assert any("至少需要 30 個" in item.value for item in app.warning)
    app.selectbox(key="prototype_heatmap_source").set_value("Synthetic v3 reference fixture").run()
    app.button(key="prototype_calculate_heatmap").click().run()
    assert any("相關不代表改善或因果" in item.value for item in app.success)


def test_run_records_show_completed_and_interrupted_without_resume_or_training():
    app = navigate(new_app(), "Run 紀錄")
    text = all_text(app)
    assert "不會建立 runtime_data 或觸發訓練" in text
    app.selectbox(key="prototype_run_select").set_value("RUN-PROTO-002").run()
    assert any("只能唯讀檢視" in item.value for item in app.warning)
    json_text = "\n".join(str(item.value) for item in app.json)
    assert '"resume_supported": false' in json_text
    assert '"training_eligible": false' in json_text
