"""Add the synthetic heat_resistance_c target required by SKILL.md.

The script is deterministic and idempotent.  It preserves the original source
CSVs in raw data/backups/pre_heat_resistance_v1 on the first run.
"""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
import shutil


SEED = 42
SPEC_LSL_C = 300.0
SPEC_USL_C = 330.0
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw data"
BACKUP = RAW / "backups" / "pre_heat_resistance_v1"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stable_normal(key: str) -> float:
    digest = hashlib.sha256(f"{SEED}:{key}".encode("utf-8")).digest()
    u1 = max(int.from_bytes(digest[:8], "big") / 2**64, 1e-12)
    u2 = int.from_bytes(digest[8:16], "big") / 2**64
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def quantize_half_degree(value: float) -> float:
    return round(value * 2.0) / 2.0


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def latent_heat_resistance(row: dict[str, str]) -> float:
    """Generate a correlated latent maximum passing temperature in °C."""
    peel = float(row["peel_strength_process_n_per_mm"])
    md_change = abs(float(row["md_dimensional_change_process_pct"]))
    td_change = abs(float(row["td_dimensional_change_process_pct"]))
    shrink_md = float(row["thermal_shrinkage_md_process_pct"])
    shrink_td = float(row["thermal_shrinkage_td_process_pct"])
    appearance = float(row["appearance_risk_process_score"])

    value = (
        304.0
        + 30.0 * (peel - 1.2)
        - 110.0 * (shrink_md - 0.075)
        - 95.0 * (shrink_td - 0.075)
        - 25.0 * md_change
        - 20.0 * td_change
        - 35.0 * max(0.0, appearance - 0.03)
    )
    return min(max(value, 288.5), SPEC_USL_C)


def add_timeseries_targets() -> dict[str, dict[str, str]]:
    path = RAW / "quality_timeseries.csv"
    fields, rows = read_csv(path)
    for field in ["heat_resistance_process_c", "heat_resistance_measured_c"]:
        if field not in fields:
            fields.append(field)

    by_segment: dict[str, dict[str, str]] = {}
    for row in rows:
        process_value = latent_heat_resistance(row)
        noise_scale = float(row.get("measurement_noise_scale") or 1.0)
        measured_value = process_value + 0.8 * noise_scale * stable_normal(row["segment_id"])
        measured_value = quantize_half_degree(min(max(measured_value, 288.5), SPEC_USL_C))
        row["heat_resistance_process_c"] = f"{process_value:.4f}"
        row["heat_resistance_measured_c"] = f"{measured_value:.1f}"
        by_segment[row["segment_id"]] = row

    write_csv(path, fields, rows)
    return by_segment


def add_inspection_targets(by_segment: dict[str, dict[str, str]]) -> None:
    path = RAW / "quality_inspection.csv"
    fields, rows = read_csv(path)
    new_fields = [
        "heat_resistance_c",
        "heat_resistance_process_c",
        "heat_resistance_spec_pass_flag",
    ]
    for field in new_fields:
        if field not in fields:
            fields.append(field)

    roll_values: dict[str, dict[str, list[float]]] = {}
    for sample in by_segment.values():
        if sample["process_step"] != "lamination":
            continue
        bucket = roll_values.setdefault(sample["root_roll_id"], {"process": [], "measured": []})
        bucket["process"].append(float(sample["heat_resistance_process_c"]))
        bucket["measured"].append(float(sample["heat_resistance_measured_c"]))

    for row in rows:
        process_value: float | None = None
        measured_value: float | None = None
        if row["inspection_type"] == "5_minute_lab_sample":
            sample = by_segment.get(row["segment_id"])
            if sample:
                process_value = float(sample["heat_resistance_process_c"])
                measured_value = float(sample["heat_resistance_measured_c"])
        elif row["inspection_type"] == "per_roll_qualification_demo":
            values = roll_values[row["root_roll_id"]]
            process_value = percentile(values["process"], 0.10)
            measured_value = quantize_half_degree(percentile(values["measured"], 0.10))

        if measured_value is None or process_value is None:
            row["heat_resistance_c"] = ""
            row["heat_resistance_process_c"] = ""
            row["heat_resistance_spec_pass_flag"] = ""
        else:
            row["heat_resistance_c"] = f"{measured_value:.1f}"
            row["heat_resistance_process_c"] = f"{process_value:.4f}"
            row["heat_resistance_spec_pass_flag"] = str(
                int(SPEC_LSL_C <= measured_value <= SPEC_USL_C)
            )

    write_csv(path, fields, rows)


def add_specification() -> None:
    path = RAW / "quality_specifications.csv"
    fields, rows = read_csv(path)
    rows = [row for row in rows if row["characteristic"] != "heat_resistance_c"]
    rows.append(
        {
            "product_id": "X_PRODUCT_DEMO",
            "product_name": "X 產品（合成示範）",
            "spec_version": "1.0",
            "characteristic": "heat_resistance_c",
            "category": "heat_resistance",
            "center": "305.0",
            "lsl": f"{SPEC_LSL_C:.1f}",
            "usl": f"{SPEC_USL_C:.1f}",
            "unit": "°C",
            "test_condition": "合成階梯升溫測試的最高通過溫度；0.5 °C 解析度",
            "spec_basis": "synthetic_demo_assumption",
            "pass_rule": "lsl <= value <= usl",
            "assumption_note": "中心值及上下限均為模擬假設，不代表通用 IPC 限值或正式產品驗收標準。",
            "data_status": "SYNTHETIC_DEMO_ONLY",
        }
    )
    write_csv(path, fields, rows)


def preserve_originals() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for name in [
        "quality_timeseries.csv",
        "quality_inspection.csv",
        "quality_specifications.csv",
    ]:
        source = RAW / name
        target = BACKUP / name
        if not target.exists():
            shutil.copy2(source, target)


def main() -> None:
    preserve_originals()
    by_segment = add_timeseries_targets()
    add_inspection_targets(by_segment)
    add_specification()
    print(f"Updated heat resistance targets for {len(by_segment)} quality time-series rows.")


if __name__ == "__main__":
    main()
