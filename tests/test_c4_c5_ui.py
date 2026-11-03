import pytest

from c_dashboard.state import WORKSPACE_KEY
from c_dashboard.spc.incidents import group_spc_incidents
from c3_support import PEEL
from test_c2_ui import load_mock, new_app


def test_whatif_controls_comparison_and_state_survive_tab_rerun():
    app = load_mock(new_app())
    workspace = app.session_state[WORKSPACE_KEY]
    selected = workspace.what_if.selected
    frame = workspace.data.dataset.frame.copy(deep=True)
    spc = workspace.spc.result
    key = next(slider.key for slider in app.slider if slider.key.startswith("ui_whatif_speed_"))
    app.slider(key=key).set_value(1.8).run()
    assert not app.exception
    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.what_if.selected == selected
    assert workspace.what_if.parameters["line_speed_m_min"] == pytest.approx(1.8)
    assert workspace.what_if.comparison.before.targets != workspace.what_if.comparison.after.targets
    current_prediction = workspace.model.current_prediction
    assert workspace.data.dataset.frame.equals(frame)
    assert workspace.spc.result == spc
    assert workspace.model.current_prediction == current_prediction
    assert any("不代表真實 FCCL" in item.value for item in app.caption)

    app.button(key=next(button.key for button in app.button if "ui_whatif_advanced_toggle_" in button.key)).click().run()
    assert not app.exception
    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.what_if.advanced_unlocked
    assert any(slider.key.startswith("ui_whatif_curing_temp_c_") for slider in app.slider)
    app.session_state["ui_workspace_tabs"] = "AI 圖表"
    app.run()
    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.what_if.selected == selected
    assert workspace.what_if.parameters["line_speed_m_min"] == pytest.approx(1.8)
    assert workspace.what_if.advanced_unlocked


def test_reselect_visible_segment_resets_scenario_but_source_switch_does_not_reuse_widget():
    app = load_mock(new_app())
    workspace = app.session_state[WORKSPACE_KEY]
    options = __import__("c_dashboard.quality.controller", fromlist=["available_segments"]).available_segments(
        __import__("c_dashboard.data.session", fromlist=["selected_rows"]).selected_rows(workspace),
        workspace.data.source_id,
    )
    key = next(select.key for select in app.selectbox if select.key.startswith("ui_whatif_segment_"))
    app.selectbox(key=key).set_value(options[0]).run()
    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.what_if.selected == options[0]
    assert workspace.what_if.parameters == {}


def test_mock_prediction_alarm_and_spc_alarm_are_both_visible_and_separate():
    app = load_mock(new_app(), "單點品質偏移情境")
    workspace = app.session_state[WORKSPACE_KEY]
    spc_events = workspace.spc.result.events
    assert spc_events
    settings = workspace.data.dataset.settings
    settings["quality_specs"]["peel_strength_n_mm"]["lsl"] = 9.0
    settings["appearance_ng_risk_threshold"] = 0.05
    app.run()
    assert not app.exception
    errors = [item.value for item in app.error]
    assert any("AI Alarm" in message for message in errors)
    assert sum(item.event_count for item in group_spc_incidents(workspace.spc.result)) == len(spc_events)
    assert any("incident_id" in item.value.columns for item in app.dataframe)
    assert len({event.event_id for event in spc_events}) == len(spc_events)
    assert any("固定 What-if 情境" in message for message in errors)


def test_unavailable_formal_and_mock_adapters_keep_csv_and_spc_visible(monkeypatch):
    from c_dashboard.adapters.unavailable import UnavailableAdapter
    monkeypatch.setattr("c_dashboard.ui.layout.DeterministicMockAdapter", UnavailableAdapter)
    app = load_mock(new_app(), "單點品質偏移情境")
    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.spc.result.events
    assert any("正式模型 Adapter" in item.value for item in app.caption)
    assert any("未提供預測" in item.value or "沒有可用預測" in item.value
               for item in app.caption)
    assert any("sample_id" in item.value.columns for item in app.dataframe)
    assert sum(item.event_count for item in group_spc_incidents(workspace.spc.result)) == len(
        workspace.spc.result.events
    )
    assert len(app.error) < 10
