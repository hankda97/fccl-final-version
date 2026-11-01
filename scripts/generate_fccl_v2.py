"""Generate the deterministic seven-table FCCL synthetic dataset v2.

The output is synthetic test-line data. Its specifications and process ranges are
demonstration assumptions, not factory standards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
N_ROLLS = 200
SEGMENTS_PER_ROLL = 100
ROLL_LENGTH_M = 500.0
PRODUCT_ID = "FCCL-DEMO-001"
SPEC_VERSION = "SIM-2.0"
SCHEMA_VERSION = "2.0.0"
GENERATOR_VERSION = "2.0.0"
BASE_TIME = pd.Timestamp("2026-01-01T08:00:00+08:00")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _phase_schedule(rng: np.random.Generator) -> list[str]:
    phases: list[str] = []
    for counts in ((45, 45, 30), (10, 15, 15), (10, 10, 20)):
        block = ["stable"] * counts[0] + ["mild_drift"] * counts[1] + ["strong_drift"] * counts[2]
        rng.shuffle(block)
        phases.extend(block)
    return phases


def _ar1(rng: np.random.Generator, n_rolls: int, n_segments: int, rho: float = 0.82) -> np.ndarray:
    values = np.zeros((n_rolls, n_segments))
    innovations = rng.normal(size=(n_rolls, n_segments))
    values[:, 0] = innovations[:, 0]
    for idx in range(1, n_segments):
        values[:, idx] = rho * values[:, idx - 1] + np.sqrt(1.0 - rho**2) * innovations[:, idx]
    return values.ravel()


def _edges(station: str, roll_index: int) -> np.ndarray:
    base = np.linspace(0.0, ROLL_LENGTH_M, SEGMENTS_PER_ROLL + 1)
    if station == "lamination":
        return base
    amplitude = 0.28 if station == "coating" else 0.20
    station_phase = 0.4 if station == "coating" else 1.1
    warp = amplitude * np.sin(np.linspace(0.0, 4.0 * np.pi, len(base)) + station_phase + roll_index * 0.07)
    warp[0] = 0.0
    warp[-1] = 0.0
    return base + warp


def _build_canonical(rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = N_ROLLS * SEGMENTS_PER_ROLL
    roll_index = np.repeat(np.arange(N_ROLLS), SEGMENTS_PER_ROLL)
    segment_index = np.tile(np.arange(SEGMENTS_PER_ROLL), N_ROLLS)
    split = np.select([roll_index < 120, roll_index < 160], ["train", "validation"], default="test")
    phase_by_roll = np.asarray(_phase_schedule(rng))
    phase = phase_by_roll[roll_index]
    severity_map = {"stable": 0.0, "mild_drift": 0.95, "strong_drift": 2.15}
    severity = np.vectorize(severity_map.get)(phase).astype(float)

    roll_effect = np.repeat(rng.normal(0.0, 0.42, N_ROLLS), SEGMENTS_PER_ROLL)
    ar = _ar1(rng, N_ROLLS, SEGMENTS_PER_ROLL)
    local_wave = np.sin(2.0 * np.pi * segment_index / 37.0 + roll_index * 0.17)

    ambient_temp = 24.0 + 0.55 * severity + 0.45 * local_wave + rng.normal(0.0, 0.55, n)
    ambient_rh = 52.0 + 3.8 * severity + 1.6 * local_wave + 1.1 * ar + rng.normal(0.0, 1.5, n)
    line_speed = 4.8 + rng.normal(0.0, 0.22, n) + 0.13 * severity + 0.08 * ar
    coating_temp = 82.0 + rng.normal(0.0, 1.2, n) - 0.7 * severity + 0.25 * ar
    coating_gap = 28.0 + rng.normal(0.0, 0.85, n) + 0.72 * severity + 0.22 * ar
    viscosity = 1180.0 + rng.normal(0.0, 38.0, n) + 28.0 * severity + 10.0 * roll_effect
    curing_temp = 171.0 + rng.normal(0.0, 2.0, n) - 2.15 * severity - 0.45 * ar
    curing_time = 12.5 + rng.normal(0.0, 0.42, n) - 0.52 * severity - 0.10 * ar
    lamination_temp = 181.0 + rng.normal(0.0, 1.8, n) + 0.75 * severity + 0.35 * ar
    lamination_pressure = 2.55 + rng.normal(0.0, 0.12, n) - 0.11 * severity - 0.025 * ar
    lamination_time = 18.0 + rng.normal(0.0, 0.65, n) - 0.42 * severity

    shared = 0.52 * severity + 0.34 * roll_effect + 0.22 * ar + rng.normal(0.0, 0.30, n)
    peel_score = (
        shared
        + 0.42 * ((ambient_rh - 52.0) / 5.0)
        + 0.55 * ((171.0 - curing_temp) / 3.0)
        + 0.25 * ((viscosity - 1180.0) / 55.0)
        + rng.normal(0.0, 1.40, n)
    )
    md_score = (
        shared
        + 0.48 * np.abs(lamination_temp - 181.0) / 2.6
        + 0.42 * np.abs(lamination_pressure - 2.55) / 0.17
        + rng.normal(0.0, 1.44, n)
    )
    td_score = (
        shared
        + 0.36 * np.abs(coating_gap - 28.0) / 1.2
        + 0.44 * np.abs(lamination_pressure - 2.55) / 0.17
        + rng.normal(0.0, 1.48, n)
    )
    heat_score = (
        shared
        + 0.58 * ((171.0 - curing_temp) / 3.0)
        + 0.42 * ((12.5 - curing_time) / 0.75)
        + rng.normal(0.0, 1.40, n)
    )
    appearance_score = (
        shared
        + 0.40 * ((ambient_rh - 52.0) / 5.0)
        + 0.48 * np.abs(coating_gap - 28.0) / 1.2
        + 0.40 * np.abs(lamination_pressure - 2.55) / 0.17
        + rng.normal(0.0, 1.42, n)
    )

    target_fail_rates = {"peel": 0.052, "md": 0.052, "td": 0.052, "heat": 0.052, "appearance": 0.065}
    scores = {"peel": peel_score, "md": md_score, "td": td_score, "heat": heat_score, "appearance": appearance_score}
    thresholds = {name: float(np.quantile(score, 1.0 - target_fail_rates[name])) for name, score in scores.items()}

    peel = np.round(0.85 + 0.085 * (thresholds["peel"] - peel_score), 6)
    md_magnitude = 0.10 * np.exp(0.22 * (md_score - thresholds["md"]))
    td_magnitude = 0.10 * np.exp(0.22 * (td_score - thresholds["td"]))
    md_sign = np.where(rng.normal(size=n) + 0.18 * ar >= 0.0, 1.0, -1.0)
    td_sign = np.where(rng.normal(size=n) - 0.12 * ar >= 0.0, 1.0, -1.0)
    md = np.round(md_sign * md_magnitude, 6)
    td = np.round(td_sign * td_magnitude, 6)
    heat = np.round(300.0 + 8.5 * (thresholds["heat"] - heat_score), 6)
    appearance_ng = (appearance_score > thresholds["appearance"]).astype(int)

    peel_pass = peel >= 0.85
    md_pass = np.abs(md) <= 0.10
    td_pass = np.abs(td) <= 0.10
    heat_pass = heat >= 300.0
    overall_pass = (peel_pass & md_pass & td_pass & heat_pass & (appearance_ng == 0)).astype(int)

    timestamps = [
        (BASE_TIME + pd.Timedelta(hours=int(r) * 6, minutes=int(s) * 3)).isoformat()
        for r, s in zip(roll_index, segment_index)
    ]
    roll_ids = np.array([f"ROLL-{idx + 1:04d}" for idx in roll_index])
    segment_ids = np.array([f"LAM-{r + 1:04d}-{s + 1:03d}" for r, s in zip(roll_index, segment_index)])

    canonical = pd.DataFrame(
        {
            "aligned_sample_id": [f"ALN-{r + 1:04d}-{s + 1:03d}" for r, s in zip(roll_index, segment_index)],
            "segment_id": segment_ids,
            "root_roll_id": roll_ids,
            "product_id": PRODUCT_ID,
            "product_batch": [f"BATCH-{r // 10 + 1:03d}" for r in roll_index],
            "dataset_split": split,
            "improvement_cycle_id": "CYCLE-00-BASELINE",
            "dataset_version": "synthetic-v2",
            "timestamp": timestamps,
            "material_md_start_m": segment_index * (ROLL_LENGTH_M / SEGMENTS_PER_ROLL),
            "material_md_end_m": (segment_index + 1) * (ROLL_LENGTH_M / SEGMENTS_PER_ROLL),
            "ambient_temp_c": ambient_temp,
            "ambient_rh_pct": ambient_rh,
            "line_speed_m_min": line_speed,
            "coating_temp_c": coating_temp,
            "coating_gap_um": coating_gap,
            "coating_viscosity_mpa_s": viscosity,
            "curing_temp_c": curing_temp,
            "curing_time_min": curing_time,
            "lamination_temp_c": lamination_temp,
            "lamination_pressure_mpa": lamination_pressure,
            "lamination_time_s": lamination_time,
            "peel_strength_n_mm": peel,
            "dimensional_stability_md_pct": md,
            "dimensional_stability_td_pct": td,
            "heat_resistance_c": heat,
            "appearance_ng": appearance_ng,
            "peel_spec_pass_flag": peel_pass.astype(int),
            "md_spec_pass_flag": md_pass.astype(int),
            "td_spec_pass_flag": td_pass.astype(int),
            "heat_spec_pass_flag": heat_pass.astype(int),
            "appearance_spec_pass_flag": 1 - appearance_ng,
            "overall_pass_flag": overall_pass,
            "label_source": "synthetic_ground_truth",
            "process_phase": phase,
        }
    )
    calibration = pd.DataFrame([{"target": key, "score_threshold": value} for key, value in thresholds.items()])
    return canonical, calibration


def _build_process_tables(canonical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    process_rows: list[dict] = []
    trace_rows: list[dict] = []
    stations = ("coating", "curing", "lamination")
    station_offsets = {"coating": 0, "curing": 90, "lamination": 180}
    fields = [
        "ambient_temp_c", "ambient_rh_pct", "line_speed_m_min", "coating_temp_c", "coating_gap_um",
        "coating_viscosity_mpa_s", "curing_temp_c", "curing_time_min", "lamination_temp_c",
        "lamination_pressure_mpa", "lamination_time_s",
    ]
    for roll_idx, (_, roll_df) in enumerate(canonical.groupby("root_roll_id", sort=False)):
        roll_df = roll_df.reset_index(drop=True)
        for station in stations:
            edges = _edges(station, roll_idx)
            for seg_idx in range(SEGMENTS_PER_ROLL):
                midpoint = (edges[seg_idx] + edges[seg_idx + 1]) / 2.0
                source_idx = min(SEGMENTS_PER_ROLL - 1, int(midpoint // (ROLL_LENGTH_M / SEGMENTS_PER_ROLL)))
                source = roll_df.iloc[source_idx]
                segment_id = f"{station[:3].upper()}-{roll_idx + 1:04d}-{seg_idx + 1:03d}"
                completed_at = pd.Timestamp(source["timestamp"]) + pd.Timedelta(minutes=station_offsets[station])
                row = {
                    "process_segment_id": segment_id,
                    "root_roll_id": source["root_roll_id"],
                    "product_id": PRODUCT_ID,
                    "dataset_split": source["dataset_split"],
                    "station": station,
                    "station_sequence": {"coating": 1, "curing": 2, "lamination": 3}[station],
                    "material_md_start_m": edges[seg_idx],
                    "material_md_end_m": edges[seg_idx + 1],
                    "started_at": (completed_at - pd.Timedelta(minutes=3)).isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "equipment_id": {"coating": "COATER-01", "curing": "OVEN-01", "lamination": "LAM-01"}[station],
                    "process_phase_observed": "production",
                }
                row.update({field: source[field] for field in fields})
                process_rows.append(row)
                upstream = ""
                if station == "curing":
                    upstream = f"COA-{roll_idx + 1:04d}-{source_idx + 1:03d}"
                elif station == "lamination":
                    upstream = f"CUR-{roll_idx + 1:04d}-{source_idx + 1:03d}"
                trace_rows.append(
                    {
                        "trace_id": f"TRC-{station[:3].upper()}-{roll_idx + 1:04d}-{seg_idx + 1:03d}",
                        "process_segment_id": segment_id,
                        "root_roll_id": source["root_roll_id"],
                        "station": station,
                        "material_md_start_m": edges[seg_idx],
                        "material_md_end_m": edges[seg_idx + 1],
                        "upstream_process_segment_id": upstream,
                        "source_aligned_sample_id": source["aligned_sample_id"],
                        "alignment_contract_version": "md-overlap-v1",
                    }
                )
    return pd.DataFrame(process_rows), pd.DataFrame(trace_rows)


def _build_inspections(canonical: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict] = []
    inspection_no = 0

    def base_row(source: pd.Series, event_id: str, method: str, scope: str) -> dict:
        nonlocal inspection_no
        inspection_no += 1
        return {
            "inspection_id": f"INSP-{inspection_no:07d}",
            "sampling_event_id": event_id,
            "root_roll_id": source["root_roll_id"],
            "segment_id": source["segment_id"] if scope == "segment" else "",
            "aligned_sample_id": source["aligned_sample_id"] if scope == "segment" else "",
            "product_id": PRODUCT_ID,
            "spec_version": SPEC_VERSION,
            "dataset_split": source["dataset_split"],
            "label_scope": scope,
            "inspection_method": method,
            "test_method_version": "SIM-TM-2.0",
            "sampled_at": source["timestamp"],
            "completed_at": (pd.Timestamp(source["timestamp"]) + pd.Timedelta(minutes=20 if method == "online_vision" else 240)).isoformat(),
            "label_source": "simulated_inspection",
            "validity_status": "valid",
            "is_retest": 0,
            "parent_inspection_id": "",
            "retest_reason": "",
            "disposition_code": "",
        }

    for _, source in canonical.iterrows():
        event = f"EVT-VISION-{source['root_roll_id']}-{int(source['material_md_start_m']):03d}"
        row = base_row(source, event, "online_vision", "segment")
        row.update(
            {
                "peel_strength_n_mm": np.nan,
                "dimensional_stability_md_pct": np.nan,
                "dimensional_stability_td_pct": np.nan,
                "heat_resistance_c": np.nan,
                "appearance_ng_flag": int(source["appearance_ng"]),
                "appearance_spec_pass_flag": int(source["appearance_spec_pass_flag"]),
                "peel_label_available": 0,
                "md_label_available": 0,
                "td_label_available": 0,
                "heat_label_available": 0,
                "appearance_label_available": 1,
                "quality_label_available": 1,
            }
        )
        rows.append(row)

    lab_sources = canonical[canonical.groupby("root_roll_id").cumcount() % 4 == 0]
    lab_row_indexes: list[int] = []
    for _, source in lab_sources.iterrows():
        event = f"EVT-LAB-{source['root_roll_id']}-{int(source['material_md_start_m']):03d}"
        row = base_row(source, event, "laboratory_segment", "segment")
        row.update(
            {
                "peel_strength_n_mm": source["peel_strength_n_mm"] + rng.normal(0.0, 0.012),
                "dimensional_stability_md_pct": source["dimensional_stability_md_pct"] + rng.normal(0.0, 0.003),
                "dimensional_stability_td_pct": source["dimensional_stability_td_pct"] + rng.normal(0.0, 0.003),
                "heat_resistance_c": source["heat_resistance_c"] + rng.normal(0.0, 1.2),
                "appearance_ng_flag": np.nan,
                "appearance_spec_pass_flag": np.nan,
                "peel_label_available": 1,
                "md_label_available": 1,
                "td_label_available": 1,
                "heat_label_available": 1,
                "appearance_label_available": 0,
                "quality_label_available": 1,
            }
        )
        lab_row_indexes.append(len(rows))
        rows.append(row)

    # Deterministic retests exercise the contract without changing the underlying failure mechanism.
    for original_index in lab_row_indexes[::125]:
        original = rows[original_index]
        original["validity_status"] = "superseded"
        source = canonical.loc[canonical["aligned_sample_id"] == original["aligned_sample_id"]].iloc[0]
        retest = base_row(source, original["sampling_event_id"], "laboratory_segment", "segment")
        retest.update(
            {
                "peel_strength_n_mm": original["peel_strength_n_mm"] + rng.normal(0.0, 0.006),
                "dimensional_stability_md_pct": original["dimensional_stability_md_pct"] + rng.normal(0.0, 0.0015),
                "dimensional_stability_td_pct": original["dimensional_stability_td_pct"] + rng.normal(0.0, 0.0015),
                "heat_resistance_c": original["heat_resistance_c"] + rng.normal(0.0, 0.6),
                "appearance_ng_flag": np.nan,
                "appearance_spec_pass_flag": np.nan,
                "peel_label_available": 1,
                "md_label_available": 1,
                "td_label_available": 1,
                "heat_label_available": 1,
                "appearance_label_available": 0,
                "quality_label_available": 1,
                "is_retest": 1,
                "parent_inspection_id": original["inspection_id"],
                "retest_reason": "instrument_repeatability_check",
                "completed_at": (pd.Timestamp(original["completed_at"]) + pd.Timedelta(minutes=60)).isoformat(),
            }
        )
        rows.append(retest)

    for _, roll_df in canonical.groupby("root_roll_id", sort=False):
        source = roll_df.iloc[-1]
        row = base_row(source, f"EVT-ROLL-{source['root_roll_id']}", "roll_qualification", "roll")
        row.update(
            {
                "peel_strength_n_mm": roll_df["peel_strength_n_mm"].mean(),
                "dimensional_stability_md_pct": roll_df["dimensional_stability_md_pct"].abs().max(),
                "dimensional_stability_td_pct": roll_df["dimensional_stability_td_pct"].abs().max(),
                "heat_resistance_c": roll_df["heat_resistance_c"].min(),
                "appearance_ng_flag": int(roll_df["appearance_ng"].max()),
                "appearance_spec_pass_flag": int(1 - roll_df["appearance_ng"].max()),
                "peel_label_available": 1,
                "md_label_available": 1,
                "td_label_available": 1,
                "heat_label_available": 1,
                "appearance_label_available": 1,
                "quality_label_available": 1,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _build_specs() -> pd.DataFrame:
    specs = [
        ("peel_strength_n_mm", 0.85, None, 1.10, "N/mm", "SIM-PEEL-01"),
        ("dimensional_stability_md_pct", -0.10, 0.10, 0.0, "%", "SIM-DIM-01"),
        ("dimensional_stability_td_pct", -0.10, 0.10, 0.0, "%", "SIM-DIM-01"),
        ("heat_resistance_c", 300.0, None, 315.0, "degC", "SIM-HEAT-01"),
        ("appearance_ng", 0.0, 0.0, 0.0, "flag", "SIM-VISION-01"),
        ("thermal_shrinkage_md_pct", -0.20, 0.20, 0.0, "%", "SIM-SHRINK-01"),
        ("thermal_shrinkage_td_pct", -0.20, 0.20, 0.0, "%", "SIM-SHRINK-01"),
    ]
    return pd.DataFrame(
        [
            {
                "product_id": PRODUCT_ID,
                "spec_version": SPEC_VERSION,
                "characteristic": name,
                "lsl": lsl,
                "usl": usl,
                "target": target,
                "unit": unit,
                "test_method": method,
                "effective_from": "2026-01-01T00:00:00+08:00",
                "effective_to": "",
                "spec_source": "synthetic_demonstration_only",
            }
            for name, lsl, usl, target, unit, method in specs
        ]
    )


def _build_roll_master(canonical: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for roll_id, group in canonical.groupby("root_roll_id", sort=False):
        rows.append(
            {
                "root_roll_id": roll_id,
                "product_id": PRODUCT_ID,
                "product_batch": group["product_batch"].iloc[0],
                "dataset_split": group["dataset_split"].iloc[0],
                "improvement_cycle_id": "CYCLE-00-BASELINE",
                "dataset_version": "synthetic-v2",
                "roll_start_at": group["timestamp"].iloc[0],
                "roll_end_at": group["timestamp"].iloc[-1],
                "roll_length_m": ROLL_LENGTH_M,
                "canonical_segment_count": len(group),
                "process_phase": group["process_phase"].iloc[0],
                "segment_joint_yield_pct": 100.0 * group["overall_pass_flag"].mean(),
                "roll_qualification_pass_flag": int(group["overall_pass_flag"].all()),
                "data_source": "synthetic_test_line",
            }
        )
    return pd.DataFrame(rows)


def _build_drift(canonical: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for roll_id, group in canonical.groupby("root_roll_id", sort=False):
        phase = group["process_phase"].iloc[0]
        if phase == "stable":
            continue
        roll_num = int(roll_id.split("-")[-1])
        scenario = ("humidity_rise", "curing_temperature_drop", "coating_gap_drift", "lamination_pressure_drop")[roll_num % 4]
        rows.append(
            {
                "drift_event_id": f"DRIFT-{roll_num:04d}",
                "root_roll_id": roll_id,
                "process_phase": phase,
                "scenario": scenario,
                "severity_level": "mild" if phase == "mild_drift" else "strong",
                "material_md_start_m": 0.0,
                "material_md_end_m": ROLL_LENGTH_M,
                "event_start_at": group["timestamp"].iloc[0],
                "event_end_at": group["timestamp"].iloc[-1],
                "model_feature_allowed": 0,
                "purpose": "generation_validation_only",
            }
        )
    return pd.DataFrame(rows)


def _metrics(canonical: pd.DataFrame) -> dict:
    failures = {
        "peel": float(1.0 - canonical["peel_spec_pass_flag"].mean()),
        "md": float(1.0 - canonical["md_spec_pass_flag"].mean()),
        "td": float(1.0 - canonical["td_spec_pass_flag"].mean()),
        "heat": float(1.0 - canonical["heat_spec_pass_flag"].mean()),
        "appearance": float(canonical["appearance_ng"].mean()),
    }
    return {
        "overall_segment_joint_yield": float(canonical["overall_pass_flag"].mean()),
        "failure_rates": failures,
        "yield_by_phase": canonical.groupby("process_phase")["overall_pass_flag"].mean().to_dict(),
        "yield_by_split": canonical.groupby("dataset_split")["overall_pass_flag"].mean().to_dict(),
        "appearance_ng_count": int(canonical["appearance_ng"].sum()),
        "appearance_ng_roll_count": int(canonical.loc[canonical["appearance_ng"] == 1, "root_roll_id"].nunique()),
        "test_appearance_ng_count": int(canonical.loc[canonical["dataset_split"] == "test", "appearance_ng"].sum()),
    }


def generate(output_dir: Path, seed: int = SEED) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    canonical, calibration = _build_canonical(rng)
    process, trace = _build_process_tables(canonical)
    inspections = _build_inspections(canonical, rng)
    specs = _build_specs()
    rolls = _build_roll_master(canonical)
    drift = _build_drift(canonical)

    tables = {
        "roll_master.csv": rolls,
        "process_segments.csv": process,
        "process_traceability.csv": trace,
        "quality_timeseries.csv": canonical,
        "quality_inspection.csv": inspections,
        "quality_specifications.csv": specs,
        "drift_ground_truth.csv": drift,
    }
    for filename, frame in tables.items():
        frame.to_csv(output_dir / filename, index=False, encoding="utf-8", float_format="%.6f", lineterminator="\n")

    summary = _metrics(canonical)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_at": "2026-01-01T00:00:00+08:00",
        "timezone": "Asia/Taipei",
        "seed": seed,
        "data_classification": "synthetic_test_line_demonstration_only",
        "product_id": PRODUCT_ID,
        "spec_version": SPEC_VERSION,
        "configuration": {
            "roll_count": N_ROLLS,
            "canonical_segments_per_roll": SEGMENTS_PER_ROLL,
            "canonical_segment_count": len(canonical),
            "roll_length_m": ROLL_LENGTH_M,
            "split_roll_counts": rolls.groupby("dataset_split")["root_roll_id"].nunique().to_dict(),
            "target_segment_joint_yield_range": [0.78, 0.82],
            "alignment_contract": "root_roll_id plus MD half-open overlap [start,end), minimum coverage 0.98",
            "quality_sources": ["synthetic_ground_truth", "simulated_inspection"],
        },
        "score_calibration": calibration.to_dict(orient="records"),
        "summary": summary,
        "row_counts": {filename: len(frame) for filename, frame in tables.items()},
        "csv_sha256": {filename: _sha256(output_dir / filename) for filename in sorted(tables)},
        "limitations": [
            "All specifications and process ranges are synthetic demonstration assumptions.",
            "The approximately 80% yield is final-segment joint yield, not roll release yield or a factory claim.",
            "Drift ground truth is validation-only and must never be used as a model feature.",
        ],
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("generated_data/v2"))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    metadata = generate(args.output, args.seed)
    print(json.dumps(metadata["summary"], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
