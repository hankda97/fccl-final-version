"""AI chart controls; calculations and source state live outside the UI."""

import streamlit as st
from c_dashboard.workspace_modes.state import widget_key

from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS
from c_dashboard.visualization.charts import heatmap_records, heatmap_spec
from c_dashboard.visualization.config import SHAP_KINDS, TEST_NOTICE, label
from c_dashboard.visualization.controller import heatmap_for, reconcile_features, explanation_for, key_for
from c_dashboard.adapters.explanations import UnavailableExplanationProvider
from c_dashboard.visualization.sources import label_eligibility
from c_dashboard.visualization.heatmap import eligible_rows, numeric_values


def render_visualization_panel(workspace, rows, adapter, provider=None):
    state = workspace.visualization
    st.subheader("Heatmap")
    st.caption("目前 CSV／明確投影的觀測 Pearson 相關；相關性不代表因果，Mock／合成分析不代表真實產線結論。")
    if reconcile_features(state, rows):
        st.info("新資料缺少部分先前特徵，已移除無效的 Heatmap 選項。")
    token = f"{workspace.data.source_id or 'empty'}_{state.generation}"
    features = tuple(st.multiselect(
        "Heatmap 製程／環境特徵", tuple(name for name in FEATURE_UNITS if name in rows),
        default=state.heatmap_features, format_func=label, disabled=workspace.data.dataset is None,
        key=widget_key(workspace, f"ui_heatmap_features_{token}")))
    if workspace.data.dataset is not None:
        state.heatmap_features = features
    state.heatmap_targets = tuple(st.multiselect(
        "Heatmap 實測品質目標", tuple(TARGET_UNITS), default=state.heatmap_targets,
        format_func=label, disabled=workspace.data.dataset is None, key=widget_key(workspace, f"ui_heatmap_targets_{token}")))
    retry_heatmap = st.button("重新計算 Heatmap", key=widget_key(workspace, "ui_heatmap_retry"), disabled=workspace.data.dataset is None)
    with st.spinner("Heatmap 計算中…"):
        slot = heatmap_for(workspace, rows, retry=retry_heatmap)
    if slot.status == "ready":
        result = slot.result
        source = result.source
        _render_source(source)
        st.caption(f"來源 {source.source_kind} · {source.source_id} · 映射 {source.mapping_version} · 批號 {source.batch or '全部'}")
        st.caption(f"範圍 {source.time_start or '起點'} ～ {source.time_end or '終點'} · 觀測截止 {source.cutoff or '無'} · {result.method} · 設定 {result.version}")
        st.caption(f"總列 {result.total_rows}，有效識別列 {result.eligible_rows}，排除識別／重複 {result.excluded_identity}；每格 n 為有效配對資料列，非獨立製程條件數。最低 {result.minimum_pairs} 為 C 顯示設定，不是正式採樣規則。")
        try:
            st.vega_lite_chart(spec=heatmap_spec(result), width="stretch", key=widget_key(workspace, "ui_heatmap_chart"))
        except Exception as exc:
            slot.status, slot.result, slot.reason = "error", None, f"Heatmap 繪圖錯誤：{exc}"
            st.error(slot.reason)
        with st.expander("Heatmap 有效配對與不可計算原因"):
            st.dataframe(heatmap_records(result), hide_index=True, width="stretch")
        valid = eligible_rows(rows)
        status_rows = []
        for target in TARGET_UNITS:
            mask, exclusions = label_eligibility(valid, target, source.profile)
            count = int((mask & numeric_values(valid, target).notna()).sum()) if target in valid else 0
            status_rows.append({"品質目標": label(target), "可用觀測標籤數": count,
                "觀測限制": "；".join(code for code, _ in exclusions) or ("缺少目標欄位" if target not in valid else "依來源 profile"),
                "模型目標能力": "已宣告支援" if target in adapter.describe().supports_targets else "未宣告／不可用"})
        st.dataframe(status_rows, hide_index=True, width="stretch")
        st.caption("標籤 availability、模型預測能力及 SHAP 解釋能力分開；有標籤不等於模型已就緒，缺標籤也不直接阻止有效模型解釋。")
    else:
        (st.error if slot.status == "error" else st.info)(slot.reason or "Heatmap 尚無可用資料。")
    _render_shap_controls(workspace, rows, adapter, provider or UnavailableExplanationProvider())


