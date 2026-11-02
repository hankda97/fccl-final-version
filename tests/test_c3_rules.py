from dataclasses import replace

import pytest

from c_dashboard.spc.rules import detect_signals
from c_dashboard.spc.types import GroupPoint, TargetBaseline
from c3_support import PEEL

BASE = TargetBaseline(PEEL, "N/mm", 0, 10, -10, 1, 25)


def points(values):
    return tuple(GroupPoint(PEEL, "B", str(i), "S", None, "T", 5, (x,), x, 1, (), (i+2,), (), i==0)
                 for i, x in enumerate(values))


def rules(values, baseline=BASE):
    return detect_signals(points(values), baseline)


@pytest.mark.parametrize("values,rule", [(list(range(1,8)), "TREND_UP_6"), (list(range(7,0,-1)), "TREND_DOWN_6")])
def test_trend_first_fires_at_sixth_and_overlapping_window_is_not_duplicated(values, rule):
    selected = [i for i,r,s in rules(values) if r==rule]
    assert selected == [5,6]
    assert len(rules(values[:5])) == 0


@pytest.mark.parametrize("value,rule", [(1,"ABOVE_CL_9"),(-1,"BELOW_CL_9")])
def test_side_first_fires_at_ninth_and_equal_values_still_count(value, rule):
    assert rules([value]*8) == ()
    assert [i for i,r,s in rules([value]*10) if r==rule] == [8,9]
    assert not any(r==rule for _,r,_ in rules([value]*8+[0]+[value]*8))


def test_limit_equality_and_precision_and_multiple_rules():
    assert rules([-10,10]) == ()
    assert [i for i,r,s in rules([-10.0000000001,10.0000000001]) if r=="BEYOND_LIMIT"] == [0,1]
    base = replace(BASE, cl=0, ucl=1, lcl=-1)
    signals = rules(list(range(1,10)), base)
    assert {r for i,r,s in signals if i==8} == {"BEYOND_LIMIT","TREND_UP_6","ABOVE_CL_9"}


def test_equality_invalid_and_explicit_break_reset_sequences():
    assert not any(r.startswith("TREND") for _,r,_ in rules([1,2,3,3,4,5]))
    groups = list(points([1]*10))
    groups[5] = replace(groups[5], mean=None, reasons=("invalid",))
    assert not detect_signals(groups, BASE)
    groups = list(points(range(1,7)))
    groups[3] = replace(groups[3], break_before=True)
    assert not detect_signals(groups, BASE)
