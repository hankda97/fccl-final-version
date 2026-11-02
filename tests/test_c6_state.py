from dataclasses import replace
import copy

import pytest

from c_dashboard.state import WorkspaceState, ensure_workspace, WORKSPACE_KEY
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.data.session import commit_dataset, attempt_upload, selected_rows, set_filters
from c_dashboard.visualization.controller import heatmap_for, explanation_for, begin, complete
from c_dashboard.visualization.types import ChartSlot
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c6_support import RenderTestModel, RenderTestProvider
from test_c6_sources import inspection_rows, PROFILE
from test_c6_heatmap import SPEED, PEEL


def workspace():
    w = WorkspaceState()
    commit_dataset(w, load_mock_fixture("normal"))
    return w


def test_status_machine_late_success_and_late_failure_are_rejected():
    slot = ChartSlot()
    assert slot.status == "not_loaded"
    begin(slot, "a")
    assert slot.status == "running"
    complete(slot, "a", "first")
    assert slot.status == "ready"
    slot.invalidate()
    assert slot.status == "stale" and slot.result is None
    begin(slot, "b")
    assert not complete(slot, "a", "late")
    assert not complete(slot, "a", status="error", reason="old failure")
    assert slot.status == "running"
    complete(slot, "b", status="unavailable", reason="not delivered")
    assert slot.reason == "not delivered"
    begin(slot, "c")
    complete(slot, "c", status="error", reason="failed")
    assert slot.status == "error" and slot.result is None


def test_same_key_caches_but_changed_values_options_or_only_metadata_invalidate():
    w = workspace()
    rows = selected_rows(w)
    a = heatmap_for(w, rows).result
    count = w.visualization.heatmap.computations
    assert heatmap_for(w, rows).result is a
    assert w.visualization.heatmap.computations == count
    rows = rows.copy()
    rows.loc[0, PEEL] += .01
    b = heatmap_for(w, rows).result
    assert b.source.content_digest != a.source.content_digest
    assert w.visualization.heatmap.computations == count + 1
    w.visualization.heatmap_targets = (PEEL,)
    heatmap_for(w, rows)
    assert w.visualization.heatmap.computations == count + 2
    projected = inspection_rows(rows)
    a = heatmap_for(w, projected, profile=PROFILE).result
    projected["peel_label_available"] = 0
    b = heatmap_for(w, projected, profile=PROFILE).result
    assert b.source.content_digest != a.source.content_digest and all(c.n == 0 for c in b.cells)
    c = heatmap_for(w, projected, profile=replace(PROFILE, spec_version="new")).result
    assert c.source != b.source


def test_same_source_reload_failed_upload_and_filters_keep_or_clear_only_dependencies():
    w = workspace()
    heatmap_for(w, selected_rows(w))
    result = w.visualization.heatmap.result
    generation = w.visualization.generation
    commit_dataset(w, load_mock_fixture("normal"))
    assert w.visualization.heatmap.result is result
    assert not commit_dataset(w, attempt_upload(b"", "bad.csv"))
    assert w.visualization.heatmap.result is result
    w.visualization.shap_feature = SPEED
    set_filters(w, "M-B02", None, None)
    assert w.visualization.generation == generation + 1
    assert w.visualization.heatmap.status == "stale" and w.visualization.heatmap.result is None
    assert w.visualization.shap_feature == SPEED
    original = w.data.dataset.content
    altered = original.replace(b"1.086", b"1.085", 1)
    # Keep same filename and row count, change one actual numeric value.
    if altered == original:
        altered = original.replace(b"45.0", b"46.0", 1)
    if altered == original:
        altered = original.replace(b"C-DEMO-01", b"C-DEMO-02", 1)
    new = attempt_upload(altered, w.data.dataset.source_name)
    assert new.accepted
    old = w.data.source_id
    commit_dataset(w, new)
    assert w.data.source_id != old and len(w.data.dataset.frame) == 150


def test_explanation_rerun_retry_versions_and_errors_use_independent_slots(monkeypatch):
    w = workspace()
    rows = selected_rows(w)
    provider, model = RenderTestProvider(), RenderTestModel()
    heatmap_for(w, rows)
    heatmap = w.visualization.heatmap.result
    assert explanation_for(w, rows, model, provider).status == "ready"
    request = w.visualization.explanation.request_key
    assert provider.calls == 1
    explanation_for(w, rows, model, provider)
    assert provider.calls == 1
    explanation_for(w, rows, model, provider, retry=True)
    assert provider.calls == 2
    info = provider.describe()
    monkeypatch.setattr(provider, "describe", lambda: replace(info, explanation_version="new"))
    explanation_for(w, rows, model, provider)
    assert provider.calls == 3 and request != w.visualization.explanation.request_key
    monkeypatch.setattr(provider, "describe", lambda: replace(info, manifest=replace(info.manifest, manifest_id="old")))
    assert explanation_for(w, rows, model, provider).status == "error"
    assert w.visualization.explanation.result is None and w.visualization.heatmap.result is heatmap
    assert explanation_for(w, rows, DeterministicMockAdapter(), provider).status == "unavailable"
    assert provider.calls == 3


def test_inflight_provider_cannot_commit_after_new_key_even_when_it_errors():
    for fail in (False, True):
        w = workspace()
        class Provider(RenderTestProvider):
            def explain(self, request):
                begin(w.visualization.explanation, "newer")
                if fail:
                    raise ValueError("old failure")
                return super().explain(request)
        explanation_for(w, selected_rows(w), RenderTestModel(), Provider())
        assert w.visualization.explanation.request_key == "newer"
        assert w.visualization.explanation.status == "running"
        assert w.visualization.explanation.result is None


def test_heatmap_error_retry_is_local_and_whatif_does_not_enter_key(monkeypatch):
    import c_dashboard.visualization.controller as controller
    w = workspace()
    rows = selected_rows(w)
    original = rows.copy(deep=True)
    w.what_if.parameters[SPEED] = .5
    a = heatmap_for(w, rows).result
    w.what_if.parameters[SPEED] = .7
    assert heatmap_for(w, rows).result is a and rows.equals(original)
    compute = controller.compute_heatmap
    def fail(*a, **kw):
        raise RuntimeError("heatmap-test-error")
    monkeypatch.setattr(controller, "compute_heatmap", fail)
    assert heatmap_for(w, rows, retry=True).status == "error"
    assert w.what_if.parameters[SPEED] == .7
    monkeypatch.setattr(controller, "compute_heatmap", compute)
    assert heatmap_for(w, rows, retry=True).status == "ready"


def test_backwards_session_initialization_and_cross_session_isolation():
    w = workspace()
    del w.visualization
    session = {WORKSPACE_KEY: w}
    assert ensure_workspace(session) is w
    assert w.visualization.heatmap.status == "not_loaded"
    other = workspace()
    heatmap_for(w, selected_rows(w))
    assert other.visualization.heatmap.result is None
