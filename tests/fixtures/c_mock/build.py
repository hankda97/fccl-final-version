"""Build small, versioned C-only fixtures; NOT member A's process generator."""

import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random

VERSION = "c-fixtures-v1"
TARGETS = (
    "peel_strength_n_mm", "dimensional_stability_md_pct",
    "dimensional_stability_td_pct", "heat_resistance_c", "appearance_ng",
)
UNITS = {
    "length_m": "m", "position_m": "m", "ambient_temp_c": "°C",
    "ambient_rh_pct": "%RH", "line_speed_m_min": "m/min",
    "coating_temp_c": "°C", "coating_gap_um": "μm",
    "coating_viscosity_mpa_s": "mPa·s", "curing_temp_c": "°C",
    "curing_time_min": "min", "lamination_temp_c": "°C",
    "lamination_pressure_mpa": "MPa", "lamination_time_s": "s",
    "peel_strength_n_mm": "N/mm", "dimensional_stability_md_pct": "%",
    "dimensional_stability_td_pct": "%", "heat_resistance_c": "°C",
    "appearance_ng": "0/1",
}


def build_rows(seed=42, subgroup_size=5, history_groups=25):
    if subgroup_size < 2 or history_groups < 1:
        raise ValueError("Fixture group settings must be positive; size >= 2")
    start = datetime(2026, 11, 1, 8, tzinfo=timezone(timedelta(hours=8)))

    def records(prefix, groups, origin, rng):
        rows = []
        for group in range(groups):
            timestamp = (origin + timedelta(minutes=group)).isoformat()
            for specimen in range(subgroup_size):
                row = {
                    "timestamp": timestamp, "available_at": timestamp,
                    "product_batch": f"{prefix}-B{1 + group // 15:02d}",
                    "segment_id": f"{prefix}-S{group:03d}",
                    "subgroup_id": f"{prefix}-G{group:03d}",
                    "specimen_id": f"{prefix}-{group:03d}-{specimen:02d}",
                    "product_id": "C-DEMO-01", "recipe_id": "C-MOCK-v1",
                    "length_m": 5.0, "position_m": float(group * 5),
                    "ambient_temp_c": round(24 + rng.uniform(-0.4, 0.4), 3),
                    "ambient_rh_pct": round(48 + rng.uniform(-2, 2), 3),
                    "line_speed_m_min": 2.0, "coating_temp_c": 70.0,
                    "coating_gap_um": 25.0, "coating_viscosity_mpa_s": 1500.0,
                    "curing_temp_c": 170.0, "curing_time_min": 15.0,
                    "lamination_temp_c": 195.0, "lamination_pressure_mpa": 2.0,
                    "lamination_time_s": 60.0,
                    "peel_strength_n_mm": round(1.25 + rng.uniform(-0.025, 0.025), 4),
                    "dimensional_stability_md_pct": round(rng.uniform(-0.03, 0.03), 4),
                    "dimensional_stability_td_pct": round(rng.uniform(-0.03, 0.03), 4),
                    "heat_resistance_c": round(290 + rng.uniform(-4, 4), 3),
                    "appearance_ng": int(prefix == "M" and group == 12 and specimen == 0),
                }
                rows.append(row)
        return rows

    normal = records("M", 30, start, random.Random(seed))
    history = records("H", history_groups, start - timedelta(days=1), random.Random(seed + 100))
    variants = {"normal": normal, "history": history}
    variants["partial_quality"] = [
        {k: v for k, v in row.items() if k != "heat_resistance_c"} for row in normal
    ]
    variants["no_quality"] = [
        {k: v for k, v in row.items() if k not in TARGETS} for row in normal
    ]
    variants["ungrouped"] = [
        {k: v for k, v in row.items() if k not in ("subgroup_id", "specimen_id")}
        for row in normal
    ]
    variants["missing_columns"] = [
        {k: v for k, v in row.items() if k != "timestamp"} for row in normal
    ]
    variants["invalid_values"] = [dict(row) for row in normal]
    variants["invalid_values"][0]["timestamp"] = "not-a-time"
    variants["invalid_values"][1]["ambient_rh_pct"] = 130
    variants["invalid_values"][2]["line_speed_m_min"] = "invalid"
    variants["invalid_values"][3]["peel_strength_n_mm"] = ""
    variants["invalid_values"].append(dict(normal[4]))
    for name in ("out_of_control", "trend", "same_side"):
        variants[name] = [dict(row) for row in normal]
    for i, row in enumerate(variants["out_of_control"]):
        if i // subgroup_size == 10:
            row["peel_strength_n_mm"] = round(0.65 + (i % subgroup_size) * 0.001, 4)
    for i, row in enumerate(variants["trend"]):
        group = i // subgroup_size
        if 3 <= group <= 8:
            row["peel_strength_n_mm"] = round(1.20 + (group - 3) * 0.015 + (i % subgroup_size) * 0.001, 4)
    for i, row in enumerate(variants["same_side"]):
        if 3 <= i // subgroup_size <= 11:
            row["peel_strength_n_mm"] = round(1.30 + (i % subgroup_size) * 0.001, 4)
    return variants


def write_fixtures(directory: Path, seed=42, subgroup_size=5, history_groups=25):
    directory.mkdir(parents=True, exist_ok=True)
    variants = build_rows(seed, subgroup_size, history_groups)
    for name, rows in variants.items():
        with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    metadata = {
        "source": "成員 C 專用模擬測試資料，非真實產線", "version": VERSION,
        "seed": seed, "timezone": "Asia/Taipei", "product_id": "C-DEMO-01",
        "recipe_id": "C-MOCK-v1", "subgroup_size": subgroup_size,
        "subgroup_meaning": "同次取樣的獨立試片；僅 C fixture 假設",
        "history_groups": history_groups, "history_file": "history.csv",
        "history_end": variants["history"][-1]["available_at"],
        "monitoring_start": variants["normal"][0]["available_at"],
        "quality_targets": list(TARGETS), "units": UNITS,
        "scenarios": {name: {"file": f"{name}.csv", "rows": len(rows)} for name, rows in variants.items()},
        "expected_test_cases": {
            "out_of_control": "M-G010 抗剝離值下降；C3 才驗證管制規則",
            "trend": "M-G003～008 的子組均值嚴格上升",
            "same_side": "M-G003～011 抗剝離均值高於歷史中心",
            "invalid_values": "壞時間、濕度超界、線速非數值、缺品質及重複試片",
        },
        "baseline_validation": "本階段僅建立資料；SPC 適用性與界限計算待 C3",
    }
    settings = {
        "source": "C 專用示範設定，非正式允收規格", "version": "c-settings-v1",
        "product_id": "C-DEMO-01", "recipe_id": "C-MOCK-v1",
        "quality_specs": {
            "peel_strength_n_mm": {"lsl": 1.0},
            "dimensional_stability_md_pct": {"lsl": -0.1, "usl": 0.1},
            "dimensional_stability_td_pct": {"lsl": -0.1, "usl": 0.1},
            "heat_resistance_c": {"lsl": 260.0}, "appearance_ng": {"allowed": [0]},
        },
        "appearance_ng_risk_threshold": 0.5,
        "spc": {"subgroup_size": subgroup_size, "minimum_history_groups": history_groups},
        "recommendation_policy": "待 C5 測試；不代表正式多目標策略",
    }
    for name, value in (("metadata", metadata), ("settings", settings)):
        (directory / f"{name}.json").write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    write_fixtures(Path(__file__).parent)
