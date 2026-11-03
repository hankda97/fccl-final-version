"""C's UI composition boundary. Pure analysis stays in service.py."""

from hashlib import sha256
from dataclasses import replace
from c_dashboard.data.schema import TARGET_UNITS

from c_dashboard.data.fixtures import load_spc_history
from c_dashboard.data.loader import filter_rows
from c_dashboard.data.session import selected_rows
from c_dashboard.spc.baseline import build_baseline, frame_signature, natural_samples
from c_dashboard.spc.config import RuleConfig, digest
from c_dashboard.spc.service import compute_spc
from c_dashboard.spc.sources import profile_for_dataset, spc_source_for_dataset  # profile seam kept for tests/extensions
from c_dashboard.spc.types import SourceContext


def analyze_workspace(workspace):
    dataset = workspace.data.dataset
    rows = selected_rows(workspace)
    error, profile, baseline = (), None, None
    try:
        mode = workspace.mode_context
        source = spc_source_for_dataset(dataset) if mode is None or mode.mode_id == "analysis" else None
        profile = source.profile if source is not None else mode.spc_profile
        if source is not None and source.monitoring is not None:
            rows = filter_rows(source.monitoring, workspace.data.selected_batch,
                               workspace.data.time_start, workspace.data.time_end)
        if mode is not None and mode.mode_id != "analysis":
            baseline = workspace.spc.baseline  # Never borrow A's history.
        elif profile is not None:
            if source is not None and source.history is not None:
                history_frame = source.history
                history_hash = profile.history_hash
                baseline_source = source.baseline_source
                monitor_samples = natural_samples(source.monitoring)
            else:
                history = load_spc_history()
                history_frame = history.frame
                history_hash = sha256(history.content).hexdigest()
                baseline_source = "C 獨立歷史 Mock（固定基準）"
                monitor_samples = ()
            baseline_key = digest((source.identity if source is not None else "mode", history_hash,
                                   profile.signature()))
            if baseline_key != workspace.spc.baseline_key:
                baseline = build_baseline(history_frame, profile, history_hash=history_hash,
                                          source=baseline_source, monitor_samples=monitor_samples)
                workspace.spc.baseline = baseline
                workspace.spc.baseline_key = baseline_key
            else:
                baseline = workspace.spc.baseline
        if source is not None and source.issues:
            error = tuple(source.issues)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # Keep CSV view operational; an explicit resource error is not "normal".
        error = (f"SPC_RESOURCE_UNAVAILABLE:{type(exc).__name__}",)
    context = SourceContext(workspace.data.source_id or "not-loaded", profile,
                            workspace.data.source_version or "", error)
    from c_dashboard.workspace_modes.controller import content_scope
    source_identity = source.identity if 'source' in locals() and source is not None else ""
    key = digest((content_scope(workspace), context.source_id, context.mapping_version, source_identity,
                  RuleConfig().version, frame_signature(rows),
                  (workspace.data.selected_batch, workspace.data.time_start, workspace.data.time_end),
                  profile.signature() if profile else None, baseline.version if baseline else None, error))
    if workspace.replay.mode == "replay":
        from c_dashboard.replay.service import content_token
        key = digest((key, content_token(workspace.replay)))
    if key != workspace.spc.result_key:
        if workspace.replay.mode == "replay":
            from c_dashboard.replay.controller import snapshot_for
            snapshot = snapshot_for(workspace)
            scope = digest((content_scope(workspace), workspace.replay.stream_id, workspace.replay.generation))
            # A delayed timer may cross many releases. Observe each intermediate
            # prefix so a later incomplete/late group cannot erase an earlier signal.
            if profile is not None and baseline is not None:
                from c_dashboard.replay.service import visibility
                state = workspace.replay
                for cursor in range(state.spc_processed_cursor + 1, state.cursor):
                    prefix = replace(state, cursor=cursor,
                                     virtual_clock=state.timeline.groups[cursor-1][0].available_at.isoformat())
                    interim = visibility(prefix, state.timeline)
                    for target in TARGET_UNITS:
                        partial = compute_spc(interim.measurements[target], context, baseline, analysis_scope_id=scope)
                        for event in partial.events:
                            if event.target == target:
                                state.spc_events[event.event_id] = event
            results = [compute_spc(snapshot.measurements[target], context, baseline, analysis_scope_id=scope)
                       for target in TARGET_UNITS]
            workspace.spc.result = replace(results[0], cutoff=snapshot.cutoff,
                targets=tuple(r.target(t) for t, r in zip(TARGET_UNITS, results) if t != "appearance_ng"),
                events=tuple(e for t, r in zip(TARGET_UNITS, results) for e in r.events if e.target == t),
                raw=tuple(v for t, r in zip(TARGET_UNITS, results) for v in r.raw if v.target == t),
                appearance_count=results[-1].appearance_count, appearance_ng=results[-1].appearance_ng)
            for event in workspace.spc.result.events:
                workspace.replay.spc_events[event.event_id] = event
            workspace.spc.result = replace(workspace.spc.result, events=tuple(workspace.replay.spc_events.values()))
            workspace.replay.spc_processed_cursor = workspace.replay.cursor
        else:
            workspace.spc.result = compute_spc(rows, context, baseline, analysis_scope_id=key)
        workspace.spc.result_key = key
    return workspace.spc.result
