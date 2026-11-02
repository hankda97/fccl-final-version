"""Atomic dataset changes and filter changes; no replay or what-if algorithms."""

import pandas as pd

from c_dashboard.data.loader import DataIssue, LoadResult, filter_rows, load_csv
from c_dashboard.data.schema import MappingProfile, parse_mapping
from c_dashboard.state import ReplayState, WhatIfState, WorkspaceState


def attempt_upload(content: bytes, name: str, mapping_json="") -> LoadResult:
    try:
        profile = parse_mapping(mapping_json)
    except (ValueError, TypeError, KeyError) as exc:
        return LoadResult(name, "upload", MappingProfile(), "", content,
                          issues=[DataIssue("MAPPING_CONFIG", None, None, str(exc), "error")])
    return load_csv(content, name, profile=profile)


def commit_dataset(workspace: WorkspaceState, result: LoadResult) -> bool:
    workspace.data.last_attempt = result
    if not result.accepted:
        return False
    if workspace.data.source_id == result.source_id:
        return True  # Same source/mapping/content: do not interrupt work.
    workspace.data.dataset = result
    workspace.data.source_id = result.source_id
    workspace.data.source_name = result.source_name
    workspace.data.source_version = result.profile.version
    workspace.data.csv_bytes = result.content
    workspace.data.selected_batch = None
    workspace.data.time_start = None
    workspace.data.time_end = None
    workspace.data.temporal_config = None
    workspace.data.validation_status = "issues" if any(item.severity != "info" for item in result.issues) else "valid"
    workspace.replay = ReplayState(mode=workspace.replay.mode, stream_id=result.source_id,
                                   generation=workspace.replay.generation + 1, speed=workspace.replay.speed)
    workspace.what_if = WhatIfState()
    workspace.model.baseline_version = None
    workspace.model.current_prediction_key = None
    workspace.model.current_prediction = None
    workspace.spc.result_key = None
    workspace.spc.result = None
    workspace.visualization.invalidate()
    from c_dashboard.workspace_modes.state import bind_context
    bind_context(workspace)
    return True


def set_filters(workspace: WorkspaceState, batch, start, end) -> None:
    requested = (batch, start, end)
    previous = (workspace.data.selected_batch, workspace.data.time_start, workspace.data.time_end)
    if requested == previous:
        return
    workspace.data.selected_batch, workspace.data.time_start, workspace.data.time_end = requested
    workspace.replay = ReplayState(mode=workspace.replay.mode, stream_id=workspace.data.source_id,
                                   generation=workspace.replay.generation + 1, speed=workspace.replay.speed)
    workspace.what_if = WhatIfState()
    workspace.model.current_prediction_key = None
    workspace.model.current_prediction = None

    workspace.spc.result_key = None
    workspace.spc.result = None
    workspace.visualization.invalidate()
    from c_dashboard.workspace_modes.state import bind_context
    bind_context(workspace)


def selected_rows(workspace: WorkspaceState) -> pd.DataFrame:
    if workspace.replay.mode == "replay":
        from c_dashboard.replay.controller import snapshot_for
        return snapshot_for(workspace).rows
    if workspace.data.dataset is None:
        return pd.DataFrame()
    return filter_rows(workspace.data.dataset.frame, workspace.data.selected_batch,
                       workspace.data.time_start, workspace.data.time_end)
