from datetime import datetime, timezone

import pytest

from fccl_testline.config import load_product_recipe
from fccl_testline.simulation import TestlineSimulator


def primary_defaults():
    return {k: v["default"] for k, v in load_product_recipe()["recipe"]["parameters"].items() if not v.get("advanced")}


def test_continuous_material_stations_and_quality_delay() -> None:
    sim = TestlineSimulator(seed=9001)
    sim.advance(24)  # 120 seconds
    states = sim.segments_at_station(125)
    assert states["quality_ready"]
    assert states["quality_wait"]
    assert states["lamination"]
    ready_ids = {s.segment_id for s in states["quality_ready"]}
    assert not ready_ids & {s.segment_id for s in states["quality_wait"]}


def test_parameter_event_changes_only_future_material_boundary() -> None:
    sim = TestlineSimulator(seed=9001); sim.advance(6)
    before = {s.segment_id: dict(s.parameter_versions) for s in sim.segments}
    candidate = primary_defaults(); candidate["coating_gap_um"] = 29.0
    event = sim.submit_parameters(candidate, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert event.effective_from_segment == max(s.index for s in sim.segments) + 1
    assert {s.segment_id: s.parameter_versions for s in sim.segments} == before
    sim.advance(6)
    future = max(sim.segments, key=lambda s: s.index)
    assert future.index >= event.effective_from_segment
    assert set(future.parameter_versions.values()) == {1}


def test_parameter_submission_is_atomic_and_immutable() -> None:
    sim = TestlineSimulator(seed=9001); original = dict(sim.setpoints)
    invalid = primary_defaults(); invalid["curing_temp_c"] = 999
    with pytest.raises(ValueError, match="OUTSIDE_UI_RANGE"):
        sim.submit_parameters(invalid)
    assert sim.setpoints == original and sim.events == []
    one = primary_defaults(); one["line_speed_m_min"] = 4.9
    first = sim.submit_parameters(one); two = primary_defaults(); two["line_speed_m_min"] = 5.0
    second = sim.submit_parameters(two)
    assert first.event_id != second.event_id
    assert first.new_values["line_speed_m_min"] == 4.9
    assert second.old_values["line_speed_m_min"] == 4.9
