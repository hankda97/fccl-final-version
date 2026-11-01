"""Validate FCCL synthetic seven-table dataset v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from generate_fccl_v2 import generate


CSV_FILES = {
    "roll_master.csv",
    "process_segments.csv",
    "process_traceability.csv",
    "quality_timeseries.csv",
    "quality_inspection.csv",
    "quality_specifications.csv",
    "drift_ground_truth.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate(data_dir: Path, check_reproducible: bool = False) -> dict:
    actual_csv = {path.name for path in data_dir.glob("*.csv")}
    require(actual_csv == CSV_FILES, f"expected exactly seven CSVs, got {sorted(actual_csv)}")
    metadata = json.loads((data_dir / "metadata.json").read_text(encoding="utf-8"))
    tables = {name: pd.read_csv(data_dir / name) for name in CSV_FILES}
    rolls = tables["roll_master.csv"]
    process = tables["process_segments.csv"]
    trace = tables["process_traceability.csv"]
    quality = tables["quality_timeseries.csv"]
    inspections = tables["quality_inspection.csv"]
    specs = tables["quality_specifications.csv"]

    require(len(rolls) == 200 and rolls["root_roll_id"].is_unique, "roll_master must contain 200 unique rolls")
    require(len(quality) == 20_000 and quality["aligned_sample_id"].is_unique, "quality_timeseries must contain 20,000 unique canonical samples")
    require(len(process) == 60_000 and process["process_segment_id"].is_unique, "process_segments must contain 60,000 unique station segments")
    require(len(trace) == 60_000 and trace["trace_id"].is_unique, "traceability must contain 60,000 unique rows")
    require(set(process["process_segment_id"]) == set(trace["process_segment_id"]), "traceability/process segment keys differ")
    require(set(quality["root_roll_id"]) <= set(rolls["root_roll_id"]), "quality contains an unknown roll")
    require(set(process["root_roll_id"]) <= set(rolls["root_roll_id"]), "process contains an unknown roll")

    split_counts = rolls.groupby("dataset_split")["root_roll_id"].nunique().to_dict()
    require(split_counts == {"test": 40, "train": 120, "validation": 40}, f"unexpected split counts: {split_counts}")
    require(quality.groupby("root_roll_id")["dataset_split"].nunique().max() == 1, "a roll crosses splits")

    grouped = process.sort_values(["root_roll_id", "station", "material_md_start_m"]).groupby(["root_roll_id", "station"], sort=False)
    for (_, _), group in grouped:
        starts = group["material_md_start_m"].to_numpy()
        ends = group["material_md_end_m"].to_numpy()
        require((ends > starts).all(), "non-positive MD interval")
        require(abs(starts[0]) < 1e-6 and abs(ends[-1] - 500.0) < 1e-6, "station does not cover the complete roll")
        require((abs(starts[1:] - ends[:-1]) < 2e-6).all(), "station intervals contain a gap or overlap")

    expected_overall = (
        (quality["peel_strength_n_mm"] >= 0.85)
        & (quality["dimensional_stability_md_pct"].abs() <= 0.10)
        & (quality["dimensional_stability_td_pct"].abs() <= 0.10)
        & (quality["heat_resistance_c"] >= 300.0)
        & (quality["appearance_ng"] == 0)
    ).astype(int)
    require(np.array_equal(expected_overall.to_numpy(), quality["overall_pass_flag"].to_numpy()), "overall_pass_flag is inconsistent with fixed specifications")
    overall_yield = float(quality["overall_pass_flag"].mean())
    require(0.78 <= overall_yield <= 0.82, f"joint yield {overall_yield:.4f} is outside 78%-82%")

    failure_rates = {
        "peel": 1.0 - quality["peel_spec_pass_flag"].mean(),
        "md": 1.0 - quality["md_spec_pass_flag"].mean(),
        "td": 1.0 - quality["td_spec_pass_flag"].mean(),
        "heat": 1.0 - quality["heat_spec_pass_flag"].mean(),
        "appearance": quality["appearance_ng"].mean(),
    }
    require(all(0.04 <= value <= 0.08 for value in failure_rates.values()), f"unexpected target failure rates: {failure_rates}")
    phase_yield = quality.groupby("process_phase")["overall_pass_flag"].mean().to_dict()
    require(0.93 <= phase_yield["stable"] <= 0.97, f"stable yield out of range: {phase_yield['stable']}")
    require(0.75 <= phase_yield["mild_drift"] <= 0.90, f"mild yield out of range: {phase_yield['mild_drift']}")
    require(0.45 <= phase_yield["strong_drift"] <= 0.70, f"strong yield out of range: {phase_yield['strong_drift']}")

    appearance_ng = quality[quality["appearance_ng"] == 1]
    require(len(appearance_ng) >= 1_000, "fewer than 1,000 appearance NG samples")
    require(appearance_ng["root_roll_id"].nunique() >= 50, "appearance NG covers fewer than 50 rolls")
    require(len(appearance_ng[appearance_ng["dataset_split"] == "test"]) >= 200, "test contains fewer than 200 appearance NG samples")
    stable_subgroups = len(quality[quality["process_phase"] == "stable"]) // 5
    require(stable_subgroups >= 25, "fewer than 25 stable Phase I subgroups")

    availability = ["peel_label_available", "md_label_available", "td_label_available", "heat_label_available", "appearance_label_available"]
    expected_available = inspections[availability].max(axis=1).astype(int)
    require(np.array_equal(expected_available.to_numpy(), inspections["quality_label_available"].to_numpy()), "quality_label_available does not mean at least one valid target")
    appearance_rows = inspections[inspections["appearance_label_available"] == 1]
    require(
        (appearance_rows["appearance_spec_pass_flag"] == 1 - appearance_rows["appearance_ng_flag"]).all(),
        "appearance flags conflict",
    )
    retests = inspections[inspections["is_retest"] == 1]
    require(len(retests) > 0, "no retest examples")
    original_status = inspections.set_index("inspection_id")["validity_status"]
    require(retests["parent_inspection_id"].isin(original_status.index).all(), "retest parent missing")
    require((original_status.loc[retests["parent_inspection_id"]] == "superseded").all(), "retest parent is not superseded")
    require(not specs.duplicated(["product_id", "spec_version", "characteristic"]).any(), "duplicate specification key")

    actual_hashes = {name: sha256(data_dir / name) for name in sorted(CSV_FILES)}
    require(actual_hashes == metadata["csv_sha256"], "metadata CSV hashes do not match")
    require(metadata["row_counts"] == {name: len(tables[name]) for name in metadata["row_counts"]}, "metadata row counts do not match")

    if check_reproducible:
        with tempfile.TemporaryDirectory(prefix="fccl-v2-repro-") as temp_dir:
            regenerated = generate(Path(temp_dir), int(metadata["seed"]))
            require(regenerated["csv_sha256"] == actual_hashes, "same-seed regeneration hashes differ")

    return {
        "status": "passed",
        "row_counts": {name: len(tables[name]) for name in sorted(CSV_FILES)},
        "split_roll_counts": split_counts,
        "overall_segment_joint_yield": overall_yield,
        "failure_rates": failure_rates,
        "yield_by_phase": phase_yield,
        "appearance_ng_count": len(appearance_ng),
        "appearance_ng_roll_count": appearance_ng["root_roll_id"].nunique(),
        "test_appearance_ng_count": len(appearance_ng[appearance_ng["dataset_split"] == "test"]),
        "stable_phase_i_subgroups_n5": stable_subgroups,
        "retest_count": len(retests),
        "same_seed_reproducible": check_reproducible,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("generated_data/v2"))
    parser.add_argument("--check-reproducible", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate(args.data_dir, args.check_reproducible), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
