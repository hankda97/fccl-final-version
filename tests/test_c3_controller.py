from dataclasses import replace

from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.data.session import attempt_upload, commit_dataset, set_filters
from c_dashboard.spc.controller import analyze_workspace
from c_dashboard.state import ensure_workspace
from c3_support import PEEL


def loaded(name="normal"):
    w = ensure_workspace({})
    commit_dataset(w, load_mock_fixture(name))
    return w


def test_single_analysis_object_rerun_filters_invalid_upload_and_new_source():
    w=loaded("out_of_control")
    a=analyze_workspace(w)
    assert a.events and a is analyze_workspace(w)
    baseline=a.baseline
    assert not commit_dataset(w,attempt_upload(b"", "empty.csv"))
    assert analyze_workspace(w) is a
    set_filters(w,"M-B02",None,None)
    assert w.spc.result is None
    b=analyze_workspace(w)
    assert b.baseline is baseline and not b.events
    assert a.scope_id != b.scope_id
    set_filters(w,"M-B02",None,None)
    assert analyze_workspace(w) is b
    commit_dataset(w,load_mock_fixture("partial_quality"))
    assert w.spc.result is None
    assert analyze_workspace(w).source_id != a.source_id


def test_session_and_what_if_values_do_not_mutate_measured_result():
    a,b=loaded(),loaded()
    first=analyze_workspace(a)
    a.what_if.parameters["line_speed_m_min"]=.1
    a.what_if.advanced_unlocked=True
    a.replay.cursor=5  # Only a state seam, no replay implemented.
    assert analyze_workspace(a) is first
    assert b.spc.result is None
    assert analyze_workspace(b)==first
    assert b.spc is not a.spc


def test_unknown_upload_does_not_inherit_previous_mock_baseline():
    w=loaded()
    known=analyze_workspace(w)
    assert known.target(PEEL).baseline.valid
    data=load_mock_fixture("normal")
    commit_dataset(w,attempt_upload(data.content,"uploaded.csv"))
    result=analyze_workspace(w)
    assert result.baseline is None and not result.events
    assert "MISSING_SAMPLING_EVIDENCE" in result.target(PEEL).reasons


def test_missing_history_resource_degrades_without_losing_preview(monkeypatch):
    w=loaded()
    def fail(): raise OSError("test-only missing history")
    monkeypatch.setattr("c_dashboard.spc.controller.load_spc_history",fail)
    result=analyze_workspace(w)
    assert result.baseline is None and not result.events
    assert any("SPC_RESOURCE_UNAVAILABLE" in x for x in result.target(PEEL).reasons)
    assert len(w.data.dataset.frame)==150
