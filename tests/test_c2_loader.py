from io import StringIO
import json
from pathlib import Path

import pandas as pd
import pytest

from c_dashboard.data.loader import filter_rows, input_eligibility, load_csv
from c_dashboard.data.schema import FEATURE_UNITS, MappingProfile, parse_mapping

FIXTURES = Path(__file__).parent / "fixtures" / "c_mock"


def fixture(name="normal"):
    return (FIXTURES / f"{name}.csv").read_bytes()


def codes(result):
    return {item.code for item in result.issues}


def test_normal_bom_and_identification():
    result = load_csv(b"\xef\xbb\xbf" + fixture(), "normal.csv")
    assert result.accepted
    assert len(result.frame) == 150
    assert result.frame.sample_id.is_unique
    assert result.frame.source_row.iloc[0] == 2
    assert str(result.frame.timestamp.dt.tz) == "Asia/Taipei"
    assert not result.frame.local_segment_id.any()
    eligible = input_eligibility(result.frame)
    assert eligible["prediction_input_rows"] == 150
    assert eligible["grouped_quality_rows"]["heat_resistance_c"] == 150


@pytest.mark.parametrize("payload", [b"", b" \n", b"a,b\n", b"a,a\n1,2\n", b"a,b\n1\n", b'"a,b\n', b"\xff\xfe"])
def test_bad_csv_is_rejected(payload):
    result = load_csv(payload, "bad.csv")
    assert not result.accepted
    assert "CSV_PARSE" in codes(result)


def test_non_csv_and_missing_identifiers():
    assert "FILE_TYPE" in codes(load_csv(fixture(), "data.xlsx"))
    result = load_csv(fixture("missing_columns"), "missing.csv")
    assert not result.accepted
    assert any(item.code == "MISSING_COLUMN" and item.field == "timestamp" for item in result.issues)


def test_whitespace_normalization_is_reported_and_original_values_preserved():
    raw = pd.read_csv(StringIO(fixture().decode()), dtype=str)
    raw.loc[0, "product_batch"] = "  M-B01  "
    raw.loc[0, "line_speed_m_min"] = " 2.0 "
    result = load_csv(raw.to_csv(index=False).encode(), "whitespace.csv")
    assert result.accepted
    assert "VALUE_TRIMMED" in codes(result)
    assert result.raw_frame.loc[2, "product_batch"] == "  M-B01  "
    assert result.raw_frame.loc[2, "line_speed_m_min"] == " 2.0 "
    assert result.frame.iloc[0].product_batch == "M-B01"
    assert result.frame.iloc[0].line_speed_m_min == 2.0


def test_invalid_times_numbers_missing_and_duplicates_are_reported_without_imputation():
    result = load_csv(fixture("invalid_values"), "invalid.csv")
    assert result.accepted  # Good rows remain available for inspection.
    assert {"INVALID_TIME", "OUT_OF_RANGE", "INVALID_NUMBER", "MISSING_VALUE", "DUPLICATE_RECORD"} <= codes(result)
    by_row = result.frame.set_index("source_row")
    assert pd.isna(by_row.loc[2, "timestamp"])
    assert pd.isna(by_row.loc[3, "ambient_rh_pct"])
    assert pd.isna(by_row.loc[4, "line_speed_m_min"])
    assert pd.isna(by_row.loc[5, "peel_strength_n_mm"])
    assert result.raw_frame.loc[4, "line_speed_m_min"] == "invalid"
    assert result.frame.duplicate_record.sum() == 2


def test_partial_quality_and_no_quality_still_allow_data_and_feature_inspection():
    partial = load_csv(fixture("partial_quality"), "partial.csv")
    assert partial.accepted and "heat_resistance_c" not in partial.frame
    eligible = input_eligibility(partial.frame)
    assert eligible["quality_rows"]["heat_resistance_c"] == 0
    assert eligible["quality_rows"]["peel_strength_n_mm"] == 150
    no_quality = load_csv(fixture("no_quality"), "none.csv")
    assert no_quality.accepted
    assert input_eligibility(no_quality.frame)["prediction_input_rows"] == 150
    assert all(value == 0 for value in input_eligibility(no_quality.frame)["quality_rows"].values())


