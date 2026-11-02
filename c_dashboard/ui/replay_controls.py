"""One playback timer and UI commands, kept outside calculation services."""
import json
import time
import streamlit as st
from c_dashboard.workspace_modes.state import widget_key
from c_dashboard.replay.controller import (
    timeline_for, snapshot_for, set_mode, operate, set_temporal_config,
)
from c_dashboard.replay.service import tick


def render_replay_controls(workspace):
    st.subheader("監控工作區")
    def change_mode():
        set_mode(workspace, "replay" if st.session_state[widget_key(workspace, "ui_mode_placeholder")] == "CSV 定時回放" else "snapshot")
    st.radio("監控模式", ["CSV 快照", "CSV 定時回放"], horizontal=True,
             index=int(workspace.replay.mode == "replay"), disabled=workspace.data.dataset is None,
             key=widget_key(workspace, "ui_mode_placeholder"), on_change=change_mode)
    timeline = timeline_for(workspace)
    enabled = workspace.replay.mode == "replay" and bool(timeline.groups)
    controls = st.columns(4)
    def invoke(action):
        operate(workspace, action, time.monotonic())
    for col, label, key, action in zip(controls, ("播放／暫停", "單步前進", "重新開始"),
            ("ui_play_placeholder", "ui_step_placeholder", "ui_restart_placeholder"),
            ("pause" if workspace.replay.playing else "play", "step", "restart")):
        col.button(label, key=widget_key(workspace, key), disabled=not enabled, width="stretch",
                   on_click=invoke, args=(action,))
    def change_speed():
        operate(workspace, "speed", time.monotonic(), speed=float(st.session_state[widget_key(workspace, "ui_speed_placeholder")][:-1]))
    controls[3].selectbox("回放速度", ["0.5x", "1x", "2x", "4x"],
                          index=[.5, 1., 2., 4.].index(workspace.replay.speed),
                          key=widget_key(workspace, "ui_speed_placeholder"), disabled=not enabled, on_change=change_speed)
    st.caption("回放倍率僅控制歷史播放時間，不是製程線速（m/min）；不控制設備。")
    if workspace.replay.mode == "replay":
        s = snapshot_for(workspace)
        status = "完成" if enabled and s.cursor == s.total_groups else "播放中" if workspace.replay.playing else "暫停"
        st.caption(f"回放時間：{s.cutoff or '尚未播放'} · {status}")
        st.caption(f"已釋出 {s.played_rows}／{s.total_rows} 列 · 事件群 {s.cursor}／{s.total_groups}")
        st.progress(s.cursor / s.total_groups if s.total_groups else 0.)
        st.caption(f"材料選取時間窗：{workspace.data.time_start or '全部'} ～ {workspace.data.time_end or '全部'}")
        if timeline.groups:
            st.caption(f"可信可得時間軸：{timeline.groups[0][0].available_at} ～ {timeline.groups[-1][0].available_at}")
        st.caption(f"時間設定：{timeline.profile.version if timeline.profile else '未提供'}；來源：{timeline.profile.source if timeline.profile else '待 A／B 確認'}")
        if s.reasons:
            # Do not expose row-level future validation outcomes; diagnostics explain capability only.
            st.warning("部分欄位無可靠可得時間或歷史證據，相關通道不可回放；其他可信通道仍可使用。")
            with st.expander("目前可見的時間／目標限制"):
                for reason in s.reasons[:100]:
                    st.caption(reason)
        if not timeline.groups:
            st.warning("沒有可信可回放事件。請檢查時間 profile；可切回快照檢查資料，不以推測時間替代。")


def render_temporal_config(workspace):
    with st.expander("歷史時間映射（C 來源轉接設定）"):
        st.caption("正式來源須明確提供時間角色；不以 timestamp／檢驗 completed_at 猜發布時間。C Mock 有獨立示範設定。")
        with st.form(widget_key(workspace, "ui_temporal_form")):
            value = st.text_area("時間 profile JSON（空白恢復來源預設）", key=widget_key(workspace, "ui_temporal_json"))
            submitted = st.form_submit_button("套用時間設定", key=widget_key(workspace, "ui_temporal_apply"), disabled=workspace.data.dataset is None)
        if submitted:
            try:
                set_temporal_config(workspace, json.loads(value) if value.strip() else None)
                st.success("已套用時間設定：" + (workspace.data.temporal_config or {}).get("version", "來源預設"))
            except (ValueError, TypeError, KeyError) as exc:
                st.error(f"時間設定未套用：{exc}")


def render_replay_timer(workspace):
    # Only this fragment drives elapsed time. Other reruns merely render current state.
    state = workspace.replay
    expected_generation, lifecycle = state.generation, state.lifecycle_token
    @st.fragment(run_every=.25 if workspace.replay.playing else None)
    def timer():
        if workspace.replay is state and state.mode == "replay" and state.playing:
            if tick(state, timeline_for(workspace), time.monotonic(), expected_generation,
                    lifecycle_token=lifecycle):
                st.rerun()
    timer()
