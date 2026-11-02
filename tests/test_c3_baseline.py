from dataclasses import FrozenInstanceError, replace

import pandas as pd
import pytest

from c_dashboard.data.fixtures import load_mock_fixture, load_spc_history
from c_dashboard.spc.baseline import build_baseline, natural_samples
from c_dashboard.spc.sources import load_c_profile
from c3_support import HEAT, MD, PEEL, hand_history, monitoring


@pytest.mark.parametrize("n,expected", [(5, (1.25, .04, 1.27308, 1.22692)), (3, (1.25, .02, 1.27046, 1.22954))])
def test_manual_limits_and_negative_dimension_are_not_clipped(n, expected):
    rows, p = hand_history(n)
    baseline = build_baseline(rows, p)
    result = baseline.target(PEEL)
    assert result.valid and (result.cl, result.r_bar, result.ucl, result.lcl) == pytest.approx(expected)
    assert baseline.target(MD).ucl < 0 and baseline.target(MD).lcl < 0
    assert baseline.target(MD).valid


@pytest.mark.parametrize("fault,code", [
    ("few", "INSUFFICIENT_HISTORY_GROUPS"), ("late", "HISTORY_NOT_PRIOR"),
    ("bad_group", "INVALID_HISTORY_GROUP"), ("product", "INVALID_HISTORY_GROUP"),
    ("condition", "INVALID_HISTORY_GROUP"), ("unit", "UNIT_MISMATCH"),
    ("unsupported_n", "UNSUPPORTED_SUBGROUP_SIZE"), ("constant", "ZERO_HISTORY_VARIATION"),
])
def test_bad_history_is_rejected_without_selecting_clean_subset(fault, code):
    rows, p = hand_history()
    if fault == "few": rows = rows.iloc[:-5]
    elif fault == "late": rows["available_at"] += pd.Timedelta(days=2)
    elif fault == "bad_group": rows.loc[0, PEEL] = float("nan")
    elif fault == "product": rows.loc[0, "product_id"] = "other"
    elif fault == "condition": rows.loc[0, "curing_temp_c"] = 180
    elif fault == "unit": p = replace(p, units=())
    elif fault == "unsupported_n": p = replace(p, n=11)
    elif fault == "constant": rows[PEEL] = 1.25
    result = build_baseline(rows, p).target(PEEL)
    assert not result.valid and code in result.reasons
    assert result.cl is None and result.ucl is None and result.lcl is None


def test_overlap_hash_and_single_target_rejection():
    rows, p = hand_history()
    assert "HISTORY_SAMPLE_OVERLAP" in build_baseline(rows, p, monitor_samples=natural_samples(rows)).target(PEEL).reasons
    rows.loc[0, HEAT] = float("nan")
    b = build_baseline(rows, p)
    assert b.target(PEEL).valid and not b.target(HEAT).valid
    history = load_spc_history()
    p = load_c_profile()
    assert not build_baseline(history.frame, p, history_hash="renamed-content").target(PEEL).valid
    assert build_baseline(history.frame, p, history_hash=p.history_hash).target(PEEL).valid


def test_one_target_unit_mismatch_only_disables_that_target():
    rows,p=hand_history()
    p=replace(p,units=tuple((name,"wrong" if name==HEAT else unit) for name,unit in p.units))
    b=build_baseline(rows,p)
    assert b.target(PEEL).valid and b.target(MD).valid
    assert not b.target(HEAT).valid and "UNIT_MISMATCH" in b.target(HEAT).reasons


@pytest.mark.parametrize("fault", ["outlier", "trend", "side", "range"])
def test_historical_stability_refuses_mean_and_range_signals(fault):
    rows, p = hand_history()
    if fault == "outlier": rows.loc[rows.subgroup_id == "G10", PEEL] += .5
    elif fault == "trend":
        for i in range(6): rows.loc[rows.subgroup_id == f"G{i}", PEEL] += (i-2.5)*.001
    elif fault == "side":
        for i in range(9): rows.loc[rows.subgroup_id == f"G{i}", PEEL] += .001
    else: rows.loc[rows.subgroup_id == "G10", PEEL] = [1.05, 1.15, 1.25, 1.35, 1.45]
    result = build_baseline(rows, p).target(PEEL)
    assert not result.valid
    prefix = "UNSTABLE_HISTORY_RANGE" if fault == "range" else "UNSTABLE_HISTORY_MEAN"
    assert any(reason.startswith(prefix) for reason in result.reasons)


def test_fixed_calibration_does_not_depend_on_monitoring_and_new_configuration_versions_it():
    rows, p = hand_history()
    b = build_baseline(rows, p)
    original = (b.version, b.target(PEEL).cl, b.target(PEEL).ucl, b.target(PEEL).lcl)
    view, _ = monitoring([1.25, .5, 4.0])
    view = view.iloc[5:]
    assert original == (b.version, b.target(PEEL).cl, b.target(PEEL).ucl, b.target(PEEL).lcl)
    assert build_baseline(rows, p) == b
    assert build_baseline(rows, replace(p, version="other-version")).version != b.version
    changed = rows.copy()
    changed.loc[0, PEEL] += .0001
    assert build_baseline(changed, p).version != b.version
    with pytest.raises(FrozenInstanceError): b.version = "overwritten"
