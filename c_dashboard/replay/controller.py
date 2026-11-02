"""Workspace lifecycle and safe views shared by every consumer."""
from hashlib import sha256
import json
from c_dashboard.data.loader import filter_rows
from c_dashboard.replay.temporal import build_timeline
from c_dashboard.replay.service import command


def cohort_rows(workspace):
    import pandas as pd
    d = workspace.data
    return filter_rows(d.dataset.frame, d.selected_batch, d.time_start, d.time_end) if d.dataset else pd.DataFrame()


def clear_results(workspace, *, invalidate_selection=False):
    workspace.spc.result_key, workspace.spc.result = None, None
    workspace.model.current_prediction_key, workspace.model.current_prediction = None, None
    workspace.visualization.invalidate()
    if invalidate_selection:
        w = workspace.what_if
        w.requires_reselect = w.selected is not None or w.requires_reselect
        w.parameters.clear()
        w.comparison, w.recommendation, w.result_key = None, None, None
        w.advanced_unlocked = False


def timeline_for(workspace):
    rows = cohort_rows(workspace)
    d, state = workspace.data, workspace.replay
    signature = sha256(json.dumps((d.source_id, d.source_version, d.dataset.profile.signature() if d.dataset else None,
                                  d.temporal_config, d.selected_batch, d.time_start, d.time_end,
                                  d.dataset.metadata if d.dataset else None), sort_keys=True, default=str).encode()).hexdigest()
    cached = state.timeline
    if cached is None or getattr(state, "timeline_key", None) != signature:
        state.timeline = build_timeline(d.dataset, rows, d.temporal_config)
        state.timeline_key = signature
        state.stream_id = state.timeline.stream_id
        if state.mode == "replay":
            command(state, state.timeline, "restart", 0)
            clear_results(workspace, invalidate_selection=True)
    return state.timeline


def snapshot_for(workspace):
    from c_dashboard.replay.service import visibility
    return visibility(workspace.replay, timeline_for(workspace))


def set_mode(workspace, mode):
    if workspace.replay.mode == mode:
        return
    workspace.replay.mode = mode
    timeline = timeline_for(workspace)
    command(workspace.replay, timeline, "restart", 0)
    clear_results(workspace, invalidate_selection=mode == "replay")


def operate(workspace, action, now, *, speed=None):
    timeline = timeline_for(workspace)
    command(workspace.replay, timeline, action, now, speed=speed)
    if action in {"restart", "step"}:
        clear_results(workspace, invalidate_selection=action == "restart")


def set_temporal_config(workspace, config):
    from c_dashboard.replay.temporal import profile_for
    if config is not None:
        profile_for(workspace.data.dataset, config)  # Validate before committing.
    if config != workspace.data.temporal_config:
        workspace.data.temporal_config = config
        timeline_for(workspace)


def historical_model_reason(workspace, adapter, *, explanation=False):
    """Optional C consumption hook; does not extend B's mandatory model protocol."""
    if workspace.replay.mode != "replay":
        return None
    # Formula Mock and explicit render-test subclasses are deterministic demonstrations.
    from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
    if not explanation and type(adapter) is DeterministicMockAdapter:
        return None
    cutoff = workspace.replay.virtual_clock
    try:
        metadata = adapter.historical_applicability() if hasattr(adapter, "historical_applicability") else None
    except Exception as exc:
        return f"HISTORICAL_APPLICABILITY_UNCONFIRMED：模型時間接點失敗（{type(exc).__name__}）"
    if not cutoff or not metadata:
        return "HISTORICAL_APPLICABILITY_UNCONFIRMED：模型／背景時間待 B／C9 整合"
    from c_dashboard.replay.temporal import aware
    try:
        if aware(metadata["available_at"]) > aware(cutoff) or aware(metadata["training_cutoff"]) > aware(cutoff):
            return "MODEL_NOT_AVAILABLE_AS_OF_CUTOFF"
        if explanation and aware(metadata["background_available_at"]) > aware(cutoff):
            return "BACKGROUND_NOT_AVAILABLE_AS_OF_CUTOFF"
    except (KeyError, ValueError, TypeError):
        return "HISTORICAL_APPLICABILITY_UNCONFIRMED：缺可靠模型／背景時間"
    return None
