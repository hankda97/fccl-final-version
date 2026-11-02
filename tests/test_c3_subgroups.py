from dataclasses import replace

import pandas as pd
import pytest

from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.spc.sources import load_c_profile
from c_dashboard.spc.subgroups import build_subgroups
from c_dashboard.spc.subgroups import group_inputs
from c_dashboard.data.loader import input_eligibility
from c3_support import HEAT, PEEL, monitoring


@pytest.mark.parametrize("n", [3, 5])
def test_complete_independent_groups_have_expected_mean_range_and_adjacency(n):
    rows, profile = monitoring([1.25, 1.26], n=n)
    groups = build_subgroups(rows, profile, PEEL)
    assert len(groups) == 2 and all(g.valid and g.n == n for g in groups)
    assert groups[0].mean == pytest.approx(1.25)
    assert groups[0].span == pytest.approx((n-1)*.001)
    assert groups[0].break_before and not groups[1].break_before


@pytest.mark.parametrize("fault", ["few", "extra", "duplicate", "condition", "batch", "time", "segment", "product", "recipe", "identity"])
def test_bad_rows_are_not_dropped_to_manufacture_complete_group(fault):
    rows, profile = monitoring([1.25])
    if fault == "few": rows = rows.iloc[:-1]
    elif fault == "extra": rows = pd.concat([rows, rows.iloc[:1]])
    elif fault == "duplicate": rows.loc[1, "specimen_id"] = rows.loc[0, "specimen_id"]
    elif fault == "condition": rows.loc[1, "line_speed_m_min"] = 9
    elif fault == "batch": rows.loc[1, "product_batch"] = "other"
    elif fault == "time": rows.loc[1, "timestamp"] += pd.Timedelta(seconds=1)
    elif fault == "segment": rows.loc[1, "segment_id"] = "other"
    elif fault == "product": rows.loc[1, "product_id"] = "other"
    elif fault == "recipe": rows.loc[1, "recipe_id"] = "other"
    elif fault == "identity": rows.loc[1, "identity_valid"] = False
    groups = build_subgroups(rows, profile, PEEL)
    assert groups and not any(g.valid for g in groups)
    assert sum(g.n for g in groups) == len(rows)


def test_target_missingness_is_local_and_invalid_group_is_a_barrier():
    rows, p = monitoring([1.25]*4)
    rows.loc[5, HEAT] = float("nan")
    heat = build_subgroups(rows, p, HEAT)
    peel = build_subgroups(rows, p, PEEL)
    assert all(g.valid for g in peel)
    assert not heat[1].valid and heat[2].break_before
    assert heat[-1].valid and not heat[-1].break_before
    with pytest.raises(ValueError): build_subgroups(rows, p, "appearance_ng")


def test_missing_whole_group_unknown_order_batch_and_interval_reset_continuity():
    rows, p = monitoring([1.25]*5)
    rows = rows[rows.subgroup_id != "G1"]
    groups = build_subgroups(rows, p, PEEL)
    assert groups[1].subgroup == "G2" and groups[1].break_before
    assert all(g.break_before for g in build_subgroups(rows, replace(p, interval_seconds=None), PEEL))
    rows.loc[rows.subgroup_id == "G3", "product_batch"] = "NEW"
    assert all(g.break_before for g in build_subgroups(rows, p, PEEL))


def test_registered_missing_profile_columns_and_partial_prefix_never_get_filled():
    data = load_mock_fixture("ungrouped")
    assert not any(g.valid for g in build_subgroups(data.frame, load_c_profile(), PEEL))
    rows, p = monitoring([1.25, 1.26])
    groups = build_subgroups(rows.iloc[:7], p, PEEL)
    assert groups[0].valid and not groups[1].valid and groups[1].n == 2
    assert not any(g.valid for g in build_subgroups(rows, replace(p, independent_specimens=False), PEEL))


def test_loadable_features_do_not_imply_spc_and_partial_targets_keep_preview():
    data = load_mock_fixture("normal")
    assert input_eligibility(data.frame)["prediction_input_rows"] == 150
    assert group_inputs(data.frame, None, PEEL) == ((), ("MISSING_SAMPLING_EVIDENCE",))
    for scenario in ("partial_quality", "no_quality", "ungrouped"):
        data = load_mock_fixture(scenario)
        before = data.frame.copy(deep=True)
        groups, reasons = group_inputs(data.frame, load_c_profile(), HEAT)
        assert not any(g.valid for g in groups)
        assert "NO_COMPLETE_TARGET_GROUP" in reasons
        pd.testing.assert_frame_equal(data.frame, before)
        assert input_eligibility(data.frame)["view_rows"] == 150


def test_same_specimen_reused_in_different_groups_is_not_independent_sampling():
    rows,p=monitoring([1.25,1.26,1.27])
    rows.loc[5,"specimen_id"]=rows.loc[0,"specimen_id"]
    groups=build_subgroups(rows,p,PEEL)
    assert not groups[0].valid and not groups[1].valid
    assert "REUSED_SPECIMEN_IN_SOURCE" in groups[0].reasons
    assert groups[2].valid and groups[2].break_before
