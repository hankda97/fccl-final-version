"""Routing tokens reject late work; navigation preserves content caches."""
from c_dashboard.workspace_modes.types import MODES, ContextToken, ModeIssue
from c_dashboard.workspace_modes.state import bind_context


def content_scope(workspace):
    c = workspace.mode_context
    if c is None:
        return ()
    return (c.mode_id, c.workspace_id, c.run_id, c.generation, c.settings_version,
            c.simulator_version, c.source_kind, c.cutoff)


def model_identity(adapter):
    """Use an existing optional manifest hook without extending B's protocol."""
    try:
        manifest = adapter.explanation_manifest() if hasattr(adapter, "explanation_manifest") else None
    except Exception as exc:
        manifest = ("MANIFEST_UNAVAILABLE", type(exc).__name__)
    return adapter.describe(), manifest


def request_token(workspace, request_key=""):
    from c_dashboard.replay.service import token
    return ContextToken((content_scope(workspace), workspace.data.source_id,
                         workspace.data.source_version, token(workspace.replay)),
                        workspace.mode_context.activation_epoch if workspace.mode_context else 0, request_key)


def switch_mode(registry, mode):
    if mode not in MODES:
        return ModeIssue("UNKNOWN_MODE", "mode_id", "未知模式；原工作區保持不變。")
    if mode == registry.active_mode:
        return None
    leaving = registry.workspaces[registry.active_mode]
    leaving.replay.playing, leaving.replay.last_tick = False, None
    leaving.mode_context.activation_epoch += 1
    bind_context(leaving)
    registry.active_mode = mode
    bind_context(registry.workspaces[mode])
    return None


def reset_run(registry, mode, run_id=None):
    """Explicit internal hook; not a simulator/start button in the normal UI."""
    if mode not in MODES:
        return ModeIssue("UNKNOWN_MODE", "mode_id", "未知模式")
    from c_dashboard.state import WorkspaceState
    old = registry.workspaces[mode]
    old.replay.playing, old.replay.last_tick = False, None
    context = old.mode_context
    context.generation += 1
    context.activation_epoch += 1
    context.run_id = run_id
    context.cutoff = None
    context.spc_profile = None
    bind_context(old)
    fresh = WorkspaceState()
    fresh.mode_context = context
    registry.workspaces[mode] = fresh
    bind_context(fresh)
    registry.preferences[mode].values.clear()
    return fresh


def accept_response(registry, mode, expected, request_key, *, value=None, error=None):
    workspace = registry.workspaces.get(mode)
    if (workspace is None or registry.active_mode != mode
            or expected != request_token(workspace, request_key)):
        issue = ModeIssue("STALE_CONTEXT", "context", "拒收舊模式、run 或來源的回應。")
        if mode in registry.errors:
            registry.errors[mode].append(issue)
        return False
    registry.errors[mode].extend([error] if error is not None else [])
    return True


def record_event(registry, mode, source, event_type, event_id, event):
    workspace = registry.workspaces[mode]
    c = workspace.mode_context
    key = (c.workspace_id, c.run_id, c.generation, source, event_type, event_id)
    registry.events[mode].setdefault(key, event)
    return key


def current_events(registry, mode):
    c = registry.workspaces[mode].mode_context
    return tuple(v for k, v in registry.events[mode].items() if k[:3] == (c.workspace_id, c.run_id, c.generation))
