from dataclasses import replace

from c3_support import PEEL, hand_history, monitoring
from c_dashboard.spc.baseline import build_baseline
from c_dashboard.spc.incidents import group_spc_incidents, incident_events
from c_dashboard.spc.service import compute_spc
from c_dashboard.spc.types import SourceContext


def result_for(means):
    history, profile = hand_history()
    rows, _ = monitoring(means)
    baseline = build_baseline(history, profile)
    return compute_spc(rows, SourceContext("incident-test", profile), baseline)


def test_incidents_are_pure_stable_and_conserve_raw_event_ids():
    result = result_for([0.5, 0.45, 0.4, 1.25, 0.35, 0.3])
    original = result.events
    first = group_spc_incidents(result)
    assert first == group_spc_incidents(result)
    assert result.events == original
    assert {event.event_id for event in result.events} == {
        event_id for incident in first for event_id in incident.event_ids
    }
    assert len({incident.incident_id for incident in first}) == len(first)
    assert len(first) == 2


def test_incident_summary_combines_overlapping_rules_and_marks_latest_active():
    result = result_for([0.5] * 10)
    incidents = group_spc_incidents(result)
    peel = [incident for incident in incidents if incident.target == PEEL]
    assert len(peel) == 1
    incident = peel[0]
    assert incident.active
    assert incident.subgroup_count == 10
    assert incident.event_count == len(result.events)
    assert incident.first_subgroup == "G0" and incident.latest_subgroup == "G9"
    assert incident.started_at < incident.latest_at
    assert set(incident.rules) == {"BELOW_CL_9", "BEYOND_LIMIT"}
    assert dict(incident.rule_counts) == {"BELOW_CL_9": 2, "BEYOND_LIMIT": 10}
    assert incident.max_standardized_deviation > 1
    assert tuple(event.event_id for event in incident_events(result, incident)) == incident.event_ids


def test_invalid_or_break_boundary_closes_run_without_losing_events():
    result = result_for([0.5, 0.45, 0.4])
    target = result.target(PEEL)
    groups = list(target.groups)
    groups[1] = replace(groups[1], break_before=True)
    altered = replace(result, targets=tuple(
        replace(item, groups=tuple(groups)) if item.target == PEEL else item
        for item in result.targets
    ))
    incidents = [incident for incident in group_spc_incidents(altered) if incident.target == PEEL]
    assert len(incidents) == 2
    assert not incidents[0].active and incidents[1].active
    assert sum(item.event_count for item in incidents) == len(result.events)
