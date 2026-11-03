from copy import deepcopy
import json
from pathlib import Path

import pytest

from c_dashboard.adapters.base import PredictionInput
from c_dashboard.adapters.formal import FormalModelAdapter
from c_dashboard.data.canonical import load_canonical_projection
from c_dashboard.data.session import commit_dataset, selected_rows
from c_dashboard.quality.controller import (
    current_prediction_alarms,
    ensure_what_if_selection,
    evaluate_what_if,
    monitor_prediction,
    what_if_alarms,
)
from c_dashboard.state import WorkspaceState
from fccl_ml.config import FEATURES, TARGETS


PROJECT = Path(__file__).resolve().parents[1]
PROFILE = "synthetic-ground-truth-v2"
DATASET = PROJECT / "generated_data/model_dataset_v2" / PROFILE
ARTIFACTS = PROJECT / "artifacts/synthetic_v2" / PROFILE


def _source_and_rows():
    loaded = load_canonical_projection(DATASET)
    assert loaded.accepted
    return loaded, loaded.frame.head(3)


def test_canonical_projection_loader_preserves_verified_profile_and_lineage():
    loaded, rows = _source_and_rows()
    manifest = loaded.metadata["canonical_manifest"]
    assert loaded.source_kind == "canonical-projection"
    assert manifest["profile"] == PROFILE
    assert rows.aligned_sample_id.notna().all()
    assert rows.root_roll_id.notna().all()
    assert rows.alignment_status.eq("valid").all()


def test_formal_adapter_predicts_five_targets_in_input_order():
    loaded, rows = _source_and_rows()
    adapter = FormalModelAdapter(ARTIFACTS, loaded.metadata["canonical_manifest"])
    samples = [PredictionInput(str(row.sample_id), {name: row[name] for name in FEATURES}) for _, row in rows.iterrows()]
    result = adapter.predict(samples)
    assert result.info.available
    assert result.info.supports_targets == TARGETS
    assert [record.sample_id for record in result.records] == [sample.sample_id for sample in samples]
    assert all(set(record.targets) == set(TARGETS) for record in result.records)
    assert all(0 <= record.appearance_ng_risk <= 1 for record in result.records)


def test_formal_adapter_rejects_extrapolation_without_mock_fallback():
    loaded, rows = _source_and_rows()
    adapter = FormalModelAdapter(ARTIFACTS, loaded.metadata["canonical_manifest"])
    values = {name: rows.iloc[0][name] for name in FEATURES}
    values["line_speed_m_min"] = 1e9
    record = adapter.predict([PredictionInput("outside", values)]).records[0]
    assert not record.targets
    assert set(record.unavailable_targets) == set(TARGETS)
    assert all("OUTSIDE_TRAINING_SUPPORT" in reason for reason in record.unavailable_targets.values())
    assert record.appearance_ng_risk is None


def test_source_manifest_mismatch_disables_only_formal_capability():
    loaded, _ = _source_and_rows()
    manifest = deepcopy(loaded.metadata["canonical_manifest"])
    manifest["dataset_version"] = "wrong"
    adapter = FormalModelAdapter(ARTIFACTS, manifest)
    assert not adapter.describe().available
    assert set(adapter.unavailable) == set(TARGETS)
    assert all("SOURCE_MODEL_INCOMPATIBLE" in reason for reason in adapter.unavailable.values())


