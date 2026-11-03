import math

import pytest

from fccl_testline.process_spc import IncrementalSPC, imr_limits, xbar_r_limits


def test_known_xbar_r_limits_and_incomplete_subgroup() -> None:
    groups = [[25 + .1*((i+j) % 5 - 2) for j in range(5)] for i in range(25)]
    limits = xbar_r_limits(groups)
    assert limits.chart_type == "XBAR_R" and limits.center == pytest.approx(25.0)
    assert limits.secondary_center == pytest.approx(.4)
    engine = IncrementalSPC(limits)
    assert engine.update_subgroup([25,25.1,24.9,25.0,25.2])["xbar"] == pytest.approx(25.04)
    with pytest.raises(ValueError, match="INCOMPLETE"): engine.update_subgroup([25,25])


def test_imr_and_ewma_incremental_known_sequence_and_recent_window() -> None:
    baseline = [100 + (i % 3 - 1) for i in range(30)]
    imr = IncrementalSPC(imr_limits(baseline))
    first = imr.update_individual(100); second = imr.update_individual(102)
    assert math.isnan(first["moving_range"]) and second["moving_range"] == 2
    for i in range(70): imr.update_individual(float(i))
    assert len(imr.recent()) == 60 and imr.recent()[-1] == 69
    ewma = IncrementalSPC(imr_limits(baseline, chart_type="EWMA"), ewma_lambda=.2)
    ewma.update_individual(100); point = ewma.update_individual(110)
    assert point["plotted"] == pytest.approx(102)


def test_baseline_must_be_fixed_sufficient_and_nondegenerate() -> None:
    with pytest.raises(ValueError, match="INSUFFICIENT"): imr_limits([1,2,3])
    with pytest.raises(ValueError, match="DEGENERATE"): imr_limits([1]*30)
    limits = imr_limits(list(range(30)))
    engine = IncrementalSPC(limits); original = engine.limits
    for value in [1000]*100: engine.update_individual(value)
    assert engine.limits == original
