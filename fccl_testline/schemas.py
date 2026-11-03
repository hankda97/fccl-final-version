from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from . import SCHEMA_VERSION


@dataclass(frozen=True)
class ContractIssue:
    code: str
    field: str
    message: str


COMMON = {"schema_version": str, "run_id": str}
SCHEMAS: dict[str, dict[str, type]] = {
    "process_signal": {
        **COMMON, "tick_sequence": int, "timestamp": str, "segment_id": str,
        "station": str, "signal_name": str, "actual_value": float,
        "setpoint_value": float, "unit": str, "valid": bool,
    },
    "thickness_subgroup": {
        **COMMON, "tick_sequence": int, "timestamp": str, "segment_id": str,
        "station": str, "thickness_1_um": float, "thickness_2_um": float,
        "thickness_3_um": float, "thickness_4_um": float,
        "thickness_5_um": float, "unit": str,
    },
    "material_segment": {
        **COMMON, "segment_id": str, "md_start_m": float, "md_end_m": float,
        "coating_entered_at": str, "coating_exited_at": str,
        "curing_entered_at": str, "curing_exited_at": str,
        "lamination_entered_at": str, "lamination_exited_at": str,
        "quality_available_at": str, "status": str,
    },
    "parameter_event": {
        **COMMON, "event_id": str, "timestamp": str, "station": str,
        "old_values_json": str, "new_values_json": str,
        "effective_from_segment_id": str, "source": str,
    },
    "spc_event": {
        **COMMON, "event_id": str, "signal_name": str, "chart_type": str,
        "severity": str, "event_kind": str, "rule_code": str,
        "started_at": str, "ended_at": str, "affected_points": int,
        "baseline_version": str,
    },
    "quality_prediction": {
        **COMMON, "prediction_id": str, "segment_id": str, "timestamp": str,
        "target": str, "prediction": float, "unit": str,
        "model_version": str, "input_cutoff_at": str, "support_status": str,
    },
    "manifest": {
        "schema_version": str, "run_id": str, "product_id": str,
        "recipe_id": str, "seed": int, "scenario": str, "status": str,
        "started_at": str, "checkpoint_at": str, "files": dict,
    },
}

UNIT_RULES = {
    "dry_thickness_um": "um", "line_speed_m_min": "m/min",
    "coating_gap_um": "um", "coating_temp_c": "degC",
    "coating_viscosity_mpa_s": "mPa*s", "curing_temp_c": "degC",
    "exhaust_airflow_m3_h": "m3/h", "curing_time_min": "min",
    "lamination_temp_c": "degC", "lamination_pressure_mpa": "MPa",
    "lamination_time_min": "min", "peel_strength_n_mm": "N/mm",
    "dimensional_stability_md_pct": "pct",
    "dimensional_stability_td_pct": "pct", "heat_resistance_c": "degC",
}
TARGETS = frozenset(("peel_strength_n_mm", "dimensional_stability_md_pct", "dimensional_stability_td_pct", "heat_resistance_c"))


def validate_record(kind: str, record: Mapping[str, Any]) -> list[ContractIssue]:
    if kind not in SCHEMAS:
        return [ContractIssue("UNKNOWN_SCHEMA", "kind", kind)]
    issues: list[ContractIssue] = []
    expected = SCHEMAS[kind]
    for field, field_type in expected.items():
        if field not in record:
            issues.append(ContractIssue("MISSING_FIELD", field, f"{kind} 缺少必要欄位 {field}"))
            continue
        value = record[field]
        if field_type is float:
            valid_type = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            valid_type = isinstance(value, field_type)
        if not valid_type:
            issues.append(ContractIssue("TYPE_MISMATCH", field, f"{field} 型別必須是 {field_type.__name__}"))
    if record.get("schema_version") != SCHEMA_VERSION:
        issues.append(ContractIssue("INCOMPATIBLE_SCHEMA_VERSION", "schema_version", f"只接受 {SCHEMA_VERSION}"))
    if kind == "thickness_subgroup" and record.get("unit") != "um":
        issues.append(ContractIssue("UNIT_MISMATCH", "unit", "厚度子組單位必須是 um"))
    if kind == "process_signal":
        expected_unit = UNIT_RULES.get(str(record.get("signal_name")))
        if expected_unit and record.get("unit") != expected_unit:
            issues.append(ContractIssue("UNIT_MISMATCH", "unit", f"{record.get('signal_name')} 必須使用 {expected_unit}"))
    if kind == "quality_prediction":
        target = str(record.get("target"))
        if target not in TARGETS:
            issues.append(ContractIssue("UNSUPPORTED_TARGET", "target", "v3 僅支援四個連續目標"))
        elif record.get("unit") != UNIT_RULES[target]:
            issues.append(ContractIssue("UNIT_MISMATCH", "unit", f"{target} 必須使用 {UNIT_RULES[target]}"))
    return issues


def assert_valid(kind: str, record: Mapping[str, Any]) -> None:
    issues = validate_record(kind, record)
    if issues:
        raise ValueError(";".join(f"{issue.code}:{issue.field}" for issue in issues))
