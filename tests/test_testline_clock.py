from datetime import datetime, timezone

import pytest

from fccl_testline.simulation import SimulationClock, TestlineSimulator


def test_clock_has_unique_contiguous_ticks_and_preloaded_line() -> None:
    sim = TestlineSimulator(seed=9001); assert len(sim.segments) == 4
    sim.advance(12)
    assert [x["sequence"] for x in sim.signals] == list(range(1, 13))
    assert all((b["timestamp"] - a["timestamp"]).total_seconds() == 5 for a, b in zip(sim.signals, sim.signals[1:]))


def test_clock_rejects_overlap_and_slows_then_pauses_without_skip() -> None:
    clock = SimulationClock(); clock.start(); clock._in_flight = True
    with pytest.raises(RuntimeError, match="OVERLAPPING_TICK"): clock.tick(lambda *_: None)
    clock._in_flight = False
    for expected in range(1, 3):
        clock.tick(lambda *_: None, measured_elapsed=100)
        assert clock.sequence == expected
    assert clock.multiplier == .25 and clock.running
    clock.tick(lambda *_: None, measured_elapsed=100)
    assert not clock.running and clock.paused_reason == "compute_overrun" and clock.sequence == 3


def test_failed_tick_does_not_commit_sequence() -> None:
    clock = SimulationClock(); clock.start()
    with pytest.raises(ValueError): clock.tick(lambda *_: (_ for _ in ()).throw(ValueError("boom")))
    assert clock.sequence == 0 and clock.simulated_seconds == 0 and not clock.running
