"""Compose presentation areas without implementing later-stage workflows."""

import streamlit as st

from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.quality.controller import (
    current_prediction_alarms,
    ensure_what_if_selection,
    monitor_prediction,
)
from c_dashboard.state import WorkspaceState
from c_dashboard.ui.overview import render_overview
from c_dashboard.ui.replay_controls import render_replay_controls, render_replay_timer
from c_dashboard.ui.sidebar import render_sidebar
from c_dashboard.ui.tabs import render_tabs
from c_dashboard.spc.controller import analyze_workspace
from c_dashboard.data.session import selected_rows
from c_dashboard.adapters.explanations import UnavailableExplanationProvider


def explanation_provider_for(adapter):
    """C9 may compose a trusted provider here; default Mock has no SHAP."""
    return UnavailableExplanationProvider()


def render_dashboard(workspace: WorkspaceState) -> None:
    st.title("FCCL 品質預測與 SPC 動態監控")
    st.caption("成員 C｜品質監控工作區")
    st.info("C4／C5 What-if 與確定性公式 Mock 已提供示範流程；C6 提供 Heatmap 與 SHAP 呈現接點；正式模型、真正 SHAP 及品質策略仍待跨組整合。")
    render_sidebar(workspace)
    render_replay_controls(workspace)
    spc_result = analyze_workspace(workspace)
    adapter = DeterministicMockAdapter()
    visible_rows = selected_rows(workspace)
    segment_options = ensure_what_if_selection(workspace, visible_rows)
    current_prediction = monitor_prediction(workspace, visible_rows, adapter)
    prediction_alarms, prediction_indeterminate = current_prediction_alarms(workspace, current_prediction)
    render_overview(workspace, adapter.describe(), spc_result,
                    current_prediction, prediction_alarms, prediction_indeterminate)
    render_tabs(workspace, spc_result, segment_options, adapter, explanation_provider_for(adapter))
    render_replay_timer(workspace)
    st.divider()
    st.caption("僅供決策輔助與模擬介面開發；不控制真實產線機台。")
