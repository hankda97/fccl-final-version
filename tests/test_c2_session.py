from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.data.session import attempt_upload, commit_dataset, selected_rows, set_filters
from c_dashboard.state import SegmentSnapshot, ensure_workspace


def test_successful_source_switch_clears_dependent_state_but_not_model_identity():
    workspace = ensure_workspace({})
    first = load_mock_fixture("normal")
    assert commit_dataset(workspace, first)
    workspace.replay.cursor = 8
    workspace.replay.playing = True
    workspace.what_if.selected = SegmentSnapshot("test", "B", "S", "2026-11-01T08:00:00+08:00")
    workspace.what_if.parameters["line_speed_m_min"] = 1.2
    workspace.what_if.advanced_unlocked = True
    workspace.model.version = "unloaded-test-version"
    workspace.model.baseline_version = "old-data"
    generation = workspace.replay.generation
    assert commit_dataset(workspace, load_mock_fixture("partial_quality"))
    assert workspace.data.source_id != first.source_id
    assert workspace.data.selected_batch is None
    assert workspace.replay.cursor == 0 and not workspace.replay.playing
    assert workspace.replay.generation == generation + 1
    assert workspace.what_if.selected is None
    assert workspace.what_if.parameters == {} and not workspace.what_if.advanced_unlocked
    assert workspace.model.baseline_version is None
    assert workspace.model.version == "unloaded-test-version"


def test_failed_attempt_preserves_previous_valid_data_and_filters():
    workspace = ensure_workspace({})
    first = load_mock_fixture("normal")
    commit_dataset(workspace, first)
    set_filters(workspace, "M-B02", "2026-11-01T08:16:00+08:00", "2026-11-01T08:18:00+08:00")
    assert not commit_dataset(workspace, attempt_upload(b"", "empty.csv"))
    assert workspace.data.dataset is first
    assert workspace.data.csv_bytes == first.content
    assert workspace.data.selected_batch == "M-B02"
    assert len(selected_rows(workspace)) == 15
    assert workspace.data.last_attempt.source_name == "empty.csv"


def test_same_source_reload_and_unchanged_filters_do_not_interrupt_work():
    workspace = ensure_workspace({})
    commit_dataset(workspace, load_mock_fixture("normal"))
    set_filters(workspace, None, None, None)
    workspace.replay.cursor = 7
    workspace.what_if.parameters["line_speed_m_min"] = 1.2
    generation = workspace.replay.generation
    assert commit_dataset(workspace, load_mock_fixture("normal"))
    set_filters(workspace, None, None, None)
    assert workspace.replay.cursor == 7
    assert workspace.replay.generation == generation
    assert workspace.what_if.parameters == {"line_speed_m_min": 1.2}


def test_mapping_errors_and_mapping_version_identity():
    workspace = ensure_workspace({})
    payload = load_mock_fixture("normal").content
    first = attempt_upload(payload, "uploaded.csv")
    commit_dataset(workspace, first)
    assert not commit_dataset(workspace, attempt_upload(payload, "uploaded.csv", "not json"))
    assert workspace.data.dataset is first
    assert workspace.data.last_attempt.issues[0].code == "MAPPING_CONFIG"
    changed = attempt_upload(payload, "uploaded.csv", '{"version":"other-version"}')
    assert changed.source_id != first.source_id
    assert commit_dataset(workspace, changed)


def test_filter_result_is_separate_and_can_be_empty():
    workspace = ensure_workspace({})
    result = load_mock_fixture("normal")
    commit_dataset(workspace, result)
    view = selected_rows(workspace)
    original = result.frame.peel_strength_n_mm.iloc[0]
    view.loc[0, "peel_strength_n_mm"] = 999
    assert result.frame.peel_strength_n_mm.iloc[0] == original
    set_filters(workspace, "M-B02", "2026-11-01T08:00:00+08:00", "2026-11-01T08:01:00+08:00")
    assert selected_rows(workspace).empty
