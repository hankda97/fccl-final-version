"""Persistent monitoring header and honest not-yet-available states."""

import streamlit as st
from c_dashboard.ui.replay_controls import render_replay_controls

from c_dashboard.adapters.base import AdapterInfo
from c_dashboard.quality.config import TARGET_LABELS
from c_dashboard.quality.types import PredictionAlarm, PredictionView
from c_dashboard.state import WorkspaceState
from c_dashboard.ui.spc_alarm import render_spc_events, render_spc_status


def render_overview(workspace: WorkspaceState, adapter_info: AdapterInfo, spc_result,
                    prediction: PredictionView | None = None,
                    prediction_alarms: tuple[PredictionAlarm, ...] = (),
                    prediction_indeterminate: tuple[str, ...] = ()) -> None:
    st.subheader("監控摘要")
    labels = (
        "抗剝離度（N/mm）",
        "尺寸安定性 MD（%）",
        "尺寸安定性 TD（%）",
        "耐熱度（°C）",
        "外觀 NG 風險",
    )
    for index, (column, label) in enumerate(zip(st.columns(5), labels)):
        group = spc_result.targets[index].latest if index < 4 else None
        if index < 4:
            column.metric(label, f"{group.mean:.6g}" if group and group.valid else "—")
        else:
            risk = prediction.record.appearance_ng_risk if prediction and prediction.record else None
            column.metric(label, f"{risk:.3f}" if risk is not None else "—")
        if group and group.valid:
            column.caption(f"實測子組平均 · n={group.n} · {group.completed_at}")
    if prediction:
        st.caption(f"模型預測只對應目前可見資料：{prediction.batch_id} · {prediction.segment_id} · {prediction.timestamp} · {adapter_info.source}")
    else:
        st.caption("尚無可用的目前可見資料預測。")
    st.caption("前四項是實測 SPC 子組均值；外觀欄為 Mock 未校準風險分數。所有模型結果僅供功能示範。")
    with st.container(border=True):
        st.subheader("AI Alarm")
        render_spc_status(spc_result)
        render_spc_events(spc_result)
        st.markdown("**AI 預測 Alarm（與 SPC Alarm 分離）**")
        if prediction_alarms:
            for alarm in prediction_alarms:
                st.error(f"AI Alarm｜{TARGET_LABELS.get(alarm.target, alarm.target)} {alarm.condition}：{alarm.value:g}（{alarm.threshold}）· {alarm.batch_id}/{alarm.segment_id} · {alarm.scenario}")
        else:
            st.info("目前沒有可顯示的 Mock 預測 Alarm；下方會列出無法判定的目標。")
        if prediction_indeterminate:
            st.caption("無法判定（未設定正式規格，僅顯示示範狀態）：" + "；".join(prediction_indeterminate))
        st.caption(adapter_info.message + " 正式 Random Forest 模型尚未接入。")
