"""Source-aware model prediction and measured-SPC monitoring summary."""

import streamlit as st
from c_dashboard.adapters.base import AdapterInfo
from c_dashboard.quality.config import TARGET_LABELS
from c_dashboard.quality.types import PredictionAlarm, PredictionView
from c_dashboard.state import WorkspaceState
from c_dashboard.ui.spc_alarm import render_spc_summary, render_spc_status


def render_overview(workspace: WorkspaceState, adapter_info: AdapterInfo, spc_result,
                    prediction: PredictionView | None = None,
                    prediction_alarms: tuple[PredictionAlarm, ...] = (),
                    prediction_indeterminate: tuple[str, ...] = ()) -> None:
    st.subheader("監控摘要")
    st.markdown("#### 目前區段模型預測")
    target_names = (
        "peel_strength_n_mm", "dimensional_stability_md_pct",
        "dimensional_stability_td_pct", "heat_resistance_c", "appearance_ng",
    )
    labels = tuple(TARGET_LABELS[name] for name in target_names)
    record = prediction.record if prediction else None
    for name, column, label in zip(target_names, st.columns(5), labels):
        value = record.targets.get(name) if record else None
        if name == "appearance_ng":
            risk = record.appearance_ng_risk if record else None
            shown = "—" if value is None else ("NG" if int(value) == 1 else "OK")
            if risk is not None:
                shown += f" · 風險 {risk:.3f}"
        else:
            shown = f"{float(value):.6g}" if value is not None else "—"
        column.metric(label, shown)
        if record and record.unavailable_targets and name in record.unavailable_targets:
            column.caption("不可用：" + record.unavailable_targets[name])
    if prediction:
        st.caption(f"模型預測只對應目前可見資料：{prediction.batch_id} · {prediction.segment_id} · "
                   f"{prediction.timestamp} · {adapter_info.source} · 版本 {adapter_info.version or '未提供'}")
    else:
        st.caption("尚無可用的目前可見資料預測。")
    st.caption(adapter_info.message)

    st.markdown("#### 實測 SPC 最新子組")
    for column, target in zip(st.columns(4), spc_result.targets):
        group = target.latest
        column.metric(TARGET_LABELS.get(target.target, target.target),
                      f"{group.mean:.6g}" if group and group.valid else "—")
        if group and group.valid:
            column.caption(f"實測子組平均 · n={group.n} · {group.completed_at}")
        else:
            column.caption(target.status)
    if spc_result.baseline:
        st.caption(f"SPC 基準：{spc_result.baseline.source} · 版本 {spc_result.baseline.version}")
    else:
        st.caption("SPC 基準：目前無可用的穩定歷史基準。")


def render_alarm_summary(adapter_info: AdapterInfo, spc_result,
                         prediction: PredictionView | None = None,
                         prediction_alarms: tuple[PredictionAlarm, ...] = (),
                         prediction_indeterminate: tuple[str, ...] = ()) -> None:
    """Render the bounded alarm summary after the primary navigation tabs."""
    record = prediction.record if prediction else None
    with st.container(border=True):
        st.subheader("AI Alarm")
        render_spc_status(spc_result)
        render_spc_summary(spc_result)
        st.markdown("**AI 預測 Alarm（與 SPC Alarm 分離）**")
        if prediction_alarms:
            for alarm in prediction_alarms:
                st.error(f"AI Alarm｜{TARGET_LABELS.get(alarm.target, alarm.target)} {alarm.condition}：{alarm.value:g}（{alarm.threshold}）· {alarm.batch_id}/{alarm.segment_id} · {alarm.scenario}")
        else:
            message = "目前模型預測未觸發 Alarm。" if record else "目前沒有可用的模型預測 Alarm。"
            st.info(message)
        if prediction_indeterminate:
            st.caption("無法判定（未設定正式規格，僅顯示示範狀態）：" + "；".join(prediction_indeterminate))
        st.caption(f"模型來源：{adapter_info.source} · 版本 {adapter_info.version or '未提供'} · {adapter_info.message}")
