"""Outer application navigation; B/C remain visibly unavailable."""
import streamlit as st
from c_dashboard.workspace_modes.types import MODES, LABELS
from c_dashboard.workspace_modes.state import save_preferences, restore_preferences
from c_dashboard.workspace_modes.controller import switch_mode
from c_dashboard.workspace_modes.ports import ProviderRegistry


def render_mode_navigation(registry):
    def change():
        save_preferences(registry, st.session_state)
        issue = switch_mode(registry, st.session_state.ui_application_mode)
        if issue:
            registry.errors[registry.active_mode].append(issue)
            st.session_state.ui_application_mode = registry.active_mode
        restore_preferences(registry, st.session_state)
    if st.session_state.get("ui_application_mode", registry.active_mode) not in MODES:
        st.session_state.ui_application_mode = registry.active_mode
    with st.sidebar:
        st.radio("應用模式", MODES, index=MODES.index(registry.active_mode),
                 format_func=LABELS.get, key="ui_application_mode", on_change=change)
    restore_preferences(registry, st.session_state)
    st.caption("目前模式：" + LABELS[registry.active_mode])
    for issue in registry.errors[registry.active_mode][-3:]:
        st.warning(f"{issue.code}：{issue.message}")


def render_unavailable_mode(registry):
    mode = registry.active_mode
    info = ProviderRegistry().get(mode).describe()
    st.title(LABELS[mode])
    st.warning("unavailable／待交付：" + info.reason)
    st.info("本階段僅提供導航、獨立工作區與接點；沒有隱藏 Mock 或正式模擬結果。")
    if mode == "testline":
        st.caption("後續：fccl-testline-experiment-simulation｜模擬批次、參數事件、MD 追蹤、延後品質量測與獨立 SPC。")
        st.button("投入模擬測試批次", disabled=True, key="testline_start_unavailable")
    else:
        st.caption("後續：fccl-production-disturbance-compensation｜厚度／張力／雷射雜訊、訊號可信度及人工線速補償。")
        st.button("確認模擬線速補償", disabled=True, key="production_confirm_unavailable")
    st.caption("資料來源：unavailable · 模型結果：unavailable · SPC：無獨立有效基準，無法判定 · Alarm：尚無可判定資料。")
    st.caption("未來輸出須標示 Synthetic／Mock；不保證線速調整改善品質，不控制真實設備，不回寫 generated_data/v2。")
