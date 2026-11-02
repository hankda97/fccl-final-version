"""C1's state and adapter seams, without any A/B or analytical code."""

from dataclasses import FrozenInstanceError

import pytest

from c_dashboard.adapters.base import (
    AdapterInfo,
    ModelAdapter,
    PredictionInput,
    PredictionRecord,
    PredictionResult,
)
from c_dashboard.adapters.unavailable import UnavailableAdapter
from c_dashboard.state import SegmentSnapshot, ensure_workspace


def test_reinitialization_preserves_business_state():
    session = {}
    workspace = ensure_workspace(session)
    workspace.data.csv_bytes = b"test-only data"
    workspace.data.source_id = "test-source"
    workspace.data.selected_batch = "B-1"
    workspace.replay.cursor = 7
    workspace.replay.speed = 2.0
    workspace.what_if.selected = SegmentSnapshot(
        "test-source", "B-1", "S-1", "2026-11-01T08:00:00+08:00"
    )
    workspace.what_if.parameters["line_speed_m_min"] = 1.2
    workspace.what_if.advanced_unlocked = True
    workspace.model.version = "test-only"

    assert ensure_workspace(session) is workspace
    assert workspace.data.csv_bytes == b"test-only data"
    assert workspace.data.selected_batch == "B-1"
    assert workspace.replay.cursor == 7
    assert workspace.replay.speed == 2.0
    assert workspace.what_if.selected.segment_id == "S-1"
    assert workspace.what_if.parameters == {"line_speed_m_min": 1.2}
    assert workspace.what_if.advanced_unlocked
    assert workspace.model.version == "test-only"


def test_sessions_do_not_share_mutable_parameters():
    first = ensure_workspace({})
    second = ensure_workspace({})
    first.what_if.parameters["line_speed_m_min"] = 1.2
    first.replay.cursor = 7
    assert second.what_if.parameters == {}
    assert second.replay.cursor == 0
    assert first.data is not second.data


def test_original_snapshot_is_immutable():
    snapshot = SegmentSnapshot(
        "test", "B-1", "S-1", "2026-11-01T08:00:00+08:00",
        process_settings=(("line_speed_m_min", 1.4),),
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.segment_id = "S-2"


def test_unavailable_adapter_never_invents_predictions():
    adapter = UnavailableAdapter()
    result = adapter.predict([PredictionInput("S-1", {"line_speed_m_min": 1.2})])
    assert not result.info.available
    assert not result.info.supports_shap
    assert result.info.version is None
    assert result.records == ()
    assert "正式模型" in result.info.message
    assert "Mock" in result.info.message


def test_internal_port_accepts_test_substitute_without_team_modules():
    class TestAdapter:
        def describe(self):
            return AdapterInfo("測試替身", "test-v1", True, False, "僅測試接點")

        def predict(self, samples):
            return PredictionResult(
                self.describe(),
                tuple(PredictionRecord(sample.sample_id, {"test_target": 1.0}) for sample in samples),
            )

    adapter: ModelAdapter = TestAdapter()
    inputs = [PredictionInput("S-2", {}), PredictionInput("S-1", {})]
    result = adapter.predict(inputs)
    assert [record.sample_id for record in result.records] == ["S-2", "S-1"]
    assert result.info.source == "測試替身"
    assert result.info.version == "test-v1"
    assert not result.info.supports_shap
