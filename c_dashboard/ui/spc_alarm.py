"""Measured SPC alarm renderer, independent of model availability."""

import streamlit as st

from c_dashboard.spc.rules import RULE_LABELS

TARGET_LABELS = {
    "peel_strength_n_mm": "抗剝離度", "dimensional_stability_md_pct": "尺寸安定性 MD",
    "dimensional_stability_td_pct": "尺寸安定性 TD", "heat_resistance_c": "耐熱度",
}


def event_message(event):
    return (f"實測 SPC Alarm · {TARGET_LABELS[event.target]} · {RULE_LABELS[event.rule]} · "
            f"{event.batch}/{event.segment}/{event.subgroup} · {event.triggered_at} · "
            f"均值 {event.value:.8g} · CL={event.cl:.8g} UCL={event.ucl:.8g} LCL={event.lcl:.8g} · "
            f"來源 {event.source_id} · ID {event.event_id}")


def render_spc_events(result):
    if result.events:
        st.caption("以下為目前篩選範圍內的實測歷史事件；不代表每個事件都是最新子組狀態。")
        for event in result.events:
            st.error(event_message(event))
    else:
        st.info("目前範圍無已偵測的實測 SPC 事件；請同時查看各目標的可判定狀態。")


def render_spc_status(result):
    if result.cutoff is None:
        st.info("尚未判定：尚無已載入觀測或篩選結果為空。")
    for target in result.targets:
        message = f"{TARGET_LABELS[target.target]}：{target.status}"
        if target.status == "無法判定 SPC 狀態":
            st.warning(message + " · " + "；".join(target.reasons))
        else:
            st.caption(message)
