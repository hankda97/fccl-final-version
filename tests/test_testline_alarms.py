from datetime import datetime, timedelta, timezone

from fccl_testline.alarms import AlarmManager, Severity


def test_long_drift_groups_events_and_parameter_does_not_clear() -> None:
    alarms = AlarmManager(recovery_required=3); start = datetime(2026,1,1,tzinfo=timezone.utc)
    for i in range(20): alarms.observe(signal="curing_temp_c", timestamp=start+timedelta(seconds=5*i), beyond_control=True, out_of_spec=False)
    assert len(alarms.events) == 1 and alarms.events[0].affected_points == 20
    assert alarms.events[0].severity == Severity.SEVERE
    alarms.note_parameter_event("PE-1")
    assert alarms.events[0].ended_at is None and alarms.events[0].parameter_event_ids == ["PE-1"]
    for i in range(2): alarms.observe(signal="curing_temp_c", timestamp=start+timedelta(minutes=2, seconds=5*i), beyond_control=False, out_of_spec=False)
    assert alarms.events[0].ended_at is None
    alarms.observe(signal="curing_temp_c", timestamp=start+timedelta(minutes=3), beyond_control=False, out_of_spec=False)
    assert alarms.events[0].ended_at is not None and alarms.status["curing_temp_c"] == Severity.NORMAL


def test_process_and_product_events_are_separate_and_summary_is_bounded() -> None:
    alarms = AlarmManager(); now = datetime(2026,1,1,tzinfo=timezone.utc)
    alarms.observe(signal="dry_thickness_um", timestamp=now, beyond_control=True, out_of_spec=True)
    assert {e.event_kind for e in alarms.events} == {"process_out_of_control", "product_out_of_spec"}
    for i in range(10): alarms.observe(signal=f"signal-{i}", timestamp=now, beyond_control=True, out_of_spec=False)
    assert len(alarms.summary()) == 5


def test_invalid_point_reports_insufficient_evidence_without_fake_alarm() -> None:
    alarms = AlarmManager(); now = datetime(2026,1,1,tzinfo=timezone.utc)
    assert alarms.observe(signal="airflow", timestamp=now, beyond_control=False, out_of_spec=False, valid=False) == Severity.INSUFFICIENT
    assert alarms.events == []
