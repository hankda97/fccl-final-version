from copy import deepcopy

import pytest

from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.adapters.base import AdapterInfo, PredictionRecord, PredictionResult
from c_dashboard.data.fixtures import load_mock_fixture, MOCK_CHOICES
from c_dashboard.data.session import commit_dataset, selected_rows
from c_dashboard.quality.controller import (
    ensure_what_if_selection, evaluate_what_if, select_what_if_segment,
    snapshot_features,
)
from c_dashboard.spc.controller import analyze_workspace
from c_dashboard.state import ensure_workspace
from c_dashboard.data.schema import TARGET_UNITS


def _loaded(label="normal"):
    workspace = ensure_workspace({})
    assert commit_dataset(workspace, load_mock_fixture(label))
    rows = selected_rows(workspace)
    options = ensure_what_if_selection(workspace, rows)
    return workspace, rows, options


def test_latest_visible_segment_is_default_snapshot_and_reselection_invalidates_result():
    workspace, rows, options = _loaded()
    selected = workspace.what_if.selected
    assert selected == options[-1]
    assert selected.sample_id == rows.iloc[-1].sample_id
    assert (selected.batch_id, selected.segment_id, selected.timestamp) == (
        rows.iloc[-1].product_batch, rows.iloc[-1].segment_id, rows.iloc[-1].timestamp.isoformat()
    )
    assert dict(selected.process_settings)["line_speed_m_min"] == rows.iloc[-1].line_speed_m_min
    assert dict(selected.environment)["ambient_rh_pct"] == rows.iloc[-1].ambient_rh_pct

    workspace.what_if.parameters["line_speed_m_min"] = 1.8
    workspace.what_if.editing_started = True
    evaluate_what_if(workspace, DeterministicMockAdapter())
    assert workspace.what_if.comparison is not None
    select_what_if_segment(workspace, options[0])
    assert workspace.what_if.selected == options[0]
    assert workspace.what_if.parameters == {}
    assert workspace.what_if.comparison is None
    assert not workspace.what_if.editing_started


def test_whatif_edits_do_not_mutate_csv_or_spc_calculation():
    workspace, rows, _ = _loaded()
    original_frame = workspace.data.dataset.frame.copy(deep=True)
    spc_before = analyze_workspace(workspace)
    workspace.what_if.parameters["line_speed_m_min"] = 1.8
    workspace.what_if.comparison, workspace.what_if.recommendation = evaluate_what_if(
        workspace, DeterministicMockAdapter()
    )
    spc_after = analyze_workspace(workspace)
    assert workspace.data.dataset.frame.equals(original_frame)
    assert selected_rows(workspace).equals(rows)
    assert spc_after == spc_before


def test_only_allowlisted_finite_in_range_parameters_can_be_overridden():
    workspace, _, _ = _loaded()
    snapshot = workspace.what_if.selected
    original = snapshot_features(snapshot)
    for bad in (float("nan"), float("inf"), -100):
        with pytest.raises(ValueError):
            snapshot_features(snapshot, {"line_speed_m_min": bad})
    with pytest.raises(ValueError, match="不允許"):
        snapshot_features(snapshot, {"ambient_rh_pct": 30})
    assert snapshot_features(snapshot, {}) == original


def test_advanced_parameters_rejected_until_unlocked():
    workspace, _, _ = _loaded()
    selected = workspace.what_if.selected
    workspace.what_if.parameters["curing_temp_c"] = dict(selected.process_settings)["curing_temp_c"] + 1
    comparison, _ = evaluate_what_if(workspace, DeterministicMockAdapter())
    assert comparison.before is None and comparison.after is None
    assert "尚未解鎖" in comparison.unavailable_reason


def test_source_switch_resets_fixed_snapshot_and_all_overrides():
    workspace, _, _ = _loaded()
    workspace.what_if.parameters["line_speed_m_min"] = 1.8
    workspace.what_if.advanced_unlocked = True
    old_source = workspace.what_if.selected.source_id
    assert commit_dataset(workspace, load_mock_fixture("partial_quality"))
    assert workspace.data.source_id != old_source
    assert workspace.what_if.selected is None
    assert workspace.what_if.parameters == {}
    assert not workspace.what_if.advanced_unlocked


def test_c4_adapter_stub_drives_five_target_before_after_comparison():
    class DeterministicStub:
        def describe(self):
            return AdapterInfo("C4 測試替身", "stub-v1", True, False, "測試用", tuple(TARGET_UNITS))

        def predict(self, samples):
            records = []
            for sample in samples:
                speed = sample.features["line_speed_m_min"]
                targets = {
                    "peel_strength_n_mm": 1.0 + speed,
                    "dimensional_stability_md_pct": 0.01 * speed,
                    "dimensional_stability_td_pct": -0.01 * speed,
                    "heat_resistance_c": 260.0 + speed,
                    "appearance_ng": 0,
                }
                records.append(PredictionRecord(sample.sample_id, targets, 0.1, {}, TARGET_UNITS))
            return PredictionResult(self.describe(), tuple(records))

    workspace, _, _ = _loaded()
    workspace.what_if.parameters["line_speed_m_min"] = 1.8
    comparison, _ = evaluate_what_if(workspace, DeterministicStub())
    assert comparison.before is not None and comparison.after is not None
    assert set(comparison.before.targets) == set(TARGET_UNITS)
    assert comparison.before.target_units == TARGET_UNITS
    assert comparison.before.targets["peel_strength_n_mm"] != comparison.after.targets["peel_strength_n_mm"]
