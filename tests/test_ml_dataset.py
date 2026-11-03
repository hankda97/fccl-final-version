from pathlib import Path

import pandas as pd
import pytest

from fccl_ml.config import FEATURES, PipelineConfig, TARGETS
from fccl_ml.dataset import _attach_inspections, audit_feature_allowlist, build_canonical_dataset, overlap_weighted
from fccl_ml.validation import SourceValidationError, load_and_validate_sources, validate_loaded_tables, validate_roll_splits


PROJECT = Path(__file__).resolve().parents[1]


def test_overlap_weighted_cross_boundary_is_hand_calculable():
    segments = pd.DataFrame({
        "process_segment_id": ["a", "b"],
        "material_md_start_m": [0.0, 4.0],
        "material_md_end_m": [4.0, 10.0],
        "value": [10.0, 20.0],
    })
    values, coverage, ids = overlap_weighted(2.0, 7.0, segments, ("value",))
    assert coverage == pytest.approx(1.0)
    assert values["value"] == pytest.approx((2 * 10 + 3 * 20) / 5)
    assert ids == ("a", "b")


@pytest.mark.parametrize("feature", [
    "peel_strength_n_mm", "overall_pass_flag", "spec_lsl", "peel_label_available",
    "root_roll_id", "drift_severity", "pred_heat_resistance_c",
])
def test_leakage_fields_are_rejected(feature):
    with pytest.raises(ValueError, match="LEAKAGE_FEATURES_REJECTED"):
        audit_feature_allowlist((*FEATURES, feature))


def test_split_rejects_wrong_counts_and_never_falls_back():
    rolls = pd.read_csv(PROJECT / "generated_data/v2/roll_master.csv")
    broken = rolls.iloc[:-1]
    with pytest.raises(SourceValidationError, match="SPLIT_COUNT_MISMATCH"):
        validate_roll_splits(broken)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda tables: tables.pop("drift_ground_truth.csv"), "MISSING_TABLE"),
        (lambda tables: tables.__setitem__("process_segments.csv", tables["process_segments.csv"].drop(columns=["completed_at"])), "MISSING_COLUMN"),
        (lambda tables: tables["roll_master.csv"].__setitem__("root_roll_id", ["ROLL-0001"] * len(tables["roll_master.csv"])), "DUPLICATE_KEY"),
        (lambda tables: tables["process_segments.csv"].__setitem__("root_roll_id", ["MISSING-ROLL", *tables["process_segments.csv"].root_roll_id.iloc[1:]]), "FOREIGN_KEY_MISSING"),
        (lambda tables: tables["process_segments.csv"].__setitem__("material_md_end_m", [0.0, *tables["process_segments.csv"].material_md_end_m.iloc[1:]]), "INVALID_INTERVAL"),
    ],
)
def test_loaded_source_validation_returns_structured_errors(mutation, code):
    tables, metadata = load_and_validate_sources(PROJECT / "generated_data/v2")
    tables = {name: frame.copy() for name, frame in tables.items()}
    mutation(tables)
    with pytest.raises(SourceValidationError) as captured:
        validate_loaded_tables(tables, metadata)
    assert any(issue.code == code for issue in captured.value.issues)


def test_inspection_selection_handles_retest_ambiguity_and_flag_conflict():
    ids = ["A", "B", "C"]
    canonical = pd.DataFrame({
        "aligned_sample_id": ids, "alignment_valid": [1, 1, 1],
    })
    base = {
        "root_roll_id": "R", "segment_id": "S", "product_id": "P", "spec_version": "V",
        "dataset_split": "train", "label_scope": "segment", "inspection_method": "online_vision",
        "test_method_version": "T", "sampled_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T01:00:00+00:00", "label_source": "simulated_inspection",
        "retest_reason": None, "disposition_code": None, "peel_strength_n_mm": None,
        "dimensional_stability_md_pct": None, "dimensional_stability_td_pct": None,
        "heat_resistance_c": None, "peel_label_available": 0, "md_label_available": 0,
        "td_label_available": 0, "heat_label_available": 0, "appearance_label_available": 1,
        "quality_label_available": 1,
    }
    rows = [
        dict(base, inspection_id="old", sampling_event_id="e1", aligned_sample_id="A", validity_status="superseded", is_retest=0, parent_inspection_id=None, appearance_ng_flag=0, appearance_spec_pass_flag=1),
        dict(base, inspection_id="new", sampling_event_id="e1", aligned_sample_id="A", validity_status="valid", is_retest=1, parent_inspection_id="old", retest_reason="repeat", appearance_ng_flag=1, appearance_spec_pass_flag=0),
        dict(base, inspection_id="b1", sampling_event_id="e2", aligned_sample_id="B", validity_status="valid", is_retest=0, parent_inspection_id=None, appearance_ng_flag=0, appearance_spec_pass_flag=1),
        dict(base, inspection_id="b2", sampling_event_id="e3", aligned_sample_id="B", validity_status="valid", is_retest=0, parent_inspection_id=None, appearance_ng_flag=1, appearance_spec_pass_flag=0),
        dict(base, inspection_id="c1", sampling_event_id="e4", aligned_sample_id="C", validity_status="valid", is_retest=0, parent_inspection_id=None, appearance_ng_flag=1, appearance_spec_pass_flag=1),
    ]
    specs = pd.DataFrame([{"product_id": "P", "spec_version": "V", "characteristic": "appearance_ng", "lsl": 0, "usl": 0, "target": 0, "unit": "flag", "test_method": "T", "effective_from": "2025-01-01T00:00:00+00:00", "effective_to": None}])
    merged, lineage, exclusions = _attach_inspections(canonical, {"quality_inspection.csv": pd.DataFrame(rows), "quality_specifications.csv": specs})
    assert merged.set_index("aligned_sample_id").loc["A", "appearance_ng"] == 1
    assert merged.set_index("aligned_sample_id").loc["A", "appearance_ng_available"] == 1
    assert set(exclusions.code) == {"DUPLICATE_INSPECTION_AMBIGUOUS", "APPEARANCE_FLAG_CONFLICT"}
    assert "new" in lineage.set_index("aligned_sample_id").loc["A", "inspection_ids"]


