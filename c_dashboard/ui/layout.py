"""Compose the dashboard with an explicit, isolated model source."""

from hashlib import sha256
import json
from pathlib import Path

import streamlit as st

from c_dashboard.adapters.formal import FormalModelAdapter
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.adapters.unavailable import UnavailableAdapter
from c_dashboard.quality.controller import (
    current_prediction_alarms,
    ensure_what_if_selection,
    monitor_prediction,
)
from c_dashboard.state import WorkspaceState
from c_dashboard.ui.overview import render_alarm_summary, render_overview
from c_dashboard.ui.replay_controls import render_replay_controls, render_replay_timer
from c_dashboard.ui.sidebar import render_sidebar
from c_dashboard.ui.tabs import render_tabs
from c_dashboard.spc.controller import analyze_workspace
from c_dashboard.data.session import selected_rows
from c_dashboard.adapters.explanations import UnavailableExplanationProvider
from c_dashboard.adapters.formal_explanations import FormalTreeShapProvider
from c_dashboard.ui.readiness import build_readiness_matrix, render_readiness_matrix


def explanation_provider_for(adapter):
    """Only a hash-verified formal adapter receives a real SHAP provider."""
    if isinstance(adapter, FormalModelAdapter):
        if not hasattr(adapter, "_formal_explanation_provider"):
            adapter._formal_explanation_provider = FormalTreeShapProvider(adapter)
        return adapter._formal_explanation_provider
    return UnavailableExplanationProvider()


@st.cache_resource
def _cached_formal_adapter(profile_root: str, registry_hash: str, source_manifest_json: str):
    del registry_hash
    source_manifest = json.loads(source_manifest_json) if source_manifest_json else None
    return FormalModelAdapter(profile_root, source_manifest)


def select_model_adapter(workspace: WorkspaceState):
    with st.sidebar:
        st.divider()
        st.subheader("模型來源")
        choices = ["C 公式 Mock", "Synthetic 正式 artifact", "未接入"]
        prior = workspace.model.selected_source if workspace.model.selected_source in choices else choices[0]
        selected = st.selectbox("推論來源", choices, index=choices.index(prior), key="ui_model_source")
        profile = st.selectbox(
            "模型標籤 profile", ["synthetic-ground-truth-v2", "simulated-inspection-v2"],
            index=0 if workspace.model.selected_profile == "synthetic-ground-truth-v2" else 1,
            key="ui_model_profile", disabled=selected != "Synthetic 正式 artifact",
        )
    if selected != workspace.model.selected_source or profile != workspace.model.selected_profile:
        workspace.model.selected_source = selected
        workspace.model.selected_profile = profile
        workspace.model.current_prediction_key = None
        workspace.model.current_prediction = None
        workspace.what_if.result_key = None
        workspace.what_if.comparison = None
        workspace.what_if.recommendation = None
        workspace.visualization.invalidate()
    if selected == "C 公式 Mock":
        return DeterministicMockAdapter()
    if selected == "未接入":
        return UnavailableAdapter()
    project = Path(__file__).resolve().parents[2]
    profile_root = project / "artifacts" / "synthetic_v2" / profile
    registry_path = profile_root / "registry.json"
    registry_hash = sha256(registry_path.read_bytes()).hexdigest() if registry_path.is_file() else "missing"
    dataset = workspace.data.dataset
    source_manifest = dataset.metadata.get("canonical_manifest") if dataset is not None else None
    source_json = json.dumps(source_manifest, sort_keys=True, ensure_ascii=False) if isinstance(source_manifest, dict) else ""
    return _cached_formal_adapter(str(profile_root), registry_hash, source_json)


def render_dashboard(workspace: WorkspaceState) -> None:
    st.title("FCCL 品質預測與 SPC 動態監控")
    st.caption("成員 C｜品質監控工作區")
    st.info("C4／C5 What-if 可明確切換 Synthetic 正式 artifact、C 公式 Mock 或未接入；所有 Synthetic 結果僅驗證流程，不代表真實產線效能或因果改善。")
    render_sidebar(workspace)
    render_replay_controls(workspace)
    spc_result = analyze_workspace(workspace)
    adapter = select_model_adapter(workspace)
    visible_rows = selected_rows(workspace)
    segment_options = ensure_what_if_selection(workspace, visible_rows)
    current_prediction = monitor_prediction(workspace, visible_rows, adapter)
    prediction_alarms, prediction_indeterminate = current_prediction_alarms(workspace, current_prediction)
    provider = explanation_provider_for(adapter)
    readiness = build_readiness_matrix(
        workspace, visible_rows, segment_options, adapter.describe(), provider.describe()
    )
    render_readiness_matrix(readiness)
    render_overview(workspace, adapter.describe(), spc_result,
                    current_prediction, prediction_alarms, prediction_indeterminate)
    render_tabs(workspace, spc_result, segment_options, adapter, provider, readiness)
    render_alarm_summary(adapter.describe(), spc_result,
                         current_prediction, prediction_alarms, prediction_indeterminate)
    render_replay_timer(workspace)
    st.divider()
    st.caption("僅供決策輔助與模擬介面開發；不控制真實產線機台。")
