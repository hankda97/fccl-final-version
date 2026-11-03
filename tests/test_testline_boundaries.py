from datetime import datetime, timedelta, timezone

import pytest

from fccl_testline.config import load_product_recipe
from fccl_testline.types import MaterialBoundary, Station, event_applies, quality_is_available, validate_candidate_set, validate_feature_cutoff, validate_model_support


def primary_defaults():
    return {k: v["default"] for k, v in load_product_recipe()["recipe"]["parameters"].items() if not v.get("advanced")}


def test_parameter_set_is_atomic_and_ui_bounded() -> None:
    values = primary_defaults(); assert validate_candidate_set(values) == values
    partial = dict(values); partial.pop("curing_temp_c")
    with pytest.raises(ValueError, match="PARTIAL_PARAMETER_SET"):
        validate_candidate_set(partial)
    values["line_speed_m_min"] = 5.61
    with pytest.raises(ValueError, match="OUTSIDE_UI_RANGE"):
        validate_candidate_set(values)


def test_station_boundary_does_not_rewrite_past_material() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    past = MaterialBoundary("SEG-1", Station.COATING, now - timedelta(seconds=1))
    future = MaterialBoundary("SEG-2", Station.COATING, now + timedelta(seconds=1))
    assert not event_applies(event_station=Station.COATING, event_at=now, material=past)
    assert event_applies(event_station=Station.COATING, event_at=now, material=future)
    with pytest.raises(ValueError, match="STATION_BOUNDARY_MISMATCH"):
        event_applies(event_station=Station.CURING, event_at=now, material=future)


def test_quality_delay_and_future_features() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert quality_is_available(lamination_exited_at=now - timedelta(minutes=2), quality_available_at=now - timedelta(minutes=1), now=now)
    assert not quality_is_available(lamination_exited_at=None, quality_available_at=now, now=now)
    with pytest.raises(ValueError, match="FUTURE_FEATURE"):
        validate_feature_cutoff({"curing_temp_c": now + timedelta(seconds=1)}, inference_at=now)


def test_model_support_must_come_from_train_manifest_not_ui() -> None:
    manifest = {"support_range_source": "train_manifest", "feature_support_ranges": {"line_speed_m_min": {"min": 4.2, "max": 5.3}}}
    assert validate_model_support({"line_speed_m_min": 4.8}, manifest) == {"line_speed_m_min": "in_range"}
    assert validate_model_support({"line_speed_m_min": 5.4}, manifest) == {"line_speed_m_min": "extrapolation"}
    manifest["support_range_source"] = "ui_range"
    with pytest.raises(ValueError, match="MODEL_SUPPORT_SOURCE_INVALID"):
        validate_model_support({"line_speed_m_min": 4.8}, manifest)
