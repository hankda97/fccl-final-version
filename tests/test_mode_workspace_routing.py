from dataclasses import replace
from unittest.mock import patch
import pandas as pd

from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.data.session import commit_dataset, selected_rows, set_filters
from c_dashboard.quality.controller import ensure_what_if_selection, evaluate_what_if, monitor_prediction
from c_dashboard.replay.controller import operate, snapshot_for, timeline_for
from c_dashboard.replay.service import tick
from c_dashboard.spc.controller import analyze_workspace
from c_dashboard.visualization.controller import heatmap_for
from c_dashboard.workspace_modes.state import ensure_registry, bind_context
from c_dashboard.workspace_modes.controller import switch_mode, request_token, accept_response, reset_run
from c7_support import delayed_workspace, through


def test_epoch_rejects_late_success_error_and_wrong_mode_run_source():
    r=ensure_registry({}); a=r.workspaces['analysis']
    before=request_token(a,'job')
    switch_mode(r,'testline');switch_mode(r,'analysis')
    for error in (None,ValueError('late')):
        assert not accept_response(r,'analysis',before,'job',error=error)
    current=request_token(a,'job')
    assert accept_response(r,'analysis',current,'job')
    assert not accept_response(r,'production',current,'job')
    commit_dataset(a,load_mock_fixture('normal'))
    assert not accept_response(r,'analysis',current,'job')
    c=request_token(a,'job');reset_run(r,'analysis')
    assert not accept_response(r,'analysis',c,'job')


def test_navigation_preserves_real_c7_fixed_selection_baseline_and_cache():
    original=delayed_workspace();r=ensure_registry({'fccl_workspace':original});a=original
    through(a,'2026-11-01T08:00:03+08:00')
    rows=selected_rows(a);ensure_what_if_selection(a,rows)
    adapter=DeterministicMockAdapter()
    evaluate_what_if(a,adapter);monitor_prediction(a,rows,adapter)
    baseline=analyze_workspace(a).baseline
    heatmap_for(a,rows)
    cursor=a.replay.cursor;fixed=a.what_if.selected;comparison=a.what_if.comparison
    count=a.visualization.heatmap.computations;result=a.visualization.heatmap.result
    operate(a,'play',10);old=a.replay.lifecycle_token;generation=a.replay.generation
    switch_mode(r,'testline');switch_mode(r,'analysis')
    assert not a.replay.playing and a.replay.cursor == cursor
    assert not tick(a.replay,timeline_for(a),20,generation,lifecycle_token=old)
    assert a.what_if.selected == fixed and a.what_if.comparison is comparison
    heatmap_for(a,rows);assert a.visualization.heatmap.computations==count
    assert a.visualization.heatmap.result is result
    with patch('c_dashboard.spc.controller.build_baseline',side_effect=AssertionError('recalibration')):
        assert analyze_workspace(a).baseline is baseline
    b=r.workspaces['testline'];b.mode_context.run_id='b-run'
    b.replay.cursor=8; b.what_if.parameters['line_speed_m_min']=2
    operate(a,'restart',30)
    assert a.replay.cursor==0 and a.what_if.requires_reselect
    assert b.replay.cursor==8 and b.what_if.parameters['line_speed_m_min']==2
    assert a.spc.baseline is baseline
    through(a,'2026-11-01T08:00:03+08:00')
    ensure_what_if_selection(a,selected_rows(a)); assert a.what_if.requires_reselect


def test_source_replacement_and_filter_rebind_lifecycle_and_isolate_modes():
    r=ensure_registry({});a=r.workspaces['analysis'];b=r.workspaces['testline']
    switch_mode(r,'testline');switch_mode(r,'analysis')
    epoch=a.mode_context.activation_epoch
    commit_dataset(a,load_mock_fixture('normal'))
    assert a.replay.lifecycle_token.endswith(f':{epoch}')
    generation=a.replay.generation
    set_filters(a,'M-B01',None,None)
    assert a.replay.generation>generation
    assert a.replay.lifecycle_token.endswith(f':{epoch}')
    assert b.data.dataset is None and b.replay.cursor==0


def test_inflight_prediction_and_whatif_discard_after_navigation():
    r=ensure_registry({});a=r.workspaces['analysis'];commit_dataset(a,load_mock_fixture('normal'))
    rows=selected_rows(a);ensure_what_if_selection(a,rows)
    class SwitchingAdapter(DeterministicMockAdapter):
        def predict(self,samples):
            result=super().predict(samples)
            switch_mode(r,'testline');switch_mode(r,'analysis')
            return result
    assert monitor_prediction(a,rows,SwitchingAdapter()) is None
    comparison,_=evaluate_what_if(a,SwitchingAdapter())
    assert comparison is None and a.what_if.comparison is None


def test_inflight_chart_success_and_error_rejected_after_navigation(monkeypatch):
    r=ensure_registry({});a=r.workspaces['analysis'];commit_dataset(a,load_mock_fixture('normal'))
    from c_dashboard.visualization.heatmap import compute_heatmap as real
    for fail in (False,True):
        def switched(*args,**kwargs):
            value=real(*args,**kwargs)
            switch_mode(r,'testline');switch_mode(r,'analysis')
            if fail:raise ValueError('late')
            return value
        monkeypatch.setattr('c_dashboard.visualization.controller.compute_heatmap',switched)
        slot=heatmap_for(a,selected_rows(a),retry=True)
        assert slot.result is None and slot.status=='stale'


def test_child_spc_does_not_load_A_history_and_explicit_own_baseline(monkeypatch):
    r=ensure_registry({});b=r.workspaces['testline'];commit_dataset(b,load_mock_fixture('normal'))
    monkeypatch.setattr('c_dashboard.spc.controller.load_spc_history',lambda:(_ for _ in ()).throw(AssertionError('borrowed')))
    result=analyze_workspace(b)
    assert result.baseline is None
    assert all(t.status!='正常' for t in result.targets)
    from c3_support import hand_history
    from c_dashboard.spc.baseline import build_baseline
    frame,profile=hand_history()
    b.mode_context.spc_profile=profile
    b.spc.baseline=build_baseline(frame,profile,history_hash='independent-test')
    assert analyze_workspace(b).baseline is b.spc.baseline


def test_content_changes_invalidate_only_local_chart_and_versions():
    r=ensure_registry({});a,b,c=r.workspaces.values()
    for w in (a,b,c):commit_dataset(w,load_mock_fixture('normal'));heatmap_for(w,selected_rows(w))
    assert len({w.visualization.heatmap.request_key for w in (a,b,c)})==3
    count=a.visualization.heatmap.computations
    key=b.visualization.heatmap.request_key
    b.mode_context.simulator_version='v2';heatmap_for(b,selected_rows(b))
    assert b.visualization.heatmap.request_key!=key
    assert a.visualization.heatmap.computations==count
