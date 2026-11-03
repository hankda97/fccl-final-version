from pathlib import Path

import numpy as np
import pandas as pd

from c_dashboard.adapters.formal import FormalModelAdapter
from c_dashboard.adapters.formal_explanations import FormalTreeShapProvider
from c_dashboard.data.canonical import load_canonical_projection
from c_dashboard.data.session import commit_dataset, selected_rows
from c_dashboard.state import WorkspaceState
from c_dashboard.visualization.controller import workspace_source
from c_dashboard.visualization.controller import explanation_for
from c_dashboard.visualization.explanations import (
    MAX_EXPLANATION_SAMPLES,
    make_request,
    validate_response,
)


PROJECT = Path(__file__).resolve().parents[1]
PROFILE = "synthetic-ground-truth-v2"
DATASET = PROJECT / "generated_data/model_dataset_v2" / PROFILE
ARTIFACTS = PROJECT / "artifacts/synthetic_v2" / PROFILE


def _context(row_count=4):
    loaded = load_canonical_projection(DATASET)
    workspace = WorkspaceState()
    assert commit_dataset(workspace, loaded)
    rows = selected_rows(workspace).head(row_count)
    adapter = FormalModelAdapter(ARTIFACTS, loaded.metadata["canonical_manifest"])
    provider = FormalTreeShapProvider(adapter)
    source = workspace_source(workspace, rows, columns=provider.describe().feature_names)
    return workspace, rows, adapter, provider, source


def _request(rows, adapter, provider, source, target):
    info = provider.describe()
    return make_request(
        rows,
        source,
        adapter.describe(),
        info,
        target=target,
        kind="SHAP Summary Plot",
        model_manifest=adapter.explanation_manifest(),
    )


def test_regression_tree_shap_is_aligned_additive_cached_and_background_only(monkeypatch):
    _, rows, adapter, provider, source = _context()
    request = _request(rows, adapter, provider, source, "peel_strength_n_mm")
    calls = []
    import c_dashboard.adapters.formal_explanations as module
    original = module.pd.read_csv

    def tracked(path, *args, **kwargs):
        calls.append(Path(path).name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(module.pd, "read_csv", tracked)
    response = provider.explain(request)
    validated = validate_response(request, response)
    predicted = adapter.bundles[request.target]["pipeline"].predict(
        pd.DataFrame(request.feature_values, columns=request.feature_names)
    )
    reconstructed = np.asarray(validated.base_values) + np.asarray(validated.contributions).sum(axis=1)
    assert np.allclose(reconstructed, predicted, rtol=1e-5, atol=1e-6)
    assert calls == ["background.csv"]
    assert len(provider._explainers) == 1
    provider.explain(request)
    assert len(provider._explainers) == 1


def test_classification_tree_shap_selects_ng_label_even_when_class_order_reversed():
    _, rows, adapter, provider, source = _context()
    model = adapter.bundles["appearance_ng"]["pipeline"].named_steps["model"]
    model.classes_ = model.classes_[::-1]
    adapter.manifests["appearance_ng"]["class_labels"] = [1, 0]
    provider = FormalTreeShapProvider(adapter)
    request = _request(rows, adapter, provider, source, "appearance_ng")
    response = provider.explain(request)
    validated = validate_response(request, response)
    assert response.payload.class_labels == (1, 0)
    assert response.payload.output_index == 0
    expected = model.predict_proba(np.asarray(request.feature_values))[:, 0]
    reconstructed = np.asarray(validated.base_values) + np.asarray(validated.contributions).sum(axis=1)
    assert np.allclose(reconstructed, expected, rtol=1e-5, atol=1e-6)
    assert request.output_scale == "probability" and request.output_unit == "probability"


def test_explanation_request_uses_a_bounded_deterministic_sample():
    _, rows, adapter, provider, source = _context(MAX_EXPLANATION_SAMPLES + 25)
    request = _request(rows, adapter, provider, source, "heat_resistance_c")
    assert len(request.sample_ids) == MAX_EXPLANATION_SAMPLES
    assert request.excluded_rows == 25
    assert request.sample_ids == tuple(str(value) for value in rows.sample_id.iloc[:MAX_EXPLANATION_SAMPLES])


def test_formal_provider_integrates_with_summary_and_dependence_controller():
    workspace, rows, adapter, provider, _ = _context(8)
    slot = explanation_for(workspace, rows, adapter, provider)
    assert slot.status == "ready"
    assert "SHAP Summary Plot" in slot.result.spec["title"]
    first_key = slot.request_key
    workspace.visualization.shap_kind = "SHAP Dependence Plot"
    workspace.visualization.shap_feature = "ambient_rh_pct"
    workspace.visualization.shap_target = "appearance_ng"
    slot = explanation_for(workspace, rows, adapter, provider)
    assert slot.status == "ready" and slot.request_key != first_key
    assert slot.result.request.output_scale == "probability"
    assert slot.result.spec["encoding"]["x"]["field"] == "value"
