"""Streamlit controls for the isolated, fixed-segment What-if workflow."""

import streamlit as st
from c_dashboard.workspace_modes.state import widget_key

from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.quality.config import PARAMETER_CONTROLS, TARGET_LABELS, parameter_bounds
from c_dashboard.quality.controller import evaluate_what_if, select_what_if_segment, what_if_alarms
from c_dashboard.quality.types import Recommendation, WhatIfComparison
from c_dashboard.state import SegmentSnapshot, WorkspaceState


def render_whatif_panel(workspace: WorkspaceState, options: list[SegmentSnapshot], adapter, readiness=None) -> None:
    st.subheader("What-if 參數比較")
    st.caption(f"{adapter.describe().source} 的預測與建議僅供決策輔助；不代表真實 FCCL 製程因果效果、已驗證改善或機台控制。")
    if readiness is not None:
        if readiness.ready:
            st.success("What-if 已就緒：" + readiness.reason)
        else:
            st.warning("What-if 尚未就緒：" + readiness.reason)
            st.info("下一步：" + readiness.next_step)
            _render_recommendation(None)
            return
    if workspace.what_if.requires_reselect:
        st.warning("原 What-if 比較基準已失效；需主動選取目前可見區段。舊參數、預測與建議不再顯示。")
    if not options:
        st.warning("目前篩選資料沒有可用的批號／材料區段識別，無法建立 What-if 比較。")
        _render_recommendation(None)
        return

    use_stable_selector = workspace.replay.mode == "replay" or workspace.what_if.requires_reselect
    if use_stable_selector:
        # Stable IDs, not mutable feature snapshots, are widget choices during playback.
        by_id = {f"{s.batch_id}|{s.segment_id}|{s.sample_id}": s for s in options}
        prior = workspace.what_if.selected
        matching = [key for key, value in by_id.items() if prior and value.sample_id == prior.sample_id]
        chosen = st.selectbox("選擇目前已可見區段", list(by_id),
                              index=list(by_id).index(matching[0]) if matching else len(by_id)-1,
                              format_func=lambda k: _snapshot_label(by_id[k]),
                              key=widget_key(workspace, f"ui_replay_segment_{workspace.replay.generation}"))
        if st.button("選定／更新比較基準", key=widget_key(workspace, "ui_reselect_whatif")):
            select_what_if_segment(workspace, by_id[chosen], force=True)
        if workspace.what_if.requires_reselect:
            st.button("調參控制停用：請先選定可見區段", disabled=True)
            return
        selected = workspace.what_if.selected or options[-1]
    else:
        selected = workspace.what_if.selected or options[-1]
    current = selected if use_stable_selector else st.selectbox(
        "選擇已載入／目前可見的比較區段", options,
        index=options.index(selected) if selected in options else len(options) - 1,
        format_func=_snapshot_label,
        key=widget_key(workspace, f"ui_whatif_segment_{_source_token(selected)}_r{workspace.what_if.parameter_revision}"),
    )
    if current != workspace.what_if.selected:
        select_what_if_segment(workspace, current)
        selected = current
    st.info(f"固定比較基準：批號 {selected.batch_id} · 材料區段 {selected.segment_id} · {selected.timestamp}")
    st.caption(f"卷別：{selected.root_roll_id or '未提供'} · 材料 MD：[ {selected.material_md_start or '未提供'}, {selected.material_md_end or '未提供'} ) m；不推定正式材料對齊。")

    features = dict(selected.process_settings)
    token = _widget_token(selected) + (f"_g{workspace.replay.generation}_r{workspace.what_if.parameter_revision}" if workspace.replay.mode == "replay" else "")
    speed = features.get("line_speed_m_min")
    if speed is None:
        st.warning("此區段缺少線速原始值；線速滑桿停用，請檢查資料欄位。")
    else:
        low, high, step = parameter_bounds("line_speed_m_min", speed)
        adjusted_speed = st.slider(
            f"線速（m/min）· 示範範圍 {low:g}–{high:g}", min_value=low, max_value=high,
            value=min(high, max(low, workspace.what_if.parameters.get("line_speed_m_min", speed))),
            step=step, key=widget_key(workspace, f"ui_whatif_speed_{token}"), disabled=not selected.sample_id,
        )
        _set_parameter(workspace, "line_speed_m_min", speed, adjusted_speed)

    if st.button(
        "鎖定熟化與壓合參數" if workspace.what_if.advanced_unlocked else "解鎖熟化與壓合參數（僅模擬）",
        key=widget_key(workspace, f"ui_whatif_advanced_toggle_{token}"), disabled=not selected.sample_id,
    ):
        if workspace.what_if.advanced_unlocked:
            for name, control in PARAMETER_CONTROLS.items():
                if control.advanced:
                    workspace.what_if.parameters.pop(name, None)
        workspace.what_if.advanced_unlocked = not workspace.what_if.advanced_unlocked
        workspace.what_if.parameter_revision += 1
        workspace.what_if.result_key = None
        st.rerun()

    if workspace.what_if.advanced_unlocked:
        st.warning("進階參數僅供 What-if 模擬，不會控制機台或改寫實測資料。")
        for parameter, control in PARAMETER_CONTROLS.items():
            if not control.advanced:
                continue
            baseline = features.get(parameter)
            if baseline is None:
                st.caption(f"{parameter} 缺少原始值，無法調整。")
                continue
            low, high, step = parameter_bounds(parameter, baseline)
            adjusted = st.slider(
                f"{_parameter_label(parameter)}（{control.unit}）· 示範範圍 {low:g}–{high:g}",
                min_value=low, max_value=high,
                value=min(high, max(low, workspace.what_if.parameters.get(parameter, baseline))),
                step=step, key=widget_key(workspace, f"ui_whatif_{parameter}_{token}_r{workspace.what_if.parameter_revision}"),
            )
            _set_parameter(workspace, parameter, baseline, adjusted)

    comparison, recommendation = evaluate_what_if(workspace, adapter)
    _render_comparison(comparison)
    alarms, indeterminate = what_if_alarms(workspace, comparison)
    st.markdown("**固定 What-if 情境風險（獨立於目前監控與 SPC）**")
    for alarm in alarms:
        st.error(f"AI Alarm｜固定 What-if 情境｜{TARGET_LABELS.get(alarm.target, alarm.target)} {alarm.condition}：{alarm.value:g}（{alarm.threshold}）· {alarm.batch_id}/{alarm.segment_id} · {alarm.timestamp}")
    if not alarms:
        st.caption("固定情境沒有觸發已配置的示範風險條件；缺少條件時請查看無法判定提示。")
    if indeterminate:
        st.caption("What-if 風險無法判定：" + "；".join(indeterminate))
    _render_recommendation(recommendation)


