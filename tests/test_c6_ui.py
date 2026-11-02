import json
from dataclasses import replace

from c_dashboard.state import WORKSPACE_KEY
from c_dashboard.visualization.config import SHAP_KINDS
from test_c2_ui import load_mock, new_app, upload, FIXTURES
from c6_support import RenderTestModel, RenderTestProvider
from c_dashboard.adapters.explanations import ExplanationResponse
from test_c6_sources import inspection_rows, PROFILE


def render_app(monkeypatch, provider):
    monkeypatch.setattr("c_dashboard.ui.layout.DeterministicMockAdapter", RenderTestModel)
    monkeypatch.setattr("c_dashboard.ui.layout.explanation_provider_for", lambda adapter: provider)
    return load_mock(new_app(), "單點品質偏移情境")


def chart_specs(app):
    return [json.loads(item.proto.spec) for item in app.get("vega_lite_chart")]


def heatmap_key(app, name):
    return next(widget.key for widget in app.multiselect if widget.key.startswith(name))


def test_heatmap_live_measured_labels_counts_selection_and_empty_filters():
    app = load_mock(new_app())
    workspace = app.session_state[WORKSPACE_KEY]
    result = workspace.visualization.heatmap.result
    assert result.total_rows == 150
    assert len(result.cells) == 11 * 5
    spec = next(s for s in chart_specs(app) if "Heatmap" in s["title"])
    assert spec["layer"][0]["encoding"]["color"]["condition"]["scale"]["domain"] == [-1, 1]
    assert any(cell.coefficient is None for cell in result.cells)
    assert any(cell.coefficient is not None for cell in result.cells)
    app.multiselect(key=heatmap_key(app, "ui_heatmap_targets_")).set_value(["peel_strength_n_mm"]).run()
    assert not app.exception
    assert {c.target for c in app.session_state[WORKSPACE_KEY].visualization.heatmap.result.cells} == {"peel_strength_n_mm"}
    app.multiselect(key=heatmap_key(app, "ui_heatmap_features_")).set_value([]).run()
    assert app.session_state[WORKSPACE_KEY].visualization.heatmap.status == "unavailable"
    assert any("未選取" in info.value for info in app.info)
    assert not any("Heatmap" in spec["title"] for spec in chart_specs(app))


def test_mock_has_shap_controls_no_fake_shap_and_heatmap_keeps_working():
    app = load_mock(new_app())
    assert tuple(app.radio(key="ui_shap_kind").options) == SHAP_KINDS
    app.radio(key="ui_shap_kind").set_value(SHAP_KINDS[1]).run()
    assert not app.exception
    assert any("待 B" in info.value for info in app.info)
    assert any("Heatmap" in spec["title"] for spec in chart_specs(app))
    assert not any("SHAP" in spec["title"] for spec in chart_specs(app))


def test_partial_quality_keeps_other_cells_and_source_filter_metadata():
    app = load_mock(new_app(), "部分品質欄位缺失")
    workspace = app.session_state[WORKSPACE_KEY]
    result = workspace.visualization.heatmap.result
    assert all(c.coefficient is None for c in result.cells if c.target == "heat_resistance_c")
    token = workspace.data.source_id[:12]
    app.selectbox(key=f"ui_batch_{token}").set_value("M-B02").run()
    result = app.session_state[WORKSPACE_KEY].visualization.heatmap.result
    assert result.source.batch == "M-B02" and result.total_rows == 75