def test_missing_features_and_no_subgroup_are_local_capability_limitations():
    raw = pd.read_csv(StringIO(fixture("ungrouped").decode())).drop(columns=["curing_temp_c", "segment_id"])
    result = load_csv(raw.to_csv(index=False).encode(), "source.csv")
    assert result.accepted
    assert result.frame.local_segment_id.all()
    assert "LOCAL_SEGMENT_ID" in codes(result)
    eligible = input_eligibility(result.frame)
    assert eligible["view_rows"] == 150
    assert eligible["prediction_input_rows"] == 0
    assert all(value == 0 for value in eligible["grouped_quality_rows"].values())


def test_explicit_names_units_and_timezone_mapping():
    raw = pd.read_csv(StringIO(fixture().decode()))
    raw = raw.rename(columns={"timestamp": "時間", "line_speed_m_min": "速度", "ambient_temp_c": "溫度"})
    raw["時間"] = raw["時間"].str.replace("+08:00", "", regex=False)
    raw["速度"] = raw["速度"] / 0.06
    raw["溫度"] = raw["溫度"] * 9 / 5 + 32
    mapping = parse_mapping(json.dumps({
        "name": "來源轉接測試", "version": "mapping-1", "timezone": "Asia/Taipei",
        "columns": {"timestamp": {"column": "時間"},
                    "line_speed_m_min": {"column": "速度", "unit": "mm/s"},
                    "ambient_temp_c": {"column": "溫度", "unit": "°F"}},
    }))
    result = load_csv(raw.to_csv(index=False).encode(), "mapped.csv", profile=mapping)
    assert result.accepted
    assert {"COLUMN_MAPPED", "UNIT_CONVERTED"} <= codes(result)
    assert result.frame.line_speed_m_min.eq(2.0).all()
    assert result.frame.ambient_temp_c.iloc[0] == pytest.approx(24.112)


def test_naive_time_is_not_silently_localized():
    payload = fixture().decode().replace("+08:00", "").encode()
    result = load_csv(payload, "naive.csv")
    assert not result.accepted
    assert "INVALID_TIME" in codes(result)


def test_bad_mapping_units_and_collisions_are_reported():
    with pytest.raises(ValueError):
        parse_mapping('{"columns":{"line_speed_m_min":{"column":"speed"}}}')
    with pytest.raises(ValueError):
        parse_mapping('{"columns":{"unknown":{"column":"x"}}}')
    mapping = parse_mapping('{"columns":{"line_speed_m_min":{"column":"line_speed_m_min","unit":"mph"}}}')
    result = load_csv(fixture(), "units.csv", profile=mapping)
    assert result.accepted
    assert "UNIT_MISMATCH" in codes(result)
    assert result.frame.line_speed_m_min.isna().all()
    assert input_eligibility(result.frame)["prediction_input_rows"] == 0
    mapping = parse_mapping('{"columns":{"segment_id":{"column":"product_batch"}}}')
    assert "MAPPING_COLLISION" in codes(load_csv(fixture(), "collision.csv", profile=mapping))


def test_stable_sort_and_batch_time_filter_keep_original_rows():
    raw = pd.read_csv(StringIO(fixture().decode())).iloc[::-1]
    result = load_csv(raw.to_csv(index=False).encode(), "reversed.csv")
    assert "TIME_SORTED" in codes(result)
    assert result.frame.available_at.is_monotonic_increasing
    selected = filter_rows(result.frame, "M-B02", "2026-11-01T08:16:00+08:00", "2026-11-01T08:18:00+08:00")
    assert len(selected) == 15
    assert selected.product_batch.eq("M-B02").all()
    assert selected.sample_id.isin(result.frame.sample_id).all()
    assert filter_rows(result.frame, "no-such-batch").empty


def test_availability_order_and_finite_numeric_values():
    text = fixture().decode().replace("2026-11-01T08:00:00+08:00,2026-11-01T08:00:00+08:00",
                                     "2026-11-01T08:00:00+08:00,2026-10-31T08:00:00+08:00", 1)
    result = load_csv(text.encode(), "bad-availability.csv")
    assert "INVALID_AVAILABILITY" in codes(result)
    raw = pd.read_csv(StringIO(fixture().decode()), dtype=str)
    raw.loc[0, "line_speed_m_min"] = "inf"
    result = load_csv(raw.to_csv(index=False).encode(), "inf.csv")
    assert "INVALID_NUMBER" in codes(result)
    assert pd.isna(result.frame.set_index("source_row").loc[2, "line_speed_m_min"])
