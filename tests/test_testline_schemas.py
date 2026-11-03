import copy

import pytest

from fccl_testline.schemas import SCHEMAS, assert_valid, validate_record


VALID = {
    "process_signal": {"schema_version": "testline-v3.0", "run_id": "RUN-1", "tick_sequence": 1, "timestamp": "2026-01-01T00:00:00+00:00", "segment_id": "SEG-1", "station": "curing", "signal_name": "curing_temp_c", "actual_value": 171.0, "setpoint_value": 171.0, "unit": "degC", "valid": True},
    "thickness_subgroup": {"schema_version": "testline-v3.0", "run_id": "RUN-1", "tick_sequence": 1, "timestamp": "2026-01-01T00:00:00+00:00", "segment_id": "SEG-1", "station": "coating", "thickness_1_um": 25.0, "thickness_2_um": 25.1, "thickness_3_um": 24.9, "thickness_4_um": 25.0, "thickness_5_um": 25.2, "unit": "um"},
    "material_segment": {"schema_version": "testline-v3.0", "run_id": "RUN-1", "segment_id": "SEG-1", "md_start_m": 0.0, "md_end_m": 1.0, "coating_entered_at": "t0", "coating_exited_at": "t1", "curing_entered_at": "t2", "curing_exited_at": "t3", "lamination_entered_at": "t4", "lamination_exited_at": "t5", "quality_available_at": "t6", "status": "completed"},
    "parameter_event": {"schema_version": "testline-v3.0", "run_id": "RUN-1", "event_id": "PE-1", "timestamp": "t", "station": "curing", "old_values_json": "{}", "new_values_json": "{}", "effective_from_segment_id": "SEG-2", "source": "operator"},
    "spc_event": {"schema_version": "testline-v3.0", "run_id": "RUN-1", "event_id": "SPC-1", "signal_name": "curing_temp_c", "chart_type": "I-MR", "severity": "warning", "event_kind": "process_out_of_control", "rule_code": "POINT_BEYOND_LIMIT", "started_at": "t", "ended_at": "", "affected_points": 1, "baseline_version": "BASE-1"},
    "quality_prediction": {"schema_version": "testline-v3.0", "run_id": "RUN-1", "prediction_id": "QP-1", "segment_id": "SEG-1", "timestamp": "t", "target": "peel_strength_n_mm", "prediction": 1.3, "unit": "N/mm", "model_version": "M-1", "input_cutoff_at": "t", "support_status": "in_range"},
    "manifest": {"schema_version": "testline-v3.0", "run_id": "RUN-1", "product_id": "FCCL-DEMO-001", "recipe_id": "SIM-RECIPE-3.0", "seed": 42, "scenario": "stable", "status": "running", "started_at": "t", "checkpoint_at": "t", "files": {}},
}


def test_all_seven_schema_kinds_accept_valid_fixture() -> None:
    assert set(VALID) == set(SCHEMAS)
    for kind, record in VALID.items():
        assert_valid(kind, record)


@pytest.mark.parametrize("kind", list(VALID))
def test_missing_field_has_structured_reason(kind: str) -> None:
    record = copy.deepcopy(VALID[kind]); record.pop(next(iter(SCHEMAS[kind])))
    assert "MISSING_FIELD" in {i.code for i in validate_record(kind, record)}


def test_wrong_unit_and_version_are_rejected() -> None:
    record = copy.deepcopy(VALID["process_signal"]); record["unit"] = "F"
    assert "UNIT_MISMATCH" in {i.code for i in validate_record("process_signal", record)}
    record = copy.deepcopy(VALID["manifest"]); record["schema_version"] = "testline-v2"
    assert "INCOMPATIBLE_SCHEMA_VERSION" in {i.code for i in validate_record("manifest", record)}