def _render_shap_controls(workspace, rows, adapter, provider):
    state = workspace.visualization
    st.subheader("SHAP Summary Plot")
    st.subheader("SHAP Dependence Plot")
    state.shap_kind = st.radio("SHAP 圖型", SHAP_KINDS, index=SHAP_KINDS.index(state.shap_kind),
                               key=widget_key(workspace, "ui_shap_kind"))
    state.shap_target = st.selectbox("SHAP 品質目標", tuple(TARGET_UNITS),
        index=tuple(TARGET_UNITS).index(state.shap_target), format_func=label, key=widget_key(workspace, "ui_shap_target"))
    try:
        info = provider.describe()
        declared = info.feature_names
        choices = declared if (declared and len(set(declared)) == len(declared)
                               and all(isinstance(name, str) for name in declared)) else tuple(FEATURE_UNITS)
        units = dict(zip(info.feature_names, info.feature_units))
    except Exception:
        info, choices, units = None, tuple(FEATURE_UNITS), {}
    if state.shap_feature not in choices:
        state.shap_feature = choices[0]
    state.shap_feature = st.selectbox("SHAP Dependence 特徵", choices,
        index=choices.index(state.shap_feature),
        format_func=lambda name: label(name) if name in FEATURE_UNITS else f"{name} [{units.get(name, '單位待提供')}]",
        key=widget_key(workspace, f"ui_shap_feature_{key_for(choices, state.generation)[:12]}"))
    retry = st.button("重新取得 SHAP 解釋", key=widget_key(workspace, "ui_shap_retry"),
        disabled=workspace.data.dataset is None or not adapter.describe().supports_shap)
    st.caption(f"模型來源 {adapter.describe().source} · 版本 {adapter.describe().version} · supports_shap={adapter.describe().supports_shap}")
    if info:
        st.caption(f"解釋來源 {info.source} · 版本 {info.explanation_version or '尚未交付'} · schema {info.schema_version}")
        if info.manifest:
            m = info.manifest
            st.caption(f"Manifest {m.manifest_id} · model type {m.model_type} · schema {m.schema_version} · features {m.feature_version} · labels {m.label_version} · specs {m.spec_version} · 訓練資料 {m.dataset_version}")
    with st.spinner("SHAP 圖表計算中…"):
        slot = explanation_for(workspace, rows, adapter, provider, retry=retry)
    if slot.status != "ready":
        (st.error if slot.status == "error" else st.info)(f"SHAP {slot.status}：{slot.reason}")
        return
    rendered = slot.result
    request = rendered.request
    _render_source(request.source)
    if request.info.source_kind == "render-test":
        st.warning(TEST_NOTICE)
    st.caption(f"{request.kind} · 目標 {label(request.target)} · 輸出 {request.output_scale} [{request.output_unit}] · 背景 {request.info.background_source}")
    st.caption(f"資料來源 {request.source.source_id} · 批號 {request.source.batch or '全部'} · 範圍 {request.source.time_start or '起點'} ～ {request.source.time_end or '終點'} · 截止 {request.source.cutoff} · 使用 {len(request.sample_ids)} 列，排除 {request.excluded_rows} 列 · 未抽樣")
    st.caption(f"模型 {request.info.model_version} · 前處理 {request.info.preprocessing_version} · 解釋 {request.info.explanation_version} · 請求 {request.request_key[:16]}")
    try:
        if rendered.spec is not None:
            st.vega_lite_chart(spec=rendered.spec, width="stretch", key=widget_key(workspace, "ui_shap_chart"))
        else:
            st.image(rendered.png, caption=request.kind + (f" · {TEST_NOTICE}" if request.info.source_kind == "render-test" else ""))
    except Exception as exc:
        slot.status, slot.result, slot.reason = "error", None, f"SHAP 嵌入錯誤：{exc}"
        st.error(slot.reason)


def _render_source(source):
    profile = source.profile
    st.caption(f"分析來源 profile {profile.kind}／{profile.version} · dataset {profile.dataset_version} · schema {profile.schema_version} · alignment {profile.alignment_version} · labels {profile.label_version} · specs {profile.spec_version}")
    if profile.kind in {"c-mock", "synthetic-ground-truth"}:
        st.caption("合成／Mock 示範資料，非真實產線量測；合成真值不與抽檢資料混算。")
    elif profile.kind == "legacy-csv":
        st.caption("C 單 CSV 相容顯示；正式來源／標籤有效性未驗證。")
    elif profile.kind == "unresolved":
        st.warning("正式來源投影尚未交付／跨組待確認；不繞過 availability，A／B 七表整合留 C9。")
    if source.context:
        st.caption("來源追溯（材料 MD 為 [start,end)）：" + " · ".join(f"{k}={v}" for k, v in source.context))