def test_complete_synthetic_builder_has_20000_unique_rows_and_five_targets(tmp_path):
    config = PipelineConfig.default(PROJECT)
    result = build_canonical_dataset(config, "synthetic-ground-truth-v2", tmp_path / "first")
    assert len(result.canonical) == 20_000
    assert result.canonical.aligned_sample_id.nunique() == 20_000
    assert set(result.projections) == set(TARGETS)
    assert all(len(frame) == 20_000 for frame in result.projections.values())
    assert result.canonical[[f"{station}_coverage" for station in ("coating", "curing", "lamination")]].min().min() >= 0.98
    assert result.manifest["split_roll_ids"].keys() == {"train", "validation", "test"}
    samples = result.spc_samples
    assert not samples.empty
    assert samples.aligned_sample_id.is_unique and samples.specimen_id.is_unique
    assert samples.groupby("subgroup_id").size().eq(5).all()
    assert samples.groupby("subgroup_id").root_roll_id.nunique().eq(1).all()
    assert samples.groupby("subgroup_id").synthetic_phase.nunique().eq(1).all()
    assert result.manifest["spc_profile"]["baseline_policy"] == "earliest-25-complete-train-stable-groups"
    assert result.manifest["spc_profile"]["monitoring_policy"] == "validation-and-test-only"
    written_manifest = __import__("json").loads((tmp_path / "first/manifest.json").read_text(encoding="utf-8"))
    assert written_manifest["output_hashes"]["spc_samples.csv"]
    dictionary = __import__("json").loads((tmp_path / "first/data_dictionary.json").read_text(encoding="utf-8"))
    assert dictionary["spc_sidecar"]["classification"].startswith("synthetic demonstration")
    for _, group in samples.groupby("subgroup_id"):
        ordered = group.sort_values("material_md_start_m")
        assert ordered.observed_at.is_monotonic_increasing
        assert ordered.material_md_end_m.iloc[:-1].to_numpy() == pytest.approx(
            ordered.material_md_start_m.iloc[1:].to_numpy()
        )


def test_profiles_are_separate_and_reproducible(tmp_path):
    config = PipelineConfig.default(PROJECT)
    first = build_canonical_dataset(config, "simulated-inspection-v2", tmp_path / "inspection-a")
    second = build_canonical_dataset(config, "simulated-inspection-v2", tmp_path / "inspection-b")
    assert first.manifest == second.manifest
    assert first.manifest["profile"] == "simulated-inspection-v2"
    assert first.manifest["dataset_version"] != build_canonical_dataset(config, "synthetic-ground-truth-v2", tmp_path / "synthetic").manifest["dataset_version"]
    assert first.manifest["projection_rows"]["appearance_ng"] == 20_000
    assert 0 < first.manifest["projection_rows"]["peel_strength_n_mm"] < 20_000
    assert (tmp_path / "inspection-a/manifest.json").read_bytes() == (tmp_path / "inspection-b/manifest.json").read_bytes()
    assert first.spc_samples.empty
    assert "spc_profile" not in first.manifest
    written_manifest = __import__("json").loads((tmp_path / "inspection-a/manifest.json").read_text(encoding="utf-8"))
    assert "spc_samples.csv" not in written_manifest["output_hashes"]


def test_synthetic_spc_sidecar_is_reproducible_and_non_overlapping(tmp_path):
    config = PipelineConfig.default(PROJECT)
    first = build_canonical_dataset(config, "synthetic-ground-truth-v2", tmp_path / "spc-a")
    second = build_canonical_dataset(config, "synthetic-ground-truth-v2", tmp_path / "spc-b")
    assert first.spc_samples.equals(second.spc_samples)
    assert (tmp_path / "spc-a/spc_samples.csv").read_bytes() == (tmp_path / "spc-b/spc_samples.csv").read_bytes()
    assert not set(first.spc_samples.query("baseline_candidate == 1").aligned_sample_id) & set(
        first.spc_samples.query("monitoring_eligible == 1").aligned_sample_id
    )

