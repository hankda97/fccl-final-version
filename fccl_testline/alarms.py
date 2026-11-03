from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    SEVERE = "severe"
    INSUFFICIENT = "insufficient_evidence"


@dataclass
class AlarmGroup:
    event_id: str
    signal_name: str
    event_kind: str
    started_at: datetime
    severity: Severity
    rule_codes: set[str] = field(default_factory=set)
    affected_points: int = 0
    recovery_points: int = 0
    ended_at: datetime | None = None
    parameter_event_ids: list[str] = field(default_factory=list)


class AlarmManager:
    def __init__(self, recovery_required: int = 5) -> None:
        self.recovery_required = recovery_required; self.events: list[AlarmGroup] = []; self.status: dict[str, Severity] = {}

    def _open(self, signal: str, kind: str, timestamp: datetime) -> AlarmGroup:
        active = next((e for e in reversed(self.events) if e.signal_name == signal and e.event_kind == kind and e.ended_at is None), None)
        if active: return active
        event = AlarmGroup(f"ALARM-{len(self.events)+1:06d}", signal, kind, timestamp, Severity.WARNING)
        self.events.append(event); return event

    def observe(self, *, signal: str, timestamp: datetime, beyond_control: bool, out_of_spec: bool, valid: bool = True) -> Severity:
        if not valid:
            self.status[signal] = Severity.INSUFFICIENT; return Severity.INSUFFICIENT
        triggered: list[AlarmGroup] = []
        if beyond_control:
            event = self._open(signal, "process_out_of_control", timestamp); event.rule_codes.add("POINT_BEYOND_CONTROL_LIMIT"); triggered.append(event)
        if out_of_spec:
            event = self._open(signal, "product_out_of_spec", timestamp); event.rule_codes.add("POINT_OUTSIDE_PRODUCT_SPEC"); triggered.append(event)
        for event in triggered:
            event.affected_points += 1; event.recovery_points = 0
            event.severity = Severity.SEVERE if event.affected_points >= 3 else Severity.WARNING
        active = [e for e in self.events if e.signal_name == signal and e.ended_at is None]
        if not beyond_control and not out_of_spec:
            for event in active:
                event.recovery_points += 1
                if event.recovery_points >= self.recovery_required: event.ended_at = timestamp
            active = [e for e in active if e.ended_at is None]
        severity = max((e.severity for e in active), key=lambda s: [Severity.NORMAL, Severity.WARNING, Severity.SEVERE].index(s), default=Severity.NORMAL)
        self.status[signal] = severity; return severity

    def note_parameter_event(self, event_id: str) -> None:
        for event in self.events:
            if event.ended_at is None and event_id not in event.parameter_event_ids: event.parameter_event_ids.append(event_id)

    def summary(self, limit: int = 5) -> list[AlarmGroup]:
        active = [e for e in self.events if e.ended_at is None]
        active.sort(key=lambda e: (e.severity == Severity.SEVERE, e.started_at), reverse=True)
        return active[:limit]