def test_render_test_summary_dependence_target_feature_switch_and_rerun(monkeypatch):
    provider = RenderTestProvider()
    app = render_app(monkeypatch, provider)
    assert any("介面測試資料，非真正 SHAP" in x.value for x in app.warning)
    assert any("SHAP Summary" in s["title"] for s in chart_specs(app))
    calls = provider.calls
    app.run()
    assert provider.calls == calls  # Matching reruns reuse validated data, not live Figures.
    app.radio(key="ui_shap_kind").set_value(SHAP_KINDS[1]).run()
    feature = next(x for x in app.selectbox if x.key.startswith("ui_shap_feature_"))
    feature.set_value("ambient_rh_pct").run()
    app.selectbox(key="ui_shap_target").set_value("appearance_ng").run()
    assert not app.exception
    spec = next(s for s in chart_specs(app) if "SHAP Dependence" in s["title"])
    assert "%RH" in spec["encoding"]["x"]["title"]
    assert "probability" in spec["encoding"]["y"]["title"]
    assert any("Heatmap" in s["title"] for s in chart_specs(app))


def test_provider_failure_retry_and_partial_target_do_not_reset_other_features(monkeypatch):
    class Provider(RenderTestProvider):
        failed = False
        def explain(self, request):
            if self.failed:
                raise ValueError("test-provider-failure")
            return super().explain(request)
    provider = Provider()
    app = render_app(monkeypatch, provider)
    w = app.session_state[WORKSPACE_KEY]
    w.data.dataset.settings["quality_specs"]["peel_strength_n_mm"]["lsl"] = 9.0
    w.data.dataset.settings["appearance_ng_risk_threshold"] = .05
    app.run()
    spc, selection, current = w.spc.result, w.what_if.selected, w.model.current_prediction
    assert spc.events
    assert any("AI Alarm" in e.value for e in app.error)
    provider.failed = True
    app.button(key="ui_shap_retry").click().run()
    assert not app.exception and app.session_state[WORKSPACE_KEY].visualization.explanation.status == "error"
    assert any("test-provider-failure" in e.value for e in app.error)
    assert not any("SHAP" in s["title"] for s in chart_specs(app))
    assert any("Heatmap" in s["title"] for s in chart_specs(app))
    assert w.spc.result == spc and w.what_if.selected == selection and w.model.current_prediction == current
    assert any("SPC Alarm" in e.value for e in app.error)
    assert any("AI Alarm" in e.value for e in app.error)
    provider.failed = False
    app.button(key="ui_shap_retry").click().run()
    assert w.visualization.explanation.status == "ready"
    monkeypatch.setattr(provider, "describe", lambda: replace(RenderTestProvider().describe(), supported_targets=("heat_resistance_c",)))
    app.run()
    assert w.visualization.explanation.status == "unavailable" and not app.exception
    assert w.spc.result == spc and w.what_if.selected == selection


def test_figure_provider_embeds_image_without_live_figure_state(monkeypatch):
    class FigureProvider(RenderTestProvider):
        def explain(self, request):
            from matplotlib import pyplot as plt
            figure, axis = plt.subplots()
            axis.scatter([1, 2], [.1, -.1])
            return ExplanationResponse(request, figure=figure)
    app = render_app(monkeypatch, FigureProvider())
    assert not app.exception
    result = app.session_state[WORKSPACE_KEY].visualization.explanation.result
    assert result.png.startswith(b"\x89PNG") and result.spec is None
    assert app.get("image")


def test_projected_availability_scope_versions_and_missing_labels_in_ui(monkeypatch):
    provider = RenderTestProvider()
    app = render_app(monkeypatch, provider)
    w = app.session_state[WORKSPACE_KEY]
    w.data.dataset.frame = inspection_rows(w.data.dataset.frame)
    monkeypatch.setattr("c_dashboard.visualization.controller.profile_for_workspace", lambda workspace, rows: PROFILE)
    w.data.dataset.frame["peel_label_available"] = 0
    w.data.dataset.frame["peel_label_reason"] = "DUPLICATE_INSPECTION_AMBIGUOUS"
    app.run()
    assert not app.exception
    assert w.visualization.explanation.status == "ready"  # No observed peel label is needed to explain a model.
    assert all(c.n == 0 for c in w.visualization.heatmap.result.cells if c.target == "peel_strength_n_mm")
    assert any("root_roll_id=TEST-ROLL" in c.value for c in app.caption)
    assert any("monitoring-v2" in c.value for c in app.caption)
    assert any("Manifest render-test-manifest" in c.value for c in app.caption)
    old = w.visualization.heatmap.request_key
    w.data.dataset.frame["label_scope"] = "roll"
    app.run()
    assert old != w.visualization.heatmap.request_key
    assert all(c.n == 0 for c in w.visualization.heatmap.result.cells)
    assert any("標籤 availability" in c.value for c in app.caption)


