from pathlib import Path

import numpy as np
import pytest

from c_dashboard.data.loader import load_csv
from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.visualization.config import MINIMUM_PAIRS
from c_dashboard.visualization.heatmap import compute_heatmap, source_for

PEEL = "peel_strength_n_mm"
SPEED = "line_speed_m_min"
MD = "dimensional_stability_md_pct"
TD = "dimensional_stability_td_pct"


def hand_rows():
    path = Path(__file__).parent / "fixtures/c_visualization/hand_calculation.csv"
    result = load_csv(path.read_bytes(), path.name)
    assert result.accepted
    return result.frame


def source(rows):
    return source_for(rows, source_id="C6-test", mapping_version="test-v1", source_kind="mock")


def test_hand_calculated_positive_negative_zero_and_units():
    rows = hand_rows()
    original = rows.copy(deep=True)
    result = compute_heatmap(rows, source(rows), [SPEED], list(TARGET_UNITS))
    cells = {cell.target: cell for cell in result.cells}
    assert cells[PEEL].coefficient == pytest.approx(1)
    assert cells[MD].coefficient == pytest.approx(-1)
    assert cells[TD].coefficient == pytest.approx(0)
    assert all(cell.n == 4 for cell in result.cells)
    assert result.minimum_pairs == MINIMUM_PAIRS == 3
    assert rows.equals(original)


def test_pairwise_counts_partial_invalid_and_absent_quality():
    rows = hand_rows()
    rows.loc[rows.index[0], PEEL] = np.nan
    rows.loc[rows.index[1], MD] = np.inf
    rows = rows.drop(columns=[TD])
    result = compute_heatmap(rows, source(rows), [SPEED], [PEEL, MD, TD])
    assert [cell.n for cell in result.cells] == [3, 3, 0]
    assert [cell.excluded for cell in result.cells] == [1, 1, 4]
    assert result.cells[0].coefficient == pytest.approx(1)
    assert result.cells[1].coefficient == pytest.approx(-1)
    assert "缺少欄位" in result.cells[2].reason


def test_constants_single_class_and_insufficient_pairs_are_not_zero():
    rows = hand_rows()
    result = compute_heatmap(rows, source(rows), ["ambient_rh_pct"], [PEEL])
    assert result.cells[0].coefficient is None and "常數" in result.cells[0].reason
    rows["appearance_ng"] = 0
    result = compute_heatmap(rows, source(rows), [SPEED], ["appearance_ng"])
    assert result.cells[0].coefficient is None and "單一類別" in result.cells[0].reason
    small = rows.iloc[:2]
    result = compute_heatmap(small, source(small), [SPEED], [PEEL])
    assert result.cells[0].coefficient is None and "不足" in result.cells[0].reason


def test_invalid_identity_duplicates_non_numeric_allowlist_and_empty_selection():
    rows = hand_rows()
    rows.loc[rows.index[0], "identity_valid"] = False
    rows.loc[rows.index[1], "duplicate_record"] = True
    result = compute_heatmap(rows, source(rows), [SPEED], [PEEL])
    assert result.eligible_rows == 2 and result.excluded_identity == 2
    with pytest.raises(ValueError, match="allowlist"):
        compute_heatmap(rows, source(rows), ["product_batch"], [PEEL])
    rows[SPEED] = rows[SPEED].astype(object)
    rows.loc[rows.index[2], SPEED] = "bad"
    assert compute_heatmap(rows, source(rows), [SPEED], [PEEL]).cells[0].n == 1
    assert compute_heatmap(rows, source(rows), [], [PEEL]).cells == ()


def test_bounded_input_and_unrelated_prediction_values_do_not_change_results():
    rows = hand_rows()
    first = compute_heatmap(rows, source(rows), [SPEED], [PEEL])
    rows["pred_peel_strength_n_mm"] = 999
    rows["hidden_truth"] = -999
    assert compute_heatmap(rows, source(rows), [SPEED], [PEEL]) == first
    prefix = rows.iloc[:3].copy()
    saved = compute_heatmap(prefix, source(prefix), [SPEED], [PEEL])
    rows.loc[rows.index[-1], PEEL] = 99999
    assert compute_heatmap(prefix, source(prefix), [SPEED], [PEEL]) == saved
