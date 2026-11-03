from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

import numpy as np

from .config import load_product_recipe
from .generation import DEMO_SEEDS, SCENARIOS
from .types import validate_candidate_set


TICK_SECONDS = 5


@dataclass
class SimulationClock:
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sequence: int = 0
    simulated_seconds: int = 0
    multiplier: float = 1.0
    running: bool = False
    paused_reason: str | None = None
    preloaded_steady_state: bool = True
    _in_flight: bool = False

    def start(self) -> None:
        self.running = True; self.paused_reason = None

    def tick(self, callback: Callable[[int, datetime], Any], *, measured_elapsed: float | None = None) -> Any:
        if not self.running: raise RuntimeError("CLOCK_NOT_RUNNING")
        if self._in_flight: raise RuntimeError("OVERLAPPING_TICK")
        self._in_flight = True
        next_sequence = self.sequence + 1
        next_time = self.started_at + timedelta(seconds=self.simulated_seconds + TICK_SECONDS)
        begun = time.perf_counter()
        try:
            result = callback(next_sequence, next_time)
        except Exception:
            self.running = False; self.paused_reason = "tick_error"; raise
        finally:
            self._in_flight = False
        elapsed = measured_elapsed if measured_elapsed is not None else time.perf_counter() - begun
        self.sequence = next_sequence; self.simulated_seconds += TICK_SECONDS
        allowed = TICK_SECONDS / max(self.multiplier, .01)
        if elapsed > allowed:
            if self.multiplier > .25: self.multiplier = max(.25, self.multiplier / 2); self.paused_reason = "auto_slowdown"
            else: self.running = False; self.paused_reason = "compute_overrun"
        return result


@dataclass(frozen=True)
class ParameterEvent:
    event_id: str
    timestamp: datetime
    old_values: Mapping[str, float]
    new_values: Mapping[str, float]
    effective_from_segment: int
    source: str = "operator"


@dataclass
class MaterialSegment:
    index: int
    segment_id: str
    coating_exit_s: int
    curing_exit_s: int
    lamination_exit_s: int
    quality_available_s: int
    parameter_versions: dict[str, int]


class TestlineSimulator:
    __test__ = False

    def __init__(self, *, seed: int = DEMO_SEEDS[0], scenario: str = "stable") -> None:
        if seed not in DEMO_SEEDS: raise ValueError("DEMO_SEED_REQUIRED")
        if scenario not in SCENARIOS: raise ValueError("UNKNOWN_SCENARIO")
        self.seed = seed; self.scenario = scenario; self.rng = np.random.default_rng(seed)
        cfg = load_product_recipe()["recipe"]["parameters"]
        self.setpoints = {name: float(item["default"]) for name, item in cfg.items()}
        self.actuals = dict(self.setpoints); self.clock = SimulationClock(started_at=datetime(2026, 1, 1, tzinfo=timezone.utc)); self.events: list[ParameterEvent] = []
        self.segments: list[MaterialSegment] = []; self.signals: list[dict[str, Any]] = []
        self._preload()

    def _preload(self) -> None:
        # Four simultaneous sections represent a continuous roll already occupying all stations.
        for index in range(-3, 1):
            self.segments.append(self._make_segment(index, max(0, index * 30)))

    def _make_segment(self, index: int, coating_exit_s: int) -> MaterialSegment:
        return MaterialSegment(index, f"SEG-{index:06d}", coating_exit_s, coating_exit_s + 30, coating_exit_s + 60, coating_exit_s + 90, {name: len(self.events) for name in self.setpoints})

    def submit_parameters(self, candidate: Mapping[str, float], timestamp: datetime | None = None) -> ParameterEvent:
        validated = validate_candidate_set(candidate)
        event = ParameterEvent(f"PE-{len(self.events)+1:06d}", timestamp or datetime.now(timezone.utc), dict(self.setpoints), dict(validated), max(s.index for s in self.segments) + 1)
        self.events.append(event); self.setpoints.update(validated)
        return event

    def _scenario_shift(self, name: str, seq: int) -> float:
        p = max(0.0, (seq - 20) / 60)
        mapping = {
            "thickness_increase": {"dry_thickness_mean_um": 2.2*p}, "thickness_decrease": {"dry_thickness_mean_um": -2.2*p},
            "temperature_drop": {"curing_temp_c": -6*p}, "airflow_decay": {"exhaust_airflow_m3_h": -400*p},
            "pressure_drift": {"lamination_pressure_mpa": -.35*p},
            "compound_drift": {"dry_thickness_mean_um": 1.4*p, "curing_temp_c": -3.5*p, "exhaust_airflow_m3_h": -220*p, "lamination_pressure_mpa": -.18*p},
        }
        return mapping.get(self.scenario, {}).get(name, 0.0)

    def tick(self, sequence: int, timestamp: datetime) -> dict[str, Any]:
        for name, setpoint in self.setpoints.items():
            self.actuals[name] += .28 * (setpoint - self.actuals[name]) + float(self.rng.normal(0, max(abs(setpoint)*.001, .005)))
        thickness = 25 + .55*(self.actuals["coating_gap_um"]-28) - .28*(self.actuals["line_speed_m_min"]-4.8) + self._scenario_shift("dry_thickness_mean_um", sequence)
        record = {"sequence": sequence, "timestamp": timestamp, **self.actuals, "dry_thickness_mean_um": thickness + self.rng.normal(0,.08)}
        record["curing_temp_c"] += self._scenario_shift("curing_temp_c", sequence)
        record["exhaust_airflow_m3_h"] += self._scenario_shift("exhaust_airflow_m3_h", sequence)
        record["lamination_pressure_mpa"] += self._scenario_shift("lamination_pressure_mpa", sequence)
        record["thickness_points_um"] = [record["dry_thickness_mean_um"] + float(x) for x in self.rng.normal(0,.1,5)]
        self.signals.append(record)
        if sequence % 6 == 0:
            self.segments.append(self._make_segment(max(s.index for s in self.segments)+1, sequence*TICK_SECONDS))
        return record

    def advance(self, ticks: int) -> None:
        if not self.clock.running: self.clock.start()
        for _ in range(ticks): self.clock.tick(self.tick)

    def segments_at_station(self, now_s: int) -> dict[str, list[MaterialSegment]]:
        return {
            "coating": [s for s in self.segments if now_s <= s.coating_exit_s],
            "curing": [s for s in self.segments if s.coating_exit_s < now_s <= s.curing_exit_s],
            "lamination": [s for s in self.segments if s.curing_exit_s < now_s <= s.lamination_exit_s],
            "quality_wait": [s for s in self.segments if s.lamination_exit_s < now_s < s.quality_available_s],
            "quality_ready": [s for s in self.segments if s.quality_available_s <= now_s],
        }

    def snapshot_hash(self) -> str:
        import hashlib
        serializable = [{**r, "timestamp": r["timestamp"].isoformat()} for r in self.signals]
        return hashlib.sha256(json.dumps(serializable, sort_keys=True).encode()).hexdigest()