def test_raw_v2_metadata_is_not_silently_dropped_into_legacy_heatmap():
    payload = (FIXTURES / "normal.csv").read_text(encoding="utf-8").splitlines()
    payload[0] += ",label_source,peel_label_available"
    payload[1:] = [line + ",simulated_inspection,0" for line in payload[1:]]
    app = upload(new_app(), "\n".join(payload).encode())
    w = app.session_state[WORKSPACE_KEY]
    assert not app.exception
    assert w.visualization.heatmap.result.source.profile.kind == "unresolved"
    assert all(c.n == 0 for c in w.visualization.heatmap.result.cells)
    assert any("投影尚未交付" in x.value for x in app.warning)
    assert any("sample_id" in d.value.columns for d in app.dataframe)


def test_chart_ui_errors_are_local_and_retry_recovers(monkeypatch):
    import streamlit as st
    original = st.vega_lite_chart
    failed = {"ui_shap_chart"}
    def draw(*args, **kwargs):
        if kwargs.get("key") in failed:
            raise ValueError("ui-render-failed")
        return original(*args, **kwargs)
    monkeypatch.setattr(st, "vega_lite_chart", draw)
    app = render_app(monkeypatch, RenderTestProvider())
    w = app.session_state[WORKSPACE_KEY]
    assert not app.exception and w.visualization.explanation.status == "error"
    assert w.visualization.heatmap.status == "ready" and w.spc.result.events
    failed.clear()
    app.button(key="ui_shap_retry").click().run()
    assert not app.exception and w.visualization.explanation.status == "ready"
    failed.add("ui_heatmap_chart")
    app.button(key="ui_heatmap_retry").click().run()
    assert not app.exception and w.visualization.heatmap.status == "error"
    assert w.visualization.explanation.status == "ready" and w.spc.result.events
    failed.clear()
    app.button(key="ui_heatmap_retry").click().run()
    assert not app.exception and w.visualization.heatmap.status == "ready"


def test_whatif_tabs_filters_source_switch_and_failed_upload_preserve_correct_chart_state(monkeypatch):
    app = render_app(monkeypatch, RenderTestProvider())
    w = app.session_state[WORKSPACE_KEY]
    chart, spc = w.visualization.heatmap.result, w.spc.result
    selection = w.what_if.selected
    slider = next(x for x in app.slider if x.key.startswith("ui_whatif_speed_"))
    slider.set_value(slider.value - .1).run()
    parameters = dict(w.what_if.parameters)
    for tab in ("AI 圖表", "SPC 監控", "What-if"):
        app.session_state["ui_workspace_tabs"] = tab
        app.run()
        assert w.visualization.heatmap.result is chart and w.spc.result == spc
        assert w.what_if.selected == selection and w.what_if.parameters == parameters
    upload(app, b"", "invalid.csv")
    assert w.visualization.heatmap.result is chart
    token = w.data.source_id[:12]
    app.selectbox(key=f"ui_batch_{token}").set_value("M-B02").run()
    assert w.visualization.heatmap.result.source.batch == "M-B02"
    assert w.visualization.heatmap.result.total_rows == 75
    load_mock(app, "部分品質欄位缺失")
    assert not app.exception
    assert w.visualization.heatmap.result.source.source_id == w.data.source_id
    assert all(c.coefficient is None for c in w.visualization.heatmap.result.cells if c.target == "heat_resistance_c")
