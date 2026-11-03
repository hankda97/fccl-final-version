"""Shared immutable configuration for dataset building and model training."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TARGETS = (
    "peel_strength_n_mm",
    "dimensional_stability_md_pct",
    "dimensional_stability_td_pct",
    "heat_resistance_c",
    "appearance_ng",
)

FEATURES = (
    "ambient_temp_c",
    "ambient_rh_pct",
    "line_speed_m_min",
    "coating_temp_c",
    "coating_gap_um",
    "coating_viscosity_mpa_s",
    "curing_temp_c",
    "curing_time_min",
    "lamination_temp_c",
    "lamination_pressure_mpa",
    "lamination_time_s",
)

FEATURE_UNITS = {
    "ambient_temp_c": "°C",
    "ambient_rh_pct": "%RH",
    "line_speed_m_min": "m/min",
    "coating_temp_c": "°C",
    "coating_gap_um": "μm",
    "coating_viscosity_mpa_s": "mPa·s",
    "curing_temp_c": "°C",
    "curing_time_min": "min",
    "lamination_temp_c": "°C",
    "lamination_pressure_mpa": "MPa",
    "lamination_time_s": "s",
}

TARGET_UNITS = {
    "peel_strength_n_mm": "N/mm",
    "dimensional_stability_md_pct": "%",
    "dimensional_stability_td_pct": "%",
    "heat_resistance_c": "°C",
    "appearance_ng": "class/probability",
}

PROFILES = ("synthetic-ground-truth-v2", "simulated-inspection-v2")


@dataclass(frozen=True)
class PipelineConfig:
    project_root: Path
    source_dir: Path
    dataset_dir: Path
    artifact_dir: Path
    seed: int = 42
    coverage_threshold: float = 0.98
    schema_version: str = "2.0.0"
    alignment_version: str = "md-overlap-v1"
    feature_version: str = "fccl-process-features-v1"
    preprocessing_version: str = "median-imputer-v1"

    @classmethod
    def default(cls, project_root: Path | str | None = None) -> "PipelineConfig":
        root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
        return cls(
            project_root=root,
            source_dir=root / "generated_data" / "v2",
            dataset_dir=root / "generated_data" / "model_dataset_v2",
            artifact_dir=root / "artifacts" / "synthetic_v2",
        )

