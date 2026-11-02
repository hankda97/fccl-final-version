from dataclasses import replace

import pandas as pd

from c_dashboard.data.fixtures import load_mock_fixture, load_spc_history
from c_dashboard.spc.baseline import build_baseline
from c_dashboard.spc.config import RuleConfig
from c_dashboard.spc.service import compute_spc
from c_dashboard.spc.sources import load_c_profile
from c_dashboard.spc.types import SourceContext
from c3_support import HEAT, MD, PEEL, hand_history, monitoring


def setup(means, target=PEEL):
    history, p = hand_history()
    rows, _ = monitoring(means, target)
    return rows, SourceContext("test-source",p), build_baseline(history,p)


def test_fixed_baseline_filtering_drift_and_latest_invalid_keep_history_distinct():
    rows,c,b = setup([1.25, .5, 1.25])
    first = compute_spc(rows,c,b)
    filtered = compute_spc(rows.iloc[5:],c,b)
    assert filtered.baseline is b and first.baseline is b
    assert filtered.baseline.version == first.baseline.version
    assert first.target(PEEL).baseline == filtered.target(PEEL).baseline
    assert any(e.subgroup=="G1" for e in first.events)
    rows.loc[10,PEEL]=float("nan")
    last = compute_spc(rows,c,b)
    assert last.target(PEEL).latest.mean is None
    assert last.target(PEEL).status == "無法判定 SPC 狀態"
    assert last.events and all(e.subgroup != "G2" for e in last.events)
    assert compute_spc(rows.iloc[10:],c,b).events == ()


def test_same_input_dedup_all_targets_and_meaningful_event_payload():
    rows,c,b = setup([-.05]*9,MD)
    a = compute_spc(rows,c,b)
    assert a == compute_spc(rows.copy(deep=True),c,b)
    ids=[e.event_id for e in a.events]
    assert len(ids)==len(set(ids))
    assert any(e.target==MD for e in a.events)
    event=a.events[-1]
    assert event.source_id==c.source_id and event.scope_id==a.scope_id
    assert event.source_rows and event.sequence and event.triggered_at==a.target(MD).groups[-1].completed_at


def test_unknown_source_partial_quality_empty_and_missing_baseline_are_local():
    data=load_mock_fixture("partial_quality");p=load_c_profile()
    h=load_spc_history();b=build_baseline(h.frame,p,history_hash=p.history_hash)
    r=compute_spc(data.frame,SourceContext(data.source_id,p),b)
    assert not r.target(HEAT).latest.valid and r.target(PEEL).latest.valid
    assert r.target(PEEL).baseline.valid
    unknown=compute_spc(data.frame,SourceContext("upload"),None)
    assert not unknown.events and unknown.raw
    assert "MISSING_SAMPLING_EVIDENCE" in unknown.target(PEEL).reasons
    empty=compute_spc(data.frame.iloc[:0],SourceContext("test",p),b)
    assert not empty.events and empty.cutoff is None
    assert not compute_spc(data.frame,SourceContext("test",p),None).events


def test_bounded_prefix_no_lookahead_or_input_mutation_and_no_filter_warmup():
    rows,c,b=setup([1.20,1.21,1.22,1.23,1.24,1.25,1.26])
    original=rows.copy(deep=True)
    prefix=rows.iloc[:25].copy()
    expected=compute_spc(prefix,c,b)
    rows.loc[25:,PEEL]=99
    assert compute_spc(prefix,c,b)==expected
    pd.testing.assert_frame_equal(prefix,original.iloc[:25])
    assert not any(e.rule.startswith("TREND") for e in expected.events)
    assert any(e.rule=="TREND_UP_6" for e in compute_spc(original,c,b).events)
    assert not any(e.rule.startswith("TREND") for e in compute_spc(original.iloc[5:30],c,b).events)
    assert not compute_spc(original.iloc[:3],c,b).target(PEEL).latest.valid


def test_profile_mismatch_overlap_and_rule_version_never_use_valid_lines():
    rows,c,b=setup([.5])
    assert not compute_spc(rows,replace(c,profile=replace(c.profile,version="other")),b).target(PEEL).baseline.valid
    assert not compute_spc(rows,c,b,RuleConfig("other")).events
    rows.loc[0,"product_batch"],rows.loc[0,"specimen_id"]=b.natural_samples[0]
    r=compute_spc(rows,c,b)
    assert "HISTORY_SAMPLE_OVERLAP" in r.target(PEEL).reasons
    assert not r.events


def test_explicit_slice_before_monitoring_origin_cannot_use_future_calibration():
    rows,c,b=setup([.5,1.25])
    rows["timestamp"]-=pd.Timedelta(days=2)
    rows["available_at"]-=pd.Timedelta(days=2)
    r=compute_spc(rows,c,b)
    assert not r.events
    assert all(t.status=="無法判定 SPC 狀態" for t in r.targets)
    assert "MONITORING_BEFORE_ORIGIN" in r.target(PEEL).reasons
