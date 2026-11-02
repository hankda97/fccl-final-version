import copy
from io import StringIO
import pandas as pd
import pytest
from c_dashboard.data.loader import load_csv
from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS
from c_dashboard.replay.temporal import build_timeline
from c_dashboard.replay.controller import timeline_for, snapshot_for
from c7_support import delayed_workspace, through, FIXTURES, CONFIG


def edited(**columns):
    f = pd.read_csv(FIXTURES / "delayed.csv")
    for k, v in columns.items():
        f[k] = v
    return f.to_csv(index=False).encode()


def test_declared_atomic_timeline_identity_units_and_no_mutation():
    w = delayed_workspace()
    original = w.data.dataset.frame.copy(deep=True)
    t = timeline_for(w)
    assert len(t.groups) == 9
    assert len(t.groups[0]) == 5  # Identity only; no future features or labels.
    assert all(len({e.available_at for e in g}) == 1 for g in t.groups)
    assert t == timeline_for(w)
    assert not t.reasons
    s = snapshot_for(w)
    assert s.rows.empty and s.raw.empty and s.played_rows == 0
    s = through(w, "2026-11-01T08:00:01+08:00")
    assert s.played_rows == 5 and s.total_rows == 15
    assert s.rows[list(FEATURE_UNITS)].notna().all().all()
    assert s.rows[list(TARGET_UNITS)].isna().all().all()
    pd.testing.assert_frame_equal(w.data.dataset.frame, original)


def test_targets_released_separately_with_measurement_and_publication_times():
    w = delayed_workspace()
    s = through(w, "2026-11-01T08:00:04+08:00")
    first = s.rows[s.rows.source_row <= 6]
    assert first.peel_strength_n_mm.notna().all() and first.heat_resistance_c.isna().all()
    v = s.measurements["peel_strength_n_mm"]
    assert v.iloc[0].timestamp == pd.Timestamp("2026-11-01T08:00:00+08:00")
    assert v.iloc[0].available_at == pd.Timestamp("2026-11-01T08:00:04+08:00")
    assert s.played_rows == 15
    s = through(w, "2026-11-01T08:00:10+08:00")
    assert s.rows[list(TARGET_UNITS)].notna().all().all()
    assert s.played_rows == 15  # Multiple target releases never add source rows.


@pytest.mark.parametrize('column,value', [
    ('quality_available_at',''), ('quality_available_at','bad'),
    ('quality_available_at','2026-11-01T07:59:59+08:00'),
    ('sampled_at','2026-11-01T08:00:00'), ('target_flag',0), ('is_retest',1),
    ('peel_label_available',0), ('quality_label_available',0), ('label_scope','roll'),
])
def test_unreliable_channel_does_not_disable_valid_process(column, value):
    w = delayed_workspace(edited(**{column:value}))
    t = timeline_for(w)
    assert t.groups and t.reasons
    s = through(w, "2026-11-01T08:01:00+08:00")
    assert s.rows.line_speed_m_min.notna().all()
    assert s.rows.peel_strength_n_mm.isna().all()


@pytest.mark.parametrize('bad', ['bad', '', '2026-11-01T08:00:00'])
def test_identity_time_failure_no_fake_release(bad):
    w = delayed_workspace(edited(process_completed_at=bad))
    assert not timeline_for(w).groups
    assert snapshot_for(w).rows.empty


def test_loader_fallback_is_not_formal_release_and_snapshot_is_still_accepted():
    raw = pd.read_csv(FIXTURES / 'delayed.csv').drop(columns='available_at').to_csv(index=False).encode()
    d = load_csv(raw, 'upload.csv')
    assert d.accepted and any(i.code=='AVAILABILITY_ASSUMED' for i in d.issues)
    t = build_timeline(d, d.frame, CONFIG)
    assert not t.groups and t.reasons
    t = build_timeline(d, d.frame)
    assert not t.groups and t.profile is None


def test_per_target_availability_conflict_and_md_trace():
    w = delayed_workspace(edited(peel_label_available=0, root_roll_id='C7-ROLL',
                                material_md_start_m=0, material_md_end_m=5))
    s = through(w, '2026-11-01T08:01:00+08:00')
    assert s.rows.peel_strength_n_mm.isna().all()
    assert s.rows.heat_resistance_c.notna().all()
    assert set(s.rows.root_roll_id)=={'C7-ROLL'}


def test_appearance_conflict_does_not_poison_continuous_targets():
    w = delayed_workspace(edited(appearance_ng_flag=1, appearance_spec_pass_flag=1))
    s = through(w, '2026-11-01T08:01:00+08:00')
    assert s.rows.appearance_ng.isna().all() and s.rows.peel_strength_n_mm.notna().all()


def test_no_future_values_or_raw_fields_and_no_feature_imputation():
    a = delayed_workspace()
    b = delayed_workspace(edited(peel_strength_n_mm=999, heat_resistance_c=999, target_flag=0))
    for w in (a,b):
        s=through(w,'2026-11-01T08:00:01+08:00')
        assert s.raw.quality_available_at.isna().all()
        assert s.raw.target_flag.isna().all()
        assert s.rows[list(TARGET_UNITS)].isna().all().all()
    pd.testing.assert_frame_equal(snapshot_for(a).rows.drop(columns='sample_id'),
                                  snapshot_for(b).rows.drop(columns='sample_id'))


def test_canonical_source_metadata_does_not_imply_replay_time():
    d=load_csv((FIXTURES/'delayed.csv').read_bytes(),'formal.csv')
    assert not build_timeline(d,d.frame).groups
    invalid=copy.deepcopy(CONFIG);invalid['identity']['available_at']='completed_at'
    assert not build_timeline(d,d.frame,invalid).groups


def test_explicit_timezone_mapping_and_unconfirmed_retest_history():
    raw=edited(sampled_at='2026-11-01T08:00:00',is_retest=1)
    w=delayed_workspace(raw)
    config=copy.deepcopy(CONFIG);config['timezone']='Asia/Taipei';config['revision_evidence']=True
    from c_dashboard.replay.controller import set_temporal_config
    set_temporal_config(w,config)
    assert through(w,'2026-11-01T08:01:00+08:00').rows.peel_strength_n_mm.notna().all()


def test_future_duplicate_specimen_does_not_invalidate_earlier_visible_identity():
    raw=pd.read_csv(FIXTURES/'delayed.csv')
    raw.loc[5,'specimen_id']=raw.loc[0,'specimen_id']
    w=delayed_workspace(raw.to_csv(index=False).encode())
    assert w.data.dataset.frame.duplicate_record.sum()==2  # Snapshot's original validation is untouched.
    early=through(w,'2026-11-01T08:00:01+08:00')
    assert early.rows.identity_valid.all() and not early.rows.duplicate_record.any()
    later=through(w,'2026-11-01T08:00:02+08:00')
    assert later.rows.duplicate_record.sum()==2
    assert not later.rows.loc[later.rows.duplicate_record,'identity_valid'].any()
