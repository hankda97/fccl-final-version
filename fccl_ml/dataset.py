"""Build deterministic target-specific canonical projections from seven tables."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .config import FEATURES, FEATURE_UNITS, PipelineConfig, TARGETS, TARGET_UNITS
from .paths import assert_output_separated
from .validation import SourceValidationError, ValidationIssue, file_sha256, load_and_validate_sources, validate_roll_splits


TARGET_AVAILABILITY = {
    "peel_strength_n_mm": "peel_label_available",
    "dimensional_stability_md_pct": "md_label_available",
    "dimensional_stability_td_pct": "td_label_available",
    "heat_resistance_c": "heat_label_available",
    "appearance_ng": "appearance_label_available",
}
INSPECTION_VALUE = {**{target: target for target in TARGETS[:-1]}, "appearance_ng": "appearance_ng_flag"}
STATION_FEATURES = {
    "coating": ("coating_temp_c", "coating_gap_um", "coating_viscosity_mpa_s"),
    "curing": ("curing_temp_c", "curing_time_min"),
    "lamination": ("ambient_temp_c", "ambient_rh_pct", "line_speed_m_min", "lamination_temp_c", "lamination_pressure_mpa", "lamination_time_s"),
}
SPC_SAMPLE_COLUMNS = (
    "aligned_sample_id", "sampling_event_id", "subgroup_id", "specimen_id",
    "root_roll_id", "dataset_split", "synthetic_phase", "material_md_start_m",
    "material_md_end_m", "observed_at", "sampled_at", "available_at",
    "spc_condition_code", "baseline_candidate", "monitoring_eligible",
)
SPC_PROFILE_VERSION = "synthetic-xbar-profile-v1"


@dataclass(frozen=True)
class BuildResult:
    profile: str
    output_dir: Path
    canonical: pd.DataFrame
    projections: dict[str, pd.DataFrame]
    lineage: pd.DataFrame
    exclusions: pd.DataFrame
    spc_samples: pd.DataFrame
    manifest: dict


def overlap_weighted(anchor_start: float, anchor_end: float, segments: pd.DataFrame, columns: Iterable[str]) -> tuple[dict[str, float], float, tuple[str, ...]]:
    starts = segments.material_md_start_m.to_numpy(dtype=float)
    ends = segments.material_md_end_m.to_numpy(dtype=float)
    weights = np.maximum(0.0, np.minimum(anchor_end, ends) - np.maximum(anchor_start, starts))
    selected = weights > 0
    length = float(anchor_end - anchor_start)
    coverage = float(weights[selected].sum() / length) if length > 0 else 0.0
    values = {}
    for column in columns:
        numeric = pd.to_numeric(segments.loc[selected, column], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(numeric)
        values[column] = float(np.average(numeric[valid], weights=weights[selected][valid])) if valid.any() else np.nan
    ids = tuple(str(value) for value in segments.loc[selected, "process_segment_id"])
    return values, coverage, ids


def build_canonical_dataset(config: PipelineConfig, profile: str, output_dir: Path | str | None = None, *, write: bool = True) -> BuildResult:
    if profile not in {"synthetic-ground-truth-v2", "simulated-inspection-v2"}:
        raise ValueError(f"Unknown profile: {profile}")
    tables, metadata = load_and_validate_sources(config.source_dir)
    output = Path(output_dir or config.dataset_dir / profile).resolve()
    assert_output_separated(output, (config.source_dir, config.project_root / "raw data"))
    splits = validate_roll_splits(tables["roll_master.csv"])
    canonical, lineage, alignment_exclusions = _align_process(tables, config)
    if profile == "synthetic-ground-truth-v2":
        canonical, label_lineage, label_exclusions = _attach_synthetic(canonical, tables)
    else:
        canonical, label_lineage, label_exclusions = _attach_inspections(canonical, tables)
    lineage = lineage.merge(label_lineage, on="aligned_sample_id", how="left")
    exclusions = pd.concat([alignment_exclusions, label_exclusions], ignore_index=True, sort=False)
    spc_samples = _build_spc_samples(canonical, tables, profile)
    projections: dict[str, pd.DataFrame] = {}
    for target in TARGETS:
        available = canonical[f"{target}_available"].eq(1) & canonical[target].notna()
        columns = ["aligned_sample_id", "root_roll_id", "dataset_split", "timestamp", "process_phase", *FEATURES, target]
        projections[target] = canonical.loc[available, columns].copy().sort_values(["timestamp", "aligned_sample_id"]).reset_index(drop=True)
    audit_feature_allowlist(FEATURES)
    manifest = _manifest(config, profile, metadata, tables["quality_specifications.csv"], canonical,
                         projections, splits, lineage, exclusions, spc_samples)
    result = BuildResult(profile, output, canonical, projections, lineage, exclusions, spc_samples, manifest)
    if write:
        _write_result(result)
    return result


def _build_spc_samples(canonical: pd.DataFrame, tables: dict[str, pd.DataFrame], profile: str) -> pd.DataFrame:
    """Build explicit synthetic rational-subgroup evidence, never row-order fallback evidence."""
    if profile != "synthetic-ground-truth-v2":
        return pd.DataFrame(columns=SPC_SAMPLE_COLUMNS)
    truth = tables["quality_timeseries.csv"][["aligned_sample_id", "timestamp", "process_phase"]].rename(
        columns={"timestamp": "observed_at", "process_phase": "synthetic_phase"}
    )
    frame = canonical[[
        "aligned_sample_id", "root_roll_id", "dataset_split", "material_md_start_m",
        "material_md_end_m", *FEATURES,
    ]].merge(truth, on="aligned_sample_id", how="left", validate="one_to_one")
    frame["_time"] = pd.to_datetime(frame.observed_at, utc=True, errors="coerce")
    frame = frame.sort_values(["root_roll_id", "material_md_start_m", "aligned_sample_id"]).reset_index(drop=True)
    records: list[pd.DataFrame] = []
    for (roll, phase), source in frame.groupby(["root_roll_id", "synthetic_phase"], sort=False, dropna=False):
        source = source.sort_values(["material_md_start_m", "aligned_sample_id"]).reset_index(drop=True)
        for offset in range(0, len(source), 5):
            group = source.iloc[offset:offset + 5].copy()
            if len(group) != 5:
                continue
            md_adjacent = np.allclose(
                group.material_md_end_m.to_numpy(dtype=float)[:-1],
                group.material_md_start_m.to_numpy(dtype=float)[1:], rtol=0.0, atol=1e-9,
            )
            times = group._time
            conditions_present = group[list(FEATURES)].notna().all(axis=None)
            if not md_adjacent or times.isna().any() or not times.is_monotonic_increasing or not conditions_present:
                continue
            group_number = offset // 5
            subgroup = f"SPC-{roll}-{str(phase).upper()}-{group_number:03d}"
            event_time = times.max().isoformat()
            group["sampling_event_id"] = subgroup
            group["subgroup_id"] = subgroup
            group["specimen_id"] = group.aligned_sample_id
            group["sampled_at"] = event_time
            group["available_at"] = event_time
            group["spc_condition_code"] = 1.0
            group["baseline_candidate"] = (
                group.dataset_split.eq("train") & group.synthetic_phase.eq("stable")
            ).astype(int)
            group["monitoring_eligible"] = group.dataset_split.isin(["validation", "test"]).astype(int)
            records.append(group[list(SPC_SAMPLE_COLUMNS)])
    if not records:
        return pd.DataFrame(columns=SPC_SAMPLE_COLUMNS)
    result = pd.concat(records, ignore_index=True)
    if result.aligned_sample_id.duplicated().any() or result.specimen_id.duplicated().any():
        raise SourceValidationError([ValidationIssue(
            "SPC_SAMPLE_REUSED", "aligned_sample_id", None,
            "Synthetic SPC specimens must belong to one non-overlapping subgroup",
        )])
    return result.sort_values(["sampled_at", "root_roll_id", "subgroup_id", "specimen_id"]).reset_index(drop=True)


def _align_process(tables: dict[str, pd.DataFrame], config: PipelineConfig):
    segments = tables["process_segments.csv"].copy()
    trace = tables["process_traceability.csv"]
    trace_map = trace.set_index("process_segment_id").source_aligned_sample_id.to_dict()
    anchors = segments.loc[segments.station.eq("lamination")].copy().sort_values(["root_roll_id", "material_md_start_m"])
    rows, lineages, exclusions = [], [], []
    groups = {}
    for (roll, station), group in segments.groupby(["root_roll_id", "station"], sort=False):
        ordered = group.sort_values("material_md_start_m")
        groups[(roll, station)] = {
            "starts": ordered.material_md_start_m.to_numpy(dtype=float),
            "ends": ordered.material_md_end_m.to_numpy(dtype=float),
            "ids": ordered.process_segment_id.astype(str).to_numpy(),
            "values": {column: pd.to_numeric(ordered[column], errors="coerce").to_numpy(dtype=float) for column in STATION_FEATURES[station]},
        }
    for anchor in anchors.itertuples(index=False):
        aligned_id = trace_map.get(anchor.process_segment_id)
        record = {
            "aligned_sample_id": aligned_id,
            "segment_id": anchor.process_segment_id,
            "root_roll_id": anchor.root_roll_id,
            "product_id": anchor.product_id,
            "dataset_split": anchor.dataset_split,
            "timestamp": anchor.completed_at,
            "material_md_start_m": float(anchor.material_md_start_m),
            "material_md_end_m": float(anchor.material_md_end_m),
            "process_phase": anchor.process_phase_observed,
        }
        source_ids = {}
        valid = True
        for station, columns in STATION_FEATURES.items():
            values, coverage, ids = _overlap_arrays(float(anchor.material_md_start_m), float(anchor.material_md_end_m), groups[(anchor.root_roll_id, station)], columns)
            record.update(values)
            record[f"{station}_coverage"] = coverage
            source_ids[station] = ids
            if coverage + 1e-9 < config.coverage_threshold:
                valid = False
                exclusions.append({"aligned_sample_id": aligned_id, "target": None, "code": "ALIGNMENT_INCOMPLETE", "detail": f"{station} coverage={coverage:.6f}"})
        record["alignment_valid"] = int(valid)
        rows.append(record)
        lineages.append({
            "aligned_sample_id": aligned_id,
            "coating_source_ids": json.dumps(source_ids["coating"]),
            "curing_source_ids": json.dumps(source_ids["curing"]),
            "lamination_source_ids": json.dumps(source_ids["lamination"]),
            "alignment_version": config.alignment_version,
        })
    canonical = pd.DataFrame(rows)
    if canonical.aligned_sample_id.isna().any() or canonical.aligned_sample_id.duplicated().any():
        raise SourceValidationError([ValidationIssue("ALIGNED_ID_INVALID", "aligned_sample_id", None, "Aligned IDs must be present and unique")])
    return canonical, pd.DataFrame(lineages), pd.DataFrame(exclusions, columns=["aligned_sample_id", "target", "code", "detail"])


def _overlap_arrays(anchor_start: float, anchor_end: float, group: dict, columns: Iterable[str]):
    starts, ends = group["starts"], group["ends"]
    left = int(np.searchsorted(ends, anchor_start, side="right"))
    right = int(np.searchsorted(starts, anchor_end, side="left"))
    local_starts, local_ends = starts[left:right], ends[left:right]
    weights = np.maximum(0.0, np.minimum(anchor_end, local_ends) - np.maximum(anchor_start, local_starts))
    selected = weights > 0
    length = anchor_end - anchor_start
    coverage = float(weights[selected].sum() / length) if length > 0 else 0.0
    values = {}
    for column in columns:
        numeric = group["values"][column][left:right]
        valid = selected & np.isfinite(numeric)
        values[column] = float(np.average(numeric[valid], weights=weights[valid])) if valid.any() else np.nan
    ids = tuple(group["ids"][left:right][selected])
    return values, coverage, ids


def _attach_synthetic(canonical: pd.DataFrame, tables: dict[str, pd.DataFrame]):
    truth = tables["quality_timeseries.csv"][["aligned_sample_id", *TARGETS]].copy()
    merged = canonical.merge(truth, on="aligned_sample_id", how="left", validate="one_to_one")
    for target in TARGETS:
        merged[f"{target}_available"] = (merged[target].notna() & merged.alignment_valid.eq(1)).astype(int)
    lineage = pd.DataFrame({"aligned_sample_id": merged.aligned_sample_id, "label_source": "synthetic_ground_truth", "inspection_ids": "[]"})
    return merged, lineage, pd.DataFrame(columns=["aligned_sample_id", "target", "code", "detail"])


def _attach_inspections(canonical: pd.DataFrame, tables: dict[str, pd.DataFrame]):
    inspections = tables["quality_inspection.csv"].copy()
    specs = tables["quality_specifications.csv"].copy()
    merged = canonical.copy()
    exclusions: list[dict] = []
    lineage_by_id: dict[str, list[str]] = {value: [] for value in merged.aligned_sample_id}
    spec_lookup = _spec_lookup(specs)
    for target in TARGETS:
        availability = TARGET_AVAILABILITY[target]
        value_column = INSPECTION_VALUE[target]
        candidates = inspections.loc[
            inspections.label_scope.eq("segment")
            & inspections[availability].eq(1)
            & inspections[value_column].notna()
            & ~inspections.validity_status.isin(["invalid", "superseded"])
        ].copy()
        if target == "appearance_ng":
            conflict = candidates.appearance_spec_pass_flag.notna() & candidates.disposition_code.isna() & (candidates.appearance_spec_pass_flag.astype(float) != 1 - candidates.appearance_ng_flag.astype(float))
            for aligned_id in candidates.loc[conflict, "aligned_sample_id"].unique():
                exclusions.append({"aligned_sample_id": aligned_id, "target": target, "code": "APPEARANCE_FLAG_CONFLICT", "detail": "NG and pass flags disagree without disposition"})
            candidates = candidates.loc[~candidates.aligned_sample_id.isin(candidates.loc[conflict, "aligned_sample_id"])].copy()
        counts = candidates.groupby("aligned_sample_id").aligned_sample_id.transform("size")
        singles = candidates.loc[counts.eq(1)].copy()
        selected = _select_spec_valid_rows(singles, target, value_column, spec_lookup, exclusions)
        multiples = candidates.loc[counts.gt(1)]
        for aligned_id, group in multiples.groupby("aligned_sample_id", sort=False):
            retests = group.loc[group.is_retest.eq(1) & group.parent_inspection_id.notna() & group.retest_reason.notna()]
            if retests.empty:
                exclusions.append({"aligned_sample_id": aligned_id, "target": target, "code": "DUPLICATE_INSPECTION_AMBIGUOUS", "detail": "Multiple valid inspections without retest relation"})
                continue
            chosen = retests.assign(_completed=pd.to_datetime(retests.completed_at, utc=True)).sort_values("_completed").iloc[[-1]]
            selected.extend(_select_spec_valid_rows(chosen, target, value_column, spec_lookup, exclusions))
        values = {aligned_id: value for aligned_id, value, _ in selected}
        merged[target] = merged.aligned_sample_id.map(values)
        merged[f"{target}_available"] = (merged[target].notna() & merged.alignment_valid.eq(1)).astype(int)
        for aligned_id, _, inspection_id in selected:
            lineage_by_id[aligned_id].append(str(inspection_id))
    lineage = pd.DataFrame({
        "aligned_sample_id": merged.aligned_sample_id,
        "label_source": "simulated_inspection",
        "inspection_ids": [json.dumps(lineage_by_id[value]) for value in merged.aligned_sample_id],
    })
    return merged, lineage, pd.DataFrame(exclusions, columns=["aligned_sample_id", "target", "code", "detail"])


def _select_spec_valid_rows(rows: pd.DataFrame, target: str, value_column: str, lookup: dict, exclusions: list[dict]):
    selected = []
    for row in rows.itertuples(index=False):
        key = (row.product_id, row.spec_version, target)
        at = pd.to_datetime(row.completed_at, utc=True)
        active = [(start, end, unit) for start, end, unit in lookup.get(key, ()) if start <= at and (end is None or at < end)]
        if len(active) != 1 or not isinstance(active[0][2], str) or not active[0][2]:
            exclusions.append({"aligned_sample_id": row.aligned_sample_id, "target": target, "code": "SPEC_NOT_FOUND", "detail": "No unique effective specification"})
            continue
        selected.append((row.aligned_sample_id, getattr(row, value_column), row.inspection_id))
    return selected


def _spec_lookup(specs: pd.DataFrame) -> dict[tuple[str, str, str], list[tuple[pd.Timestamp, pd.Timestamp | None, str]]]:
    lookup: dict[tuple[str, str, str], list[tuple[pd.Timestamp, pd.Timestamp | None, str]]] = {}
    for row in specs.itertuples(index=False):
        start = pd.to_datetime(row.effective_from, utc=True)
        parsed_end = pd.to_datetime(row.effective_to, utc=True, errors="coerce")
        end = None if pd.isna(parsed_end) else parsed_end
        lookup.setdefault((row.product_id, row.spec_version, row.characteristic), []).append((start, end, row.unit))
    return lookup


def audit_feature_allowlist(features: Iterable[str]) -> tuple[str, ...]:
    values = tuple(features)
    forbidden_exact = {*TARGETS, "root_roll_id", "product_batch", "product_id", "dataset_split", "timestamp", "process_phase"}
    rejected = [name for name in values if name in forbidden_exact or name.startswith(("drift_", "spec_", "pred_")) or name.endswith(("_pass_flag", "_available"))]
    unknown = [name for name in values if name not in FEATURES]
    if rejected or unknown or len(set(values)) != len(values):
        raise ValueError("LEAKAGE_FEATURES_REJECTED: " + ",".join(sorted(set(rejected + unknown))))
    return values


def _manifest(config, profile, metadata, specifications, canonical, projections, splits, lineage, exclusions,
              spc_samples):
    source_hashes = dict(sorted(metadata["csv_sha256"].items()))
    projection_rows = {target: len(frame) for target, frame in projections.items()}
    identity = {
        "profile": profile, "source_hashes": source_hashes, "schema_version": config.schema_version,
        "feature_version": config.feature_version, "features": list(FEATURES), "targets": list(TARGETS),
        "coverage_threshold": config.coverage_threshold, "split_roll_ids": splits,
        "projection_rows": projection_rows,
    }
    dataset_version = sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    quality_specs = {}
    for row in specifications.loc[specifications.characteristic.isin(TARGETS)].itertuples(index=False):
        values = {"unit": row.unit, "test_method": row.test_method, "spec_version": row.spec_version}
        for name in ("lsl", "usl", "target"):
            value = getattr(row, name)
            if pd.notna(value):
                values[name] = float(value)
        quality_specs[row.characteristic] = values
    result = {
        "manifest_schema": "fccl-canonical-dataset-1.0",
        "dataset_version": dataset_version,
        "profile": profile,
        "data_classification": "synthetic_test_line_demonstration_only",
        "limitations": metadata.get("limitations", []),
        "schema_version": config.schema_version,
        "spec_version": metadata.get("spec_version"),
        "alignment_version": config.alignment_version,
        "coverage_threshold": config.coverage_threshold,
        "feature_version": config.feature_version,
        "feature_names": list(FEATURES),
        "feature_units": FEATURE_UNITS,
        "target_units": TARGET_UNITS,
        "quality_specs": quality_specs,
        "source_hashes": source_hashes,
        "split_roll_ids": splits,
        "canonical_rows": len(canonical),
        "projection_rows": projection_rows,
        "lineage_rows": len(lineage),
        "exclusion_counts": exclusions.code.value_counts().sort_index().to_dict() if not exclusions.empty else {},
    }
    if not spc_samples.empty:
        validation = spc_samples.loc[spc_samples.dataset_split.eq("validation")]
        result["spc_profile"] = {
            "profile_id": "canonical-synthetic-ground-truth-xbar",
            "version": SPC_PROFILE_VERSION,
            "source_file": "spc_samples.csv",
            "classification": "synthetic_demonstration_only",
            "product": str(canonical.product_id.iloc[0]),
            "recipe": "synthetic-v2",
            "subgroup_size": 5,
            "minimum_history_groups": 25,
            "baseline_policy": "earliest-25-complete-train-stable-groups",
            "monitoring_policy": "validation-and-test-only",
            "monitoring_origin": str(validation.sampled_at.min()),
            "interval_seconds": 900.0,
            "conditions": [["spc_condition_code", 1.0]],
            "condition_tolerance": 0.0,
            "environment_ranges": [["ambient_temp_c", 15.0, 35.0], ["ambient_rh_pct", 20.0, 80.0]],
            "units": {target: TARGET_UNITS[target] for target in TARGETS[:-1]},
            "phase_metadata_role": "spc_validation_only_not_model_feature",
        }
    return result


def _write_result(result: BuildResult) -> None:
    output = result.output_dir
    output.mkdir(parents=True, exist_ok=True)
    projections_dir = output / "projections"
    projections_dir.mkdir(exist_ok=True)
    result.canonical.sort_values("aligned_sample_id").to_csv(output / "canonical.csv", index=False, lineterminator="\n")
    result.lineage.sort_values("aligned_sample_id").to_csv(output / "lineage.csv", index=False, lineterminator="\n")
    result.exclusions.sort_values(["aligned_sample_id", "target"], na_position="last").to_csv(output / "exclusions.csv", index=False, lineterminator="\n")
    if not result.spc_samples.empty:
        result.spc_samples.to_csv(output / "spc_samples.csv", index=False, lineterminator="\n")
    for target, frame in result.projections.items():
        frame.to_csv(projections_dir / f"{target}.csv", index=False, lineterminator="\n")
    dictionary = {
        "profile": result.profile,
        "grain": "one completed lamination MD half-open interval per row",
        "features": [{"name": name, "unit": FEATURE_UNITS[name], "role": "model_feature"} for name in FEATURES],
        "targets": [{"name": name, "unit": TARGET_UNITS[name], "role": "target_only"} for name in TARGETS],
        "identifiers": ["aligned_sample_id", "root_roll_id"],
        "split": "dataset_split; immutable complete-roll time split",
    }
    if not result.spc_samples.empty:
        dictionary["spc_sidecar"] = {
            "file": "spc_samples.csv",
            "grain": "one synthetic specimen membership per row; five specimens per rational subgroup",
            "classification": "synthetic demonstration only; not factory sampling evidence",
            "fields": list(SPC_SAMPLE_COLUMNS),
            "baseline": "earliest 25 complete train+stable subgroups",
            "monitoring": "validation and test subgroups only",
        }
    (output / "data_dictionary.json").write_text(json.dumps(dictionary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [output / "canonical.csv", output / "lineage.csv", output / "exclusions.csv", output / "data_dictionary.json", *sorted(projections_dir.glob("*.csv"))]
    if not result.spc_samples.empty:
        files.append(output / "spc_samples.csv")
    manifest = dict(result.manifest)
    manifest["output_hashes"] = {str(path.relative_to(output)).replace("\\", "/"): file_sha256(path) for path in files}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

