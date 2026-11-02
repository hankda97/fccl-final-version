from copy import deepcopy
import pytest

from c_dashboard.state import WorkspaceState, WORKSPACE_KEY
from c_dashboard.workspace_modes.state import ensure_registry, REGISTRY_KEY, widget_key, save_preferences, restore_preferences
from c_dashboard.workspace_modes.controller import switch_mode, reset_run, record_event, current_events
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.data.session import commit_dataset, set_filters, attempt_upload
from c_dashboard.quality.controller import ensure_what_if_selection, evaluate_what_if, monitor_prediction
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.data.session import selected_rows


def registry():
    return ensure_registry({})


def populate(w, fixture="normal"):
    commit_dataset(w, load_mock_fixture(fixture))
    ensure_what_if_selection(w, selected_rows(w))
    return w


def test_deep_independence_and_cross_session_same_ids():
    r = registry(); other = registry()
    a, b, c = r.workspaces.values()
    for w in (a, b, c):
        populate(w)
    for name in ("data", "replay", "what_if", "model", "spc", "visualization", "mode_context"):
        assert len({id(getattr(w, name)) for w in (a,b,c)}) == 3
    a_before, c_before = deepcopy(a), deepcopy(c)
    b.what_if.parameters["line_speed_m_min"] = 1.2
    b.what_if.advanced_unlocked = True
    b.visualization.heatmap.reason = "B only"
    assert a.what_if == a_before.what_if and c.what_if == c_before.what_if
    assert a.data.source_id == b.data.source_id == c.data.source_id
    assert a.visualization == a_before.visualization and c.visualization == c_before.visualization
    assert other.workspaces["analysis"].data.dataset is None
    assert widget_key(a, "x") == "x"
    assert widget_key(b, "x") != widget_key(c, "x")


def test_existing_session_alias_no_copy_reinitialization_and_unknown_version():
    original = populate(WorkspaceState())
    original.replay.cursor = 4
    original.data.temporal_config = {"version":"existing"}
    original.what_if.parameters["line_speed_m_min"] = 1.2
    session = {WORKSPACE_KEY: original}
    r = ensure_registry(session)
    assert r.workspaces["analysis"] is original
    before = original.what_if
    switch_mode(r,"testline")
    assert ensure_registry(session) is r and session[WORKSPACE_KEY] is original
    assert original.what_if is before and original.replay.cursor == 4
    assert original.data.temporal_config == {"version":"existing"}
    assert not r.workspaces["testline"].data.dataset
    r.version = "unknown"
    with pytest.raises(ValueError, match="REGISTRY_VERSION"):
        ensure_registry(session)
    assert session[REGISTRY_KEY] is r and session[WORKSPACE_KEY] is original


def test_local_source_filter_failure_and_run_reset_keep_history():
    r=registry(); a=populate(r.workspaces["analysis"]); b=populate(r.workspaces["testline"])
    a_cursor=a.replay.cursor; fixed=a.what_if.selected
    source=b.data.source_id
    assert not commit_dataset(b, attempt_upload(b"", "empty.csv"))
    assert b.data.source_id == source
    set_filters(b,"M-B01",None,None)
    assert a.what_if.selected == fixed and a.replay.cursor == a_cursor
    for mode in ("testline","production"):
        r.workspaces[mode].mode_context.run_id="same-run"
        for typ in ("spc","ai","signal"):
            record_event(r,mode,"source",typ,"same-id",typ)
            record_event(r,mode,"source",typ,"same-id",typ)
    assert current_events(r,"testline") == ("spc","ai","signal")
    assert current_events(r,"production") == ("spc","ai","signal")
    reset_run(r,"testline","new-run")
    assert len(r.events["testline"])==3 and not current_events(r,"testline")
    assert len(current_events(r,"production"))==3
    assert a.what_if.selected == fixed and a.data.source_id == source
    assert switch_mode(r,"unknown").code == "UNKNOWN_MODE"
    assert r.active_mode == "analysis"


def test_durable_preferences_exclude_upload_and_buttons():
    r=registry(); session={"ui_source_choice":"上傳 CSV","ui_mapping_json":"custom",
        "ui_workspace_tabs":"AI 圖表","ui_csv_upload":object(),"ui_load_mock":True}
    save_preferences(r,session);session.clear();restore_preferences(r,session)
    assert session == {"ui_source_choice":"上傳 CSV","ui_mapping_json":"custom","ui_workspace_tabs":"AI 圖表"}
    switch_mode(r,"testline"); restore_preferences(r,{})
    assert not r.preferences["testline"].values


def test_shared_prediction_whatif_services_do_not_write_history_or_emit_events():
    r=registry(); adapter=DeterministicMockAdapter()
    for mode in ("testline","production"):
        w=populate(r.workspaces[mode]); original=w.data.dataset.frame.copy(deep=True)
        fixed=w.what_if.selected
        speed=dict(fixed.process_settings)["line_speed_m_min"]
        w.what_if.parameters["line_speed_m_min"]=speed-.2
        before, recommendation=evaluate_what_if(w,adapter)
        assert len(before.after.targets)==5
        assert before.before != before.after
        assert w.what_if.selected == fixed
        assert original.equals(w.data.dataset.frame)
        assert not current_events(r,mode)
        monitor_prediction(w,selected_rows(w),adapter)
    assert r.workspaces["analysis"].data.dataset is None
    assert r.workspaces["testline"].what_if.result_key != r.workspaces["production"].what_if.result_key
    assert r.workspaces["testline"].model.current_prediction_key != r.workspaces["production"].model.current_prediction_key
