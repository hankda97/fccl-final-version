"""Four persistent dashboard feature areas."""

import streamlit as st
from c_dashboard.workspace_modes.state import widget_key

from c_dashboard.state import WorkspaceState
from c_dashboard.ui.data_inspection import render_data_inspection
from c_dashboard.ui.spc_panel import render_spc_panel
from c_dashboard.ui.whatif_panel import render_whatif_panel
from c_dashboard.ui.visualization_panel import render_visualization_panel
from c_dashboard.data.session import selected_rows

TAB_LABELS = ("SPC 監控", "What-if", "AI 圖表", "資料檢查")


def render_tabs(workspace: WorkspaceState, spc_result, segment_options, adapter, explanation_provider=None,
                readiness=None) -> None:
    tabs = st.tabs(TAB_LABELS, key=widget_key(workspace, "ui_workspace_tabs"), on_change="rerun")
    with tabs[0]:
        render_spc_panel(spc_result, workspace)
    with tabs[1]:
        render_whatif_panel(workspace, segment_options, adapter, readiness.get("what_if") if readiness else None)
    with tabs[2]:
        render_visualization_panel(workspace, selected_rows(workspace), adapter, explanation_provider, readiness)
    with tabs[3]:
        render_data_inspection(workspace)
