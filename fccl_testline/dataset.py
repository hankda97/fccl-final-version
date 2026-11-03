from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from . import SCHEMA_VERSION
from .generation import TARGETS


FEATURE_ALLOWLIST = (
    "line_speed_actual_m_min", "coating_gap_actual_um", "coating_temp_actual_c",
    "coating_viscosity_actual_mpa_s", "dry_thickness_mean_um",
    "curing_temp_actual_c", "exhaust_airflow_actual_m3_h", "curing_time_actual_min",
    "lamination_temp_actual_c", "lamination_pressure_actual_mpa", "lamination_time_actual_min",
    "ambient_temp_c", "ambient_rh_pct",
)
IDENTITY_COLUMNS = ("root_roll_id", "segment_id", "split", "quality_available_at")
FORBIDDEN_EXACT = frozenset(("appearance_ng", "appearance_ng_flag", "root_roll_id", "segment_id", "quality_available_at"))
FORBIDDEN_FRAGMENTS = ("pass_flag", "spec_", "drift_", "scenario", "_available_at")


def validate_allowlist(columns: tuple[str, ...] = FEATURE_ALLOWLIST) -> None:
    targets = set(TARGETS)
    for column in columns:
        if column in targets or column in FORBIDDEN_EXACT or any(token in column for token in FORBIDDEN_FRAGMENTS):
            raise ValueError(f"LEAKAGE_FEATURE:{column}")


def build_target_dataset(canonical: pd.DataFrame, target: str) -> pd.DataFrame:
    if target not in TARGETS:
        raise ValueError(f"UNSUPPORTED_TARGET:{target}")
    validate_allowlist()
    required = {*FEATURE_ALLOWLIST, *IDENTITY_COLUMNS, target}
    missing = required - set(canonical)
    if missing:
        raise ValueError("MISSING_CANONICAL_COLUMNS:" + ",".join(sorted(missing)))
    frame = canonical.loc[:, [*IDENTITY_COLUMNS, *FEATURE_ALLOWLIST, target]].copy()
    frame = frame.dropna(subset=[*FEATURE_ALLOWLIST, target])
    return frame


def write_model_dataset(canonical_path: Path, output: Path) -> dict[str, Any]:
    canonical = pd.read_csv(canonical_path)
    output.mkdir(parents=True, exist_ok=True); projections = output / "projections"; projections.mkdir(exist_ok=True)
    files: dict[str, Any] = {}; target_rows: dict[str, int] = {}
    for target in TARGETS:
        frame = build_target_dataset(canonical, target); path = projections / f"{target}.csv"
        frame.to_csv(path, index=False, lineterminator="\n")
        files[str(path.relative_to(output))] = hashlib.sha256(path.read_bytes()).hexdigest(); target_rows[target] = len(frame)
    manifest = {"schema_version": SCHEMA_VERSION, "dataset_version": "canonical-v3.0", "source": str(canonical_path), "features": list(FEATURE_ALLOWLIST), "targets": list(TARGETS), "target_rows": target_rows, "files": files, "leakage_check": "passed"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest
