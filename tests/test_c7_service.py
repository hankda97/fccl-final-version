import pytest
import pandas as pd
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.data.session import commit_dataset, set_filters, selected_rows
from c_dashboard.state import WorkspaceState
from c_dashboard.replay.controller import timeline_for, snapshot_for, set_mode, operate, set_temporal_config
from c_dashboard.replay.service import tick, token
from c_dashboard.quality.controller import ensure_what_if_selection, select_what_if_segment, monitor_prediction, evaluate_what_if
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.spc.controller import analyze_workspace
from c7_support import delayed_workspace, through


@pytest.mark.parametrize('speed',[.5,1.,2.,4.])
def test_play_pause_speed_step_end_and_repeated_notifications(speed):
    w=delayed_workspace();t=timeline_for(w);r=w.replay
    operate(w,'speed',0,speed=speed);operate(w,'play',0)
    g=r.generation
    assert tick(r,t,.25,g)
    first=r.cursor
    assert first==(2 if speed==4. else 1)
    assert not tick(r,t,.25,g)
    assert token(r)==token(r)
    operate(w,'pause',.5)
    assert not tick(r,t,100,g) and r.cursor==first
    operate(w,'step',100)
    assert r.cursor==first+1 and not r.playing
    operate(w,'play',101)
    tick(r,t,101+20/speed,g)
    assert r.cursor==len(t.groups) and not r.playing
    operate(w,'step',200);operate(w,'play',200)
    assert r.cursor==len(t.groups) and not r.playing


def test_speed_anchor_restart_and_stale_lifecycle():
    w=delayed_workspace();r=w.replay;t=timeline_for(w)
    operate(w,'play',0);tick(r,t,1,r.generation)
    before=r.cursor;operate(w,'speed',1,speed=4.)
    assert r.cursor==before
    assert not tick(r,t,2,r.generation,lifecycle_token='inactive')
    old=r.generation;operate(w,'restart',2)
    assert r.cursor==0 and r.virtual_clock is None and not r.playing
    assert not tick(r,t,10,old)
    with pytest.raises(ValueError):operate(w,'speed',3,speed=100)


def test_source_filter_same_reload_failed_upload_and_temporal_version_reset():
    w=delayed_workspace();operate(w,'step',0)
    g=w.replay.generation;source=w.data.dataset
    commit_dataset(w,source)
    assert w.replay.cursor==1 and w.replay.generation==g
    from c_dashboard.data.loader import load_csv
    assert not commit_dataset(w,load_csv(b'','empty.csv'))
    assert w.replay.cursor==1
    set_temporal_config(w,{**w.data.temporal_config,'version':'new-time-version'})
    assert w.replay.cursor==0 and w.replay.generation>g
    operate(w,'step',0)
    w.data.source_version='upstream-version-change'
    timeline_for(w)
    assert w.replay.cursor==0
    operate(w,'step',0)
    set_filters(w,'M-B01',None,None)
    assert w.replay.cursor==0 and w.replay.mode=='replay'
    operate(w,'step',0)
    commit_dataset(w,load_mock_fixture('normal'))
    assert w.replay.cursor==0 and w.replay.mode=='replay' and w.data.temporal_config is None


def test_cohort_filter_keeps_late_quality_but_excludes_other_material():
    w=delayed_workspace()
    set_filters(w,None,'2026-11-01T08:00:00+08:00','2026-11-01T08:00:00+08:00')
    t=timeline_for(w)
    assert len(t.frame)==5 and t.groups[-1][0].available_at==pd.Timestamp('2026-11-01T08:00:06+08:00')
    s=through(w,'2026-11-01T08:00:10+08:00')
    assert s.rows.heat_resistance_c.notna().all() and len(s.rows)==5


def test_fixed_whatif_late_features_restart_and_explicit_reselect():
    w=delayed_workspace();rows=through(w,'2026-11-01T08:00:01+08:00').rows
    options=ensure_what_if_selection(w,rows)
    before=w.what_if.selected
    w.what_if.parameters={'line_speed_m_min':1.8}
    through(w,'2026-11-01T08:00:08+08:00')
    ensure_what_if_selection(w,selected_rows(w))
    assert w.what_if.selected==before and w.what_if.parameters=={'line_speed_m_min':1.8}
    operate(w,'restart',0)
    assert w.what_if.requires_reselect and w.what_if.parameters=={}
    through(w,'2026-11-01T08:00:10+08:00');ensure_what_if_selection(w,selected_rows(w))
    assert w.what_if.requires_reselect and evaluate_what_if(w,DeterministicMockAdapter())==(None,None)
    set_mode(w,'snapshot')
    assert w.what_if.requires_reselect
    select_what_if_segment(w,options[0],force=True)
    assert not w.what_if.requires_reselect


