"""Presentation-only SPC incident groups; raw rule events remain authoritative."""

from dataclasses import dataclass
from hashlib import sha256
import json

from c_dashboard.spc.types import SpcEvent, SpcResult


@dataclass(frozen=True)
class SpcIncident:
    incident_id: str
    source_id: str
    scope_id: str
    target: str
    batch: str
    first_subgroup: str
    latest_subgroup: str
    started_at: str
    latest_at: str
    active: bool
    rules: tuple[str, ...]
    rule_counts: tuple[tuple[str, int], ...]
    subgroup_count: int
    event_count: int
    max_standardized_deviation: float
    event_ids: tuple[str, ...]


def group_spc_incidents(result: SpcResult) -> tuple[SpcIncident, ...]:
    """Group adjacent event-bearing subgroups without altering raw events."""
    events_by_key: dict[tuple[str, str, str], list[SpcEvent]] = {}
    for event in result.events:
        events_by_key.setdefault((event.target, event.batch, event.subgroup), []).append(event)

    incidents: list[SpcIncident] = []
    consumed: set[str] = set()
    for target in result.targets:
        run: list[tuple[object, tuple[SpcEvent, ...]]] = []
        previous = None
        for point in target.groups:
            point_events = tuple(events_by_key.get(
                (target.target, point.batch, point.subgroup), ()))
            boundary = bool(point.break_before or not point.valid)
            if previous is not None and point.batch != previous.batch:
                boundary = True
            if boundary or not point_events:
                if run:
                    incidents.append(_incident(result, run, active=False))
                    consumed.update(event.event_id for _, events in run for event in events)
                    run = []
            if point.valid and point_events:
                run.append((point, point_events))
            previous = point
        if run:
            incidents.append(_incident(result, run, active=True))
            consumed.update(event.event_id for _, events in run for event in events)

    # A defensive audit fallback preserves visibility if an upstream result ever
    # carries historical events outside its current target group collection.
    for event in result.events:
        if event.event_id not in consumed:
            incidents.append(_orphan_incident(result, event))

    return tuple(sorted(incidents, key=lambda item: (item.latest_at, item.incident_id)))


def incident_events(result: SpcResult, incident: SpcIncident) -> tuple[SpcEvent, ...]:
    wanted = set(incident.event_ids)
    return tuple(event for event in result.events if event.event_id in wanted)


def _incident(result, run, active):
    points = [point for point, _ in run]
    events = tuple(event for _, item in run for event in item)
    first, latest = points[0], points[-1]
    counts: dict[str, int] = {}
    for event in events:
        counts[event.rule] = counts.get(event.rule, 0) + 1
    rules = tuple(sorted(counts))
    identity = (result.source_id, result.scope_id, first.target, first.batch,
                first.subgroup, events[0].event_id)
    return SpcIncident(
        _digest(identity), result.source_id, result.scope_id, first.target,
        first.batch, first.subgroup, latest.subgroup,
        first.completed_at or first.timestamp or "", latest.completed_at or latest.timestamp or "",
        active, rules, tuple((rule, counts[rule]) for rule in rules),
        len(points), len(events), max(_standardized(event) for event in events),
        tuple(event.event_id for event in events),
    )


def _orphan_incident(result, event):
    return SpcIncident(
        _digest((result.source_id, result.scope_id, event.target, event.batch,
                 event.subgroup, event.event_id)),
        result.source_id, result.scope_id, event.target, event.batch,
        event.subgroup, event.subgroup, event.triggered_at, event.triggered_at,
        False, (event.rule,), ((event.rule, 1),), 1, 1,
        _standardized(event), (event.event_id,),
    )


def _standardized(event):
    scale = max(abs(event.ucl - event.cl), abs(event.cl - event.lcl))
    return abs(event.value - event.cl) / scale if scale > 0 else float("inf")


def _digest(values):
    return sha256(json.dumps(values, ensure_ascii=False, default=str).encode()).hexdigest()
