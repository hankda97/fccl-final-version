"""Strict validation for the seven synthetic v2 source tables."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping

import pandas as pd


SOURCE_FILES = (
    "roll_master.csv",
    "process_segments.csv",
    "process_traceability.csv",
    "quality_timeseries.csv",
    "quality_inspection.csv",
    "quality_specifications.csv",
    "drift_ground_truth.csv",
)

REQUIRED_COLUMNS = {
    "roll_master.csv": {"root_roll_id", "dataset_split", "roll_start_at", "roll_end_at", "roll_length_m"},
    "process_segments.csv": {"process_segment_id", "root_roll_id", "station", "material_md_start_m", "material_md_end_m", "completed_at"},
    "process_traceability.csv": {"trace_id", "process_segment_id", "root_roll_id", "station", "source_aligned_sample_id"},
    "quality_timeseries.csv": {"aligned_sample_id", "segment_id", "root_roll_id", "dataset_split", "timestamp"},
    "quality_inspection.csv": {"inspection_id", "sampling_event_id", "root_roll_id", "aligned_sample_id", "label_scope", "validity_status"},
    "quality_specifications.csv": {"product_id", "spec_version", "characteristic", "unit", "effective_from"},
    "drift_ground_truth.csv": {"drift_event_id", "root_roll_id", "model_feature_allowed"},
}

UNIQUE_KEYS = {
    "roll_master.csv": ("root_roll_id",),
    "process_segments.csv": ("process_segment_id",),
    "process_traceability.csv": ("trace_id",),
    "quality_timeseries.csv": ("aligned_sample_id",),
    "quality_inspection.csv": ("inspection_id",),
    "quality_specifications.csv": ("product_id", "spec_version", "characteristic"),
    "drift_ground_truth.csv": ("drift_event_id",),
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    field: str | None
    row: int | None
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


class SourceValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__(json.dumps([issue.to_dict() for issue in issues], ensure_ascii=False))


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_sources(source_dir: Path | str) -> tuple[dict[str, pd.DataFrame], dict]:
    root = Path(source_dir).resolve()
    issues: list[ValidationIssue] = []
    metadata_path = root / "metadata.json"
    if not metadata_path.is_file():
        raise SourceValidationError([ValidationIssue("MISSING_METADATA", "metadata.json", None, "metadata.json is required")])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("schema_version") != "2.0.0":
        issues.append(ValidationIssue("SCHEMA_VERSION_MISMATCH", "schema_version", None, "Expected schema_version 2.0.0"))
    tables: dict[str, pd.DataFrame] = {}
    for name in SOURCE_FILES:
        path = root / name
        if not path.is_file():
            issues.append(ValidationIssue("MISSING_TABLE", name, None, f"Missing source table: {name}"))
            continue
        expected_hash = metadata.get("csv_sha256", {}).get(name)
        actual_hash = file_sha256(path)
        if expected_hash != actual_hash:
            issues.append(ValidationIssue("HASH_MISMATCH", name, None, f"Expected {expected_hash}, got {actual_hash}"))
        table = pd.read_csv(path)
        tables[name] = table
    if issues:
        raise SourceValidationError(issues)
    validate_loaded_tables(tables, metadata)
    return tables, metadata


def validate_loaded_tables(tables: Mapping[str, pd.DataFrame], metadata: dict) -> None:
    issues: list[ValidationIssue] = []
    for name in SOURCE_FILES:
        if name not in tables:
            issues.append(ValidationIssue("MISSING_TABLE", name, None, f"Missing source table: {name}"))
            continue
        table = tables[name]
        missing = sorted(REQUIRED_COLUMNS[name] - set(table.columns))
        for column in missing:
            issues.append(ValidationIssue("MISSING_COLUMN", column, None, f"{name} is missing {column}"))
        if not missing:
            key = list(UNIQUE_KEYS[name])
            duplicated = table.duplicated(key, keep=False)
            if duplicated.any():
                issues.append(ValidationIssue("DUPLICATE_KEY", ",".join(key), int(duplicated.idxmax()), f"Duplicate key in {name}"))
    if not issues:
        _validate_relations(tables, metadata, issues)
    if issues:
        raise SourceValidationError(issues)


def _validate_relations(tables: Mapping[str, pd.DataFrame], metadata: dict, issues: list[ValidationIssue]) -> None:
    rolls = tables["roll_master.csv"]
    roll_ids = set(rolls.root_roll_id)
    for name, table in tables.items():
        if name == "quality_specifications.csv" or "root_roll_id" not in table:
            continue
        missing = set(table.root_roll_id.dropna()) - roll_ids
        if missing:
            issues.append(ValidationIssue("FOREIGN_KEY_MISSING", "root_roll_id", None, f"{name} references {sorted(missing)[:3]}"))
    segments = tables["process_segments.csv"]
    trace = tables["process_traceability.csv"]
    missing_segments = set(trace.process_segment_id) - set(segments.process_segment_id)
    if missing_segments:
        issues.append(ValidationIssue("FOREIGN_KEY_MISSING", "process_segment_id", None, "Traceability references missing segments"))
    invalid_interval = pd.to_numeric(segments.material_md_end_m, errors="coerce") <= pd.to_numeric(segments.material_md_start_m, errors="coerce")
    if invalid_interval.any():
        issues.append(ValidationIssue("INVALID_INTERVAL", "material_md_start_m/material_md_end_m", int(invalid_interval.idxmax()), "MD interval must satisfy end > start"))
    lengths = rolls.set_index("root_roll_id").roll_length_m.astype(float)
    segment_lengths = segments.root_roll_id.map(lengths)
    too_long = (pd.to_numeric(segments.material_md_start_m, errors="coerce") < 0) | (
        segment_lengths.notna() & (pd.to_numeric(segments.material_md_end_m, errors="coerce") > segment_lengths + 1e-6)
    )
    if too_long.any():
        issues.append(ValidationIssue("INTERVAL_OUT_OF_ROLL", "material_md_end_m", int(too_long.idxmax()), "Segment lies outside roll length"))
    ordered = segments.sort_values(["root_roll_id", "station", "material_md_start_m"])
    previous_end = ordered.groupby(["root_roll_id", "station"]).material_md_end_m.shift()
    overlap = ordered.material_md_start_m < previous_end - 1e-6
    if overlap.any():
        issues.append(ValidationIssue("SOURCE_INTERVAL_OVERLAP", "material_md_start_m", int(overlap.idxmax()), "Source station intervals overlap"))
    for name, table in tables.items():
        for column in (c for c in table.columns if c.endswith("_at") or c == "timestamp"):
            values = pd.to_datetime(table[column], errors="coerce", utc=True)
            if table[column].notna().any() and values[table[column].notna()].isna().any():
                issues.append(ValidationIssue("INVALID_TIMESTAMP", column, None, f"{name}.{column} contains invalid timezone timestamps"))
    row_counts = metadata.get("row_counts", {})
    for name, table in tables.items():
        if row_counts.get(name) != len(table):
            issues.append(ValidationIssue("ROW_COUNT_MISMATCH", name, None, f"metadata={row_counts.get(name)}, actual={len(table)}"))
    validate_roll_splits(rolls)


def validate_roll_splits(rolls: pd.DataFrame) -> dict[str, list[str]]:
    if rolls.root_roll_id.duplicated().any():
        raise SourceValidationError([ValidationIssue("ROLL_CROSSES_SPLIT", "root_roll_id", None, "A roll appears more than once")])
    expected = {"train": 120, "validation": 40, "test": 40}
    actual = rolls.groupby("dataset_split").root_roll_id.nunique().to_dict()
    if actual != expected:
        raise SourceValidationError([ValidationIssue("SPLIT_COUNT_MISMATCH", "dataset_split", None, f"Expected {expected}, got {actual}")])
    starts = pd.to_datetime(rolls.roll_start_at, utc=True)
    ranges = {}
    for split in ("train", "validation", "test"):
        subset = rolls.loc[rolls.dataset_split.eq(split)].copy()
        subset["_start"] = starts.loc[subset.index]
        ranges[split] = (subset._start.min(), subset._start.max())
    if not (ranges["train"][1] < ranges["validation"][0] < ranges["test"][0]):
        raise SourceValidationError([ValidationIssue("SPLIT_TIME_ORDER", "roll_start_at", None, "Splits are not ordered train < validation < test")])
    return {split: sorted(rolls.loc[rolls.dataset_split.eq(split), "root_roll_id"].tolist()) for split in expected}