def test_selected_partial_feature_snapshot_is_not_silently_filled_later():
    w=delayed_workspace();rows=through(w,'2026-11-01T08:00:00+08:00').rows
    ensure_what_if_selection(w,rows)
    original=w.what_if.selected
    assert not original.process_settings
    rows=through(w,'2026-11-01T08:00:01+08:00').rows
    options=ensure_what_if_selection(w,rows)
    assert w.what_if.selected==original and not w.what_if.selected.process_settings
    select_what_if_segment(w,options[-1],force=True)
    assert w.what_if.selected.process_settings


def test_monitor_uses_latest_process_not_last_late_quality_and_missing_features():
    w=delayed_workspace();rows=through(w,'2026-11-01T08:00:04+08:00').rows
    p=monitor_prediction(w,rows,DeterministicMockAdapter())
    assert p.timestamp=='2026-11-01T08:00:04+08:00' and p.record is None
    rows=through(w,'2026-11-01T08:00:05+08:00').rows
    p=monitor_prediction(w,rows,DeterministicMockAdapter())
    assert p.record is not None and p.timestamp=='2026-11-01T08:00:04+08:00'
    rows=through(w,'2026-11-01T08:00:10+08:00').rows
    assert monitor_prediction(w,rows,DeterministicMockAdapter()).timestamp==p.timestamp


def test_spc_registered_source_fixed_baseline_complete_subgroups_and_dedup():
    w=WorkspaceState();commit_dataset(w,load_mock_fixture('trend'));set_mode(w,'replay')
    original=w.data.dataset.frame.copy(deep=True)
    empty=analyze_workspace(w);base=empty.baseline
    assert not empty.events
    for _ in range(7):
        operate(w,'step',0);r=analyze_workspace(w)
        assert r.baseline==base
    ids=[e.event_id for e in r.events]
    assert ids and len(ids)==len(set(ids))
    assert analyze_workspace(w)==r
    # Every currently visible target is already available in this explicit row-release fixture.
    from c_dashboard.spc.service import compute_spc
    from c_dashboard.spc.sources import profile_for_dataset
    from c_dashboard.spc.types import SourceContext
    pure=compute_spc(selected_rows(w),SourceContext(w.data.source_id,profile_for_dataset(w.data.dataset)),base,
                     analysis_scope_id=r.scope_id)
    assert [g.mean for g in pure.targets[0].groups]==[g.mean for g in r.targets[0].groups]
    assert set(e.event_id for e in pure.events)==set(ids)
    w.what_if.parameters={'line_speed_m_min':1.8}
    assert analyze_workspace(w)==r
    operate(w,'restart',0)
    assert not analyze_workspace(w).events and analyze_workspace(w).baseline==base
    pd.testing.assert_frame_equal(original,w.data.dataset.frame)


def test_spc_incomplete_target_cannot_borrow_future_values_or_baseline():
    from c_dashboard.spc.service import compute_spc
    from c_dashboard.spc.sources import load_c_profile
    from c_dashboard.spc.types import SourceContext
    w=delayed_workspace()
    calibration=WorkspaceState();commit_dataset(calibration,load_mock_fixture('normal'))
    base=analyze_workspace(calibration).baseline
    snapshot=through(w,'2026-11-01T08:00:04+08:00')
    context=SourceContext('C7 pure projection test',load_c_profile())
    peel=compute_spc(snapshot.measurements['peel_strength_n_mm'],context,base)
    heat=compute_spc(snapshot.measurements['heat_resistance_c'],context,base)
    assert any(g.valid for g in peel.target('peel_strength_n_mm').groups)
    assert not any(g.valid for g in heat.target('heat_resistance_c').groups)
    assert not heat.events
    assert all(t.status=='無法判定 SPC 狀態' for t in heat.targets)


def test_multi_group_timer_preserves_all_intermediate_spc_events():
    from c_dashboard.replay.service import tick
    a=WorkspaceState();b=WorkspaceState()
    for w in (a,b):commit_dataset(w,load_mock_fixture('trend'));set_mode(w,'replay')
    for _ in range(10):operate(a,'step',0);analyze_workspace(a)
    operate(b,'play',0);tick(b.replay,timeline_for(b),9*60+.1,b.replay.generation)
    result=analyze_workspace(b)
    assert {(e.target,e.rule,e.subgroup) for e in result.events}=={(e.target,e.rule,e.subgroup) for e in a.spc.result.events}
    assert len(result.events)==len({e.event_id for e in result.events})