def test_one_target_load_failure_keeps_other_targets_available(monkeypatch):
    loaded, _ = _source_and_rows()
    from c_dashboard.adapters import formal as module
    original = module.load_target_bundle

    def selective(root, entry, **kwargs):
        if "heat_resistance_c" in entry["manifest"]:
            raise ValueError("missing heat artifact")
        return original(root, entry, **kwargs)

    monkeypatch.setattr(module, "load_target_bundle", selective)
    adapter = FormalModelAdapter(ARTIFACTS, loaded.metadata["canonical_manifest"])
    assert "heat_resistance_c" in adapter.unavailable
    assert set(adapter.describe().supports_targets) == set(TARGETS) - {"heat_resistance_c"}


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("schema_version", "wrong-schema"),
        ("feature_version", "wrong-features"),
        ("feature_names", [*FEATURES[:-1], "wrong_feature"]),
        ("feature_units", {name: "wrong-unit" for name in FEATURES}),
        ("profile", "wrong-label-profile"),
        ("spec_version", "wrong-spec"),
        ("dataset_version", "wrong-dataset"),
    ],
)
def test_each_source_contract_mismatch_is_rejected(field, replacement):
    loaded, _ = _source_and_rows()
    adapter = FormalModelAdapter(ARTIFACTS, loaded.metadata["canonical_manifest"])
    target = "peel_strength_n_mm"
    manifest = deepcopy(adapter.manifests[target])
    source = deepcopy(loaded.metadata["canonical_manifest"])
    source[field] = replacement
    adapter.source_manifest = source
    with pytest.raises(ValueError, match="SOURCE_MODEL_INCOMPATIBLE"):
        adapter._validate_compatibility(target, manifest)


def test_one_target_inference_failure_does_not_reuse_mock_or_old_values(monkeypatch):
    loaded, rows = _source_and_rows()
    adapter = FormalModelAdapter(ARTIFACTS, loaded.metadata["canonical_manifest"])
    from c_dashboard.adapters import formal as module
    original = module.predict_bundle

    def selective(bundle, frame):
        if bundle["target"] == "heat_resistance_c":
            raise RuntimeError("isolated inference failure")
        return original(bundle, frame)

    monkeypatch.setattr(module, "predict_bundle", selective)
    sample = PredictionInput("failure", {name: rows.iloc[0][name] for name in FEATURES})
    record = adapter.predict([sample]).records[0]
    assert "heat_resistance_c" not in record.targets
    assert "INFERENCE_ERROR" in record.unavailable_targets["heat_resistance_c"]
    assert set(record.targets) == set(TARGETS) - {"heat_resistance_c"}


def test_streamlit_formal_adapter_resource_cache_is_keyed_by_registry_and_source():
    loaded, _ = _source_and_rows()
    from c_dashboard.ui.layout import _cached_formal_adapter
    registry_hash = __import__("hashlib").sha256((ARTIFACTS / "registry.json").read_bytes()).hexdigest()
    source_json = json.dumps(loaded.metadata["canonical_manifest"], sort_keys=True, ensure_ascii=False)
    first = _cached_formal_adapter(str(ARTIFACTS), registry_hash, source_json)
    second = _cached_formal_adapter(str(ARTIFACTS), registry_hash, source_json)
    assert first is second


def test_formal_adapter_runs_monitor_what_if_and_alarm_without_predicted_yield():
    loaded, _ = _source_and_rows()
    workspace = WorkspaceState()
    assert commit_dataset(workspace, loaded)
    rows = selected_rows(workspace)
    adapter = FormalModelAdapter(ARTIFACTS, loaded.metadata["canonical_manifest"])

    current = monitor_prediction(workspace, rows.head(25), adapter)
    assert current is not None and current.record is not None
    assert set(current.record.targets) == set(TARGETS)
    assert "predicted_yield" not in current.record.targets
    alarms, indeterminate = current_prediction_alarms(workspace, current)
    assert isinstance(alarms, tuple) and isinstance(indeterminate, tuple)

    options = ensure_what_if_selection(workspace, rows.head(25))
    assert options and workspace.what_if.selected is not None
    comparison, recommendation = evaluate_what_if(workspace, adapter)
    assert comparison is not None and comparison.unavailable_reason is None
    assert comparison.before is not None and comparison.after is not None
    assert set(comparison.after.targets) == set(TARGETS)
    assert "predicted_yield" not in comparison.after.targets
    scenario_alarms, scenario_indeterminate = what_if_alarms(workspace, comparison)
    assert isinstance(scenario_alarms, tuple) and isinstance(scenario_indeterminate, tuple)
    assert recommendation is not None

