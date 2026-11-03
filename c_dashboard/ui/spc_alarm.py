"""Measured SPC alarm renderer, independent of model availability."""

import streamlit as st

from c_dashboard.spc.rules import RULE_LABELS
from c_dashboard.spc.messages import format_reasons
from c_dashboard.spc.incidents import group_spc_incidents

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


def incident_message(incident):
    rules = "、".join(RULE_LABELS.get(rule, rule) for rule in incident.rules)
    state = "目前仍在發生" if incident.active else "歷史事件已結束"
    return (f"{TARGET_LABELS[incident.target]} · {state} · {incident.batch} · {rules} · "
            f"{incident.first_subgroup} → {incident.latest_subgroup} · "
            f"{incident.subgroup_count} 個子組／{incident.event_count} 筆規則事件 · "
            f"最近 {incident.latest_at}")


def render_spc_summary(result):
    """Bounded overview; detailed raw events belong only to the SPC tab."""
    incidents = group_spc_incidents(result)
    active = tuple(item for item in incidents if item.active)
    affected = tuple(dict.fromkeys(item.target for item in incidents))
    if not incidents:
        st.info("目前範圍未偵測 SPC 事件；不代表產品合格。")
        return
    st.caption(
        f"SPC Alarm 摘要：目前事件群 {len(active)}，歷史事件群 {len(incidents) - len(active)}，"
        f"原始規則事件 {len(result.events)}；完整明細請至 SPC 監控分頁。"
    )
    st.caption("影響目標：" + "、".join(TARGET_LABELS[target] for target in affected))
    for incident in active:
        st.error("實測 SPC Alarm · " + incident_message(incident))
    latest_by_target = {}
    for incident in incidents:
        latest_by_target[incident.target] = incident
    historical = [item for item in latest_by_target.values() if not item.active]
    if historical:
        st.warning("最近歷史事件：" + "；".join(incident_message(item) for item in historical))


def render_spc_status(result):
    if result.cutoff is None:
        st.info("尚未判定：尚無已載入觀測或篩選結果為空。")
    for target in result.targets:
        message = f"{TARGET_LABELS[target.target]}：{target.status}"
        if target.status == "無法判定 SPC 狀態":
            st.warning(message + " · " + format_reasons(target.reasons))
        else:
            st.caption(message)
