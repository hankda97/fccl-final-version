"""Non-destructive migration and mode-aware widget persistence."""
from c_dashboard.state import WORKSPACE_KEY, WorkspaceState, ensure_workspace
from c_dashboard.workspace_modes.types import MODES, REGISTRY_VERSION, ModeRegistry, RunContext

REGISTRY_KEY = "fccl_mode_registry"


def bind_context(workspace):
    context = workspace.mode_context
    if context is not None:
        workspace.replay.lifecycle_token = f"{context.mode_id}:{context.workspace_id}:{context.activation_epoch}"


def ensure_registry(session):
    registry = session.get(REGISTRY_KEY)
    if registry is not None:
        # Streamlit hot reload can recreate the Python class while preserving
        # Session State. Validate the explicit schema, not class object identity.
        if (getattr(registry, "version", None) != REGISTRY_VERSION
                or not all(m in getattr(registry, "workspaces", {}) for m in MODES)
                or getattr(registry, "active_mode", None) not in MODES):
            raise ValueError("REGISTRY_VERSION_UNSUPPORTED：保留原工作階段，請先確認遷移版本。")
        session[WORKSPACE_KEY] = registry.workspaces["analysis"]
        return registry
    original = ensure_workspace(session)
    workspaces = {"analysis": original, "testline": WorkspaceState(), "production": WorkspaceState()}
    for mode, workspace in workspaces.items():
        workspace.mode_context = RunContext(mode)
        bind_context(workspace)
    registry = ModeRegistry(workspaces)
    session[REGISTRY_KEY] = registry
    return registry


def widget_key(workspace, key):
    context = workspace.mode_context if workspace is not None else None
    return key if context is None or context.mode_id == "analysis" else f"{context.mode_id}:{context.workspace_id}:{key}"


# Durable logical choices only. Buttons, form-submit triggers and upload objects
# are intentionally excluded; CSV bytes already live in DataState.
PREFERENCE_PREFIXES = ("ui_source_choice", "ui_mock_scenario", "ui_mapping_json", "ui_temporal_json",
    "ui_batch_", "ui_time_", "ui_mode_placeholder", "ui_speed_placeholder", "ui_workspace_tabs",
    "ui_whatif_segment_", "ui_replay_segment_", "ui_whatif_speed_", "ui_whatif_curing_",
    "ui_whatif_lamination_", "ui_heatmap_features_", "ui_heatmap_targets_", "ui_shap_kind",
    "ui_shap_target", "ui_shap_feature_", "ui_spc_target")


def save_preferences(registry, session):
    mode = registry.active_mode
    workspace = registry.workspaces[mode]
    prefix = "" if mode == "analysis" else f"{mode}:{workspace.mode_context.workspace_id}:"
    values = {}
    for key in list(session):
        plain = key[len(prefix):] if key.startswith(prefix) else ""
        if plain.startswith(PREFERENCE_PREFIXES):
            values[key] = session[key]
    registry.preferences[mode].values = values


def restore_preferences(registry, session):
    for key, value in registry.preferences[registry.active_mode].values.items():
        if key not in session:
            session[key] = value
