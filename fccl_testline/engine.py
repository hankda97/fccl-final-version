from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .alarms import AlarmManager
from .dataset import FEATURE_ALLOWLIST
from .inference import QualityInferenceService
from .process_spc import IncrementalSPC, imr_limits, xbar_r_limits
from .run_store import RunStore
from .simulation import TestlineSimulator


class TestlineEngine:
    __test__ = False

    def __init__(self, *, project_root: Path, run_id: str, seed: int = 9001, scenario: str = "stable") -> None:
        self.project_root = project_root.resolve(); self.run_id = run_id
        self.simulator = TestlineSimulator(seed=seed, scenario=scenario)
        self.store = RunStore(self.project_root / "runtime_data")
        self.inference = QualityInferenceService(self.project_root / "artifacts/synthetic_v3/quality-v3.0")
        self.alarms = AlarmManager()
        reference = pd.read_csv(self.project_root / "generated_data/v3/stable_reference.csv")
        thickness_groups = reference[[f"dry_thickness_{i}_um" for i in range(1,6)]].head(30).values.tolist()
        self.spc = {
            "dry_thickness_mean_um": IncrementalSPC(xbar_r_limits(thickness_groups)),
            "curing_temp_c": IncrementalSPC(imr_limits(reference.curing_temp_actual_c.head(50).tolist())),
            "exhaust_airflow_m3_h": IncrementalSPC(imr_limits(reference.exhaust_airflow_actual_m3_h.head(50).tolist(), chart_type="EWMA")),
            "line_speed_m_min": IncrementalSPC(imr_limits(reference.line_speed_actual_m_min.head(50).tolist())),
            "lamination_pressure_mpa": IncrementalSPC(imr_limits(reference.lamination_pressure_actual_mpa.head(50).tolist())),
        }
        self.tables: dict[str, list[dict[str, Any]]] = {name: [] for name in ("process_signals", "material_segments", "parameter_events", "spc_events", "quality_predictions")}
        self.candidates = pd.DataFrame(); self.store.create(run_id, seed=seed, scenario=scenario)

    def _candidate(self, record: Mapping[str, Any], segment_id: str, quality_available_at: datetime) -> dict[str, Any]:
        mapping = {
            "line_speed_actual_m_min": record["line_speed_m_min"], "coating_gap_actual_um": record["coating_gap_um"],
            "coating_temp_actual_c": record["coating_temp_c"], "coating_viscosity_actual_mpa_s": record["coating_viscosity_mpa_s"],
            "dry_thickness_mean_um": record["dry_thickness_mean_um"], "curing_temp_actual_c": record["curing_temp_c"],
            "exhaust_airflow_actual_m3_h": record["exhaust_airflow_m3_h"], "curing_time_actual_min": record["curing_time_min"],
            "lamination_temp_actual_c": record["lamination_temp_c"], "lamination_pressure_actual_mpa": record["lamination_pressure_mpa"],
            "lamination_time_actual_min": record["lamination_time_min"], "ambient_temp_c": 23.0, "ambient_rh_pct": 52.0,
        }
        return {"segment_id": segment_id, "quality_available_at": quality_available_at.isoformat(), **mapping}

    def step(self, ticks: int = 1) -> None:
        if not self.simulator.clock.running: self.simulator.clock.start()
        for _ in range(ticks):
            record = self.simulator.clock.tick(self.simulator.tick); timestamp = record["timestamp"]
            signal_map = {
                "dry_thickness_mean_um": (record["dry_thickness_mean_um"], "um", 25.0),
                "curing_temp_c": (record["curing_temp_c"], "degC", self.simulator.setpoints["curing_temp_c"]),
                "exhaust_airflow_m3_h": (record["exhaust_airflow_m3_h"], "m3/h", self.simulator.setpoints["exhaust_airflow_m3_h"]),
                "line_speed_m_min": (record["line_speed_m_min"], "m/min", self.simulator.setpoints["line_speed_m_min"]),
                "lamination_pressure_mpa": (record["lamination_pressure_mpa"], "MPa", self.simulator.setpoints["lamination_pressure_mpa"]),
            }
            for name, (value, unit, setpoint) in signal_map.items():
                self.tables["process_signals"].append({"run_id": self.run_id, "tick_sequence": record["sequence"], "timestamp": timestamp.isoformat(), "signal_name": name, "actual_value": value, "setpoint_value": setpoint, "unit": unit})
                if name == "dry_thickness_mean_um": result = self.spc[name].update_subgroup(record["thickness_points_um"]); beyond = bool(result["xbar_beyond_limit"] or result["range_beyond_limit"]); out_spec = value < 23 or value > 27
                else: result = self.spc[name].update_individual(value); beyond = bool(result["beyond_limit"]); out_spec = False
                self.alarms.observe(signal=name, timestamp=timestamp, beyond_control=beyond, out_of_spec=out_spec)
            if record["sequence"] % 6 == 0:
                segment = self.simulator.segments[-1]
                self.tables["material_segments"].append({"run_id": self.run_id, "segment_id": segment.segment_id, "coating_exit_s": segment.coating_exit_s, "curing_exit_s": segment.curing_exit_s, "lamination_exit_s": segment.lamination_exit_s, "quality_available_s": segment.quality_available_s})
                candidate = self._candidate(record, segment.segment_id, self.simulator.clock.started_at + pd.Timedelta(seconds=segment.quality_available_s))
                self.candidates = pd.concat([self.candidates, pd.DataFrame([candidate])], ignore_index=True)
            predictions = self.inference.update(self.candidates, now=timestamp, simulated_seconds=self.simulator.clock.simulated_seconds)
            self.tables["quality_predictions"].extend({"run_id": self.run_id, **p} for p in predictions)
            if record["sequence"] % 12 == 0: self.checkpoint()

    def apply_parameters(self, values: Mapping[str, float]) -> None:
        event = self.simulator.submit_parameters(values, self.simulator.clock.started_at + pd.Timedelta(seconds=self.simulator.clock.simulated_seconds))
        self.tables["parameter_events"].append({"run_id": self.run_id, "event_id": event.event_id, "timestamp": event.timestamp.isoformat(), "station": "multi", "old_values_json": json.dumps(event.old_values), "new_values_json": json.dumps(event.new_values), "effective_from_segment_id": f"SEG-{event.effective_from_segment:06d}", "source": event.source})
        self.alarms.note_parameter_event(event.event_id)

    def checkpoint(self) -> None:
        self.tables["spc_events"] = [{"run_id": self.run_id, "event_id": e.event_id, "signal_name": e.signal_name, "event_kind": e.event_kind, "severity": e.severity.value, "started_at": e.started_at.isoformat(), "ended_at": e.ended_at.isoformat() if e.ended_at else "", "affected_points": e.affected_points, "rule_codes": ",".join(sorted(e.rule_codes))} for e in self.alarms.events]
        self.store.checkpoint(self.run_id, self.tables, cutoff_sequence=self.simulator.clock.sequence)

    def stop(self) -> dict[str, Any]:
        self.checkpoint(); self.simulator.clock.running = False
        return self.store.finalize(self.run_id)
