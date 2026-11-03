from pathlib import Path

from streamlit.testing.v1 import AppTest

from c_dashboard.adapters.formal import FORMAL_SOURCE
from c_dashboard.state import WORKSPACE_KEY
from c_dashboard.ui.tabs import TAB_LABELS


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_canonical_formal_inference_whatif_and_shap_end_to_end():
    app = AppTest.from_file(str(ROOT / "legacy_app.py"), default_timeout=120).run()
    assert not app.exception
    assert [tab.proto.label for tab in app.get("tab")] == list(TAB_LABELS)
    app.radio(key="ui_source_choice").set_value("Canonical Synthetic projection").run()
    app.button(key="ui_load_canonical").click().run()
    assert not app.exception
    app.selectbox(key="ui_model_source").set_value("Synthetic 正式 artifact").run()
    assert not app.exception

    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.data.dataset.source_kind == "canonical-projection"
    assert workspace.model.current_prediction.adapter_source == FORMAL_SOURCE
    assert workspace.model.current_prediction.record is not None
    assert "predicted_yield" not in workspace.model.current_prediction.record.targets
    assert len(app.metric) >= 9
    record = workspace.model.current_prediction.record
    regression_targets = (
        "peel_strength_n_mm",
        "dimensional_stability_md_pct",
        "dimensional_stability_td_pct",
        "heat_resistance_c",
    )
    assert [item.value for item in app.metric[:4]] == [
        f"{float(record.targets[target]):.6g}" for target in regression_targets
    ]
    assert app.metric[4].value != "—"
    assert [item.value for item in app.metric[5:9]] == [
        f"{target.latest.mean:.6g}" for target in workspace.spc.result.targets
    ]
    assert workspace.spc.result.baseline is not None
    assert len(workspace.spc.result.events) == 2913
    assert len(app.error) < 10
    assert any("SPC Alarm 摘要" in item.value and "原始規則事件 2913" in item.value
               for item in app.caption)
    assert not any(workspace.spc.result.events[0].event_id in item.value for item in app.error)
    incident_tables = [item.value for item in app.dataframe if "incident_id" in item.value.columns]
    assert incident_tables and len(incident_tables[0]) <= 10
    detail_tables = [item.value for item in app.dataframe if "event_id" in item.value.columns]
    assert detail_tables and set(detail_tables[-1]["event_id"]).issubset(
        {event.event_id for event in workspace.spc.result.events}
    )
    assert "Canonical Synthetic" in workspace.spc.result.baseline.source
    assert all(target.baseline.valid for target in workspace.spc.result.targets)
    rendered_text = "\n".join(
        str(item.value)
        for element_type in (app.caption, app.info, app.warning, app.error)
        for item in element_type
    )
    assert "MISSING_SAMPLING_EVIDENCE" not in rendered_text
    assert "BASELINE_UNAVAILABLE" not in rendered_text
    assert "尚未接入" not in rendered_text
    assert workspace.what_if.comparison is not None
    assert workspace.what_if.comparison.adapter_source == FORMAL_SOURCE
    assert workspace.visualization.explanation.status == "ready", workspace.visualization.explanation.reason
    assert workspace.visualization.explanation.result.request.info.source_kind == "model"
    assert not app.button(key="ui_shap_retry").disabled
    assert any("SHAP Summary Plot" in item.proto.spec for item in app.get("vega_lite_chart"))
    app.radio(key="ui_shap_kind").set_value("SHAP Dependence Plot").run()
    assert not app.exception
    assert app.session_state[WORKSPACE_KEY].visualization.explanation.status == "ready"
    assert any("SHAP Dependence Plot" in item.proto.spec for item in app.get("vega_lite_chart"))
    batch = next(item for item in app.selectbox if item.label == "批次篩選")
    batch.set_value("ROLL-0124").run()
    workspace = app.session_state[WORKSPACE_KEY]
    assert not app.exception
    assert workspace.what_if.selected.batch_id == "ROLL-0124"
    assert workspace.what_if.comparison is not None
    assert workspace.what_if.comparison.adapter_source == FORMAL_SOURCE
