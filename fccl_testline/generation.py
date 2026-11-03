from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import SCHEMA_VERSION
from .config import load_product_recipe


GENERATOR_VERSION = "3.0.0"
TRAINING_SEED = 314159
REFERENCE_SEED = 271828
DEMO_SEEDS = (9001, 9002, 9003, 9004, 9005, 9006, 9007)
SCENARIOS = ("stable", "thickness_increase", "thickness_decrease", "temperature_drop", "airflow_decay", "pressure_drift", "compound_drift")
TARGETS = ("peel_strength_n_mm", "dimensional_stability_md_pct", "dimensional_stability_td_pct", "heat_resistance_c")


@dataclass(frozen=True)
class GenerationConfig:
    seed: int = TRAINING_SEED
    rolls: int = 200
    segments_per_roll: int = 100
    start: str = "2026-01-01T00:00:00+00:00"


def dataframe_sha256(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


def _split(index: int, rolls: int) -> str:
    if rolls == 200:
        return "train" if index < 120 else "validation" if index < 160 else "test"
    a, b = round(rolls * .6), round(rolls * .8)
    return "train" if index < a else "validation" if index < b else "test"


def generate_v3(config: GenerationConfig = GenerationConfig()) -> tuple[pd.DataFrame, pd.DataFrame]:
    if config.seed in DEMO_SEEDS:
        raise ValueError("DEMO_SEED_FORBIDDEN_FOR_TRAINING")
    rng = np.random.default_rng(config.seed)
    rows: list[dict[str, Any]] = []; drift_rows: list[dict[str, Any]] = []
    start = pd.Timestamp(config.start)
    for r in range(config.rolls):
        roll_id = f"V3-ROLL-{r+1:04d}"; split = _split(r, config.rolls)
        scenario = SCENARIOS[r % len(SCENARIOS)] if r >= max(1, config.rolls // 5) else "stable"
        roll_bias = rng.normal(0, .10)
        drift_start = int(config.segments_per_roll * .45)
        if scenario != "stable":
            drift_rows.append({"root_roll_id": roll_id, "scenario": scenario, "start_segment_index": drift_start, "split": split, "truth_only": 1})
        for s in range(config.segments_per_roll):
            progress = max(0.0, (s - drift_start) / max(1, config.segments_per_roll - drift_start - 1))
            thickness_shift = progress * (2.4 if scenario == "thickness_increase" else -2.4 if scenario == "thickness_decrease" else (1.5 if scenario == "compound_drift" else 0))
            temp_shift = progress * (-7.0 if scenario == "temperature_drop" else -4.0 if scenario == "compound_drift" else 0)
            airflow_shift = progress * (-420 if scenario == "airflow_decay" else -250 if scenario == "compound_drift" else 0)
            pressure_shift = progress * (-.40 if scenario == "pressure_drift" else -.22 if scenario == "compound_drift" else 0)
            line = 4.8 + rng.normal(0, .07); gap = 28 + rng.normal(0, .22)
            curing_temp = 171 + temp_shift + rng.normal(0, .45); airflow = 2100 + airflow_shift + rng.normal(0, 28)
            pressure = 2.55 + pressure_shift + rng.normal(0, .025)
            coating_temp = 82 + rng.normal(0, .35); viscosity = 1180 + rng.normal(0, 22)
            base_thickness = 25 + .55 * (gap - 28) - .28 * (line - 4.8) + thickness_shift + roll_bias
            points = base_thickness + rng.normal(0, .12, 5)
            thickness = float(points.mean())
            timestamp = start + pd.Timedelta(minutes=(r * config.segments_per_roll + s) * 2)
            coating_out = timestamp; curing_out = coating_out + pd.Timedelta(minutes=12.5); lam_out = curing_out + pd.Timedelta(minutes=18); quality_at = lam_out + pd.Timedelta(minutes=2)
            peel = 1.34 + .025*(curing_temp-171) + .00009*(airflow-2100) + .10*(pressure-2.55) - .018*abs(thickness-25) + rng.normal(0,.025)
            md = .070 + .004*abs(curing_temp-171) + .010*abs(pressure-2.55) + .004*abs(thickness-25) + rng.normal(0,.006)
            td = .060 + .0035*abs(curing_temp-171) + .009*abs(pressure-2.55) + .003*abs(thickness-25) + rng.normal(0,.005)
            heat = 241 + .72*(curing_temp-171) + .0015*(airflow-2100) + .15*(coating_temp-82) + rng.normal(0,1.5)
            row = {
                "schema_version": SCHEMA_VERSION, "generator_version": GENERATOR_VERSION,
                "root_roll_id": roll_id, "segment_id": f"{roll_id}-SEG-{s+1:03d}", "segment_index": s,
                "split": split, "product_id": "FCCL-DEMO-001", "recipe_id": "SIM-RECIPE-3.0",
                "material_md_start_m": float(s), "material_md_end_m": float(s+1),
                "coating_available_at": coating_out.isoformat(), "curing_available_at": curing_out.isoformat(),
                "lamination_available_at": lam_out.isoformat(), "quality_available_at": quality_at.isoformat(),
                "line_speed_setpoint_m_min": 4.8, "line_speed_actual_m_min": line,
                "coating_gap_setpoint_um": 28.0, "coating_gap_actual_um": gap,
                "coating_temp_setpoint_c": 82.0, "coating_temp_actual_c": coating_temp,
                "coating_viscosity_setpoint_mpa_s": 1180.0, "coating_viscosity_actual_mpa_s": viscosity,
                "dry_thickness_1_um": points[0], "dry_thickness_2_um": points[1], "dry_thickness_3_um": points[2], "dry_thickness_4_um": points[3], "dry_thickness_5_um": points[4], "dry_thickness_mean_um": thickness,
                "curing_temp_setpoint_c": 171.0, "curing_temp_actual_c": curing_temp,
                "exhaust_airflow_setpoint_m3_h": 2100.0, "exhaust_airflow_actual_m3_h": airflow,
                "curing_time_setpoint_min": 12.5, "curing_time_actual_min": 12.5 + rng.normal(0,.08),
                "lamination_temp_setpoint_c": 181.0, "lamination_temp_actual_c": 181 + rng.normal(0,.4),
                "lamination_pressure_setpoint_mpa": 2.55, "lamination_pressure_actual_mpa": pressure,
                "lamination_time_setpoint_min": 18.0, "lamination_time_actual_min": 18 + rng.normal(0,.10),
                "ambient_temp_c": 23 + rng.normal(0,1), "ambient_rh_pct": 52 + rng.normal(0,3),
                "peel_strength_n_mm": peel, "dimensional_stability_md_pct": md,
                "dimensional_stability_td_pct": td, "heat_resistance_c": heat,
                "peel_label_available": 1, "md_label_available": 1, "td_label_available": 1, "heat_label_available": 1,
            }
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(drift_rows)


def stable_reference(rows: int = 500, seed: int = REFERENCE_SEED) -> pd.DataFrame:
    frame, _ = generate_v3(GenerationConfig(seed=seed, rolls=max(5, (rows + 99)//100), segments_per_roll=100))
    return frame.iloc[:rows].assign(reference_version="SIM-RECIPE-3.0-STABLE-1")


def write_v3(output: Path, config: GenerationConfig = GenerationConfig()) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    canonical, drift = generate_v3(config); reference = stable_reference()
    paths = {"canonical_v3.csv": canonical, "drift_ground_truth.csv": drift, "stable_reference.csv": reference}
    hashes: dict[str, str] = {}
    for name, frame in paths.items():
        path = output / name; frame.to_csv(path, index=False, lineterminator="\n"); hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    recipe = load_product_recipe()
    manifest = {
        "schema_version": SCHEMA_VERSION, "generator_version": GENERATOR_VERSION,
        "seed": config.seed, "reference_seed": REFERENCE_SEED, "forbidden_demo_seeds": list(DEMO_SEEDS),
        "product_id": "FCCL-DEMO-001", "recipe_id": "SIM-RECIPE-3.0",
        "rolls": int(canonical.root_roll_id.nunique()), "segments": len(canonical),
        "split_rolls": canonical.groupby("split").root_roll_id.nunique().to_dict(),
        "files": hashes, "targets": list(TARGETS), "appearance_included": False,
        "runtime_data_included": False, "v2_included": False,
        "range_contract": recipe, "actual_ranges": {c: {"min": float(canonical[c].min()), "max": float(canonical[c].max())} for c in canonical.select_dtypes("number")},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return manifest