def _set_parameter(workspace, name, baseline, value):
    value = float(value)
    low, high, _ = parameter_bounds(name, float(baseline))
    if not low <= value <= high:
        st.error(f"{name} 超出目前版本的示範操作範圍。")
        return
    if value == float(baseline):
        workspace.what_if.parameters.pop(name, None)
    else:
        workspace.what_if.parameters[name] = value
    workspace.what_if.editing_started = bool(workspace.what_if.parameters)


def _render_comparison(comparison: WhatIfComparison | None) -> None:
    st.subheader("調整前後品質預測")
    if comparison is None:
        st.info("選取有效區段後顯示預測比較。")
        return
    st.caption(f"Adapter：{comparison.adapter_source} · 版本：{comparison.adapter_version or '—'} · Synthetic／Mock 決策輔助")
    if comparison.unavailable_reason:
        st.warning("目前無法比較預測：" + comparison.unavailable_reason)
    if comparison.before is None or comparison.after is None:
        return
    rows = []
    for target, unit in TARGET_UNITS.items():
        before = comparison.before.targets.get(target)
        after = comparison.after.targets.get(target)
        if before is None or after is None:
            reason = (comparison.after.unavailable_targets or {}).get(target, "Adapter 未提供此目標")
            rows.append({"品質目標": TARGET_LABELS[target], "調整前": "—", "調整後": "—", "差值": "—", "狀態": reason})
            continue
        delta = float(after) - float(before)
        rows.append({"品質目標": TARGET_LABELS[target], "調整前": f"{before} {unit}",
                     "調整後": f"{after} {unit}", "差值": f"{delta:+g} {unit}", "狀態": "模型情境預測"})
    st.dataframe(rows, hide_index=True, width="stretch")
    if comparison.after.appearance_ng_risk is not None:
        formal = "Synthetic 正式模型 artifact" in comparison.adapter_source
        label = "外觀 NG 模型機率" if formal else "外觀 NG 示範風險分數"
        suffix = "Synthetic 模型；非真實產線校準" if formal else "未校準機率"
        st.caption(f"{label}：{comparison.before.appearance_ng_risk:.3f} → {comparison.after.appearance_ng_risk:.3f}（{suffix}）")


def _render_recommendation(recommendation: Recommendation | None) -> None:
    st.subheader("具體調參建議")
    if recommendation is None:
        st.info("尚無建議結果。")
    elif recommendation.status == "suggested":
        sign = "+" if recommendation.delta is not None and recommendation.delta > 0 else ""
        st.success(f"示範候選：{_parameter_label(recommendation.parameter)} {sign}{recommendation.delta:g} {recommendation.unit}；"
                   f"{TARGET_LABELS.get(recommendation.focus_target, recommendation.focus_target)}："
                   f"{recommendation.before_value:g} → {recommendation.after_value:g}。")
        st.caption(recommendation.reason + f" · 策略版本 {recommendation.policy_version}")
    else:
        st.info(f"目前無可用建議（{recommendation.status}）：{recommendation.reason}")
    st.caption("線速 −0.2 m/min 僅為可配置測試候選；不是正式推薦政策或真實改善保證。")


def _snapshot_label(snapshot):
    return f"{snapshot.batch_id} · {snapshot.segment_id} · {snapshot.timestamp}"


def _widget_token(snapshot):
    import hashlib
    return hashlib.sha1(f"{snapshot.source_id}|{snapshot.sample_id}".encode()).hexdigest()[:12]


def _source_token(snapshot):
    import hashlib
    return hashlib.sha1(snapshot.source_id.encode()).hexdigest()[:12]


def _parameter_label(parameter):
    labels = {
        "line_speed_m_min": "線速", "curing_temp_c": "熟化溫度",
        "curing_time_min": "熟化時間", "lamination_temp_c": "壓合溫度",
        "lamination_pressure_mpa": "壓合壓力", "lamination_time_s": "壓合時間",
    }
    return labels.get(parameter, str(parameter))
