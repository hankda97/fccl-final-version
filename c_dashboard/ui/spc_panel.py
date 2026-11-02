"""X-bar and raw observations in one native Vega-Lite chart."""

from dataclasses import asdict

import pandas as pd
import streamlit as st

from c_dashboard.ui.spc_alarm import TARGET_LABELS, render_spc_events
from c_dashboard.workspace_modes.state import widget_key


def chart_spec(result, target_name):
    """Pure chart payload for explicit measured result, independently testable."""
    target = result.target(target_name)
    raw = [{"time": r.timestamp, "value": r.value, "series": "原始量測", "batch": r.batch,
            "source_row": r.source_row} for r in result.raw if r.target == target_name]
    means, segment = [], 0
    for group in target.groups:
        if group.break_before or not group.valid:
            segment += 1
        if group.valid and group.completed_at:
            means.append({"time": group.completed_at, "value": group.mean, "series": "子組均值",
                          "line_segment": str(segment), "batch": group.batch,
                          "subgroup": group.subgroup, "n": group.n})
    y = {"field": "value", "type": "quantitative", "title": target.unit, "scale": {"zero": False}}
    x = {"field": "time", "type": "temporal", "title": "量測／子組完成時間"}
    layers = [
        {"data": {"values": raw}, "mark": {"type": "point", "opacity": .35, "color": "#8895a7"},
         "encoding": {"x": x, "y": y, "tooltip": [{"field": "series"}, {"field": "value"},
                       {"field": "batch"}, {"field": "source_row"}]}},
        {"data": {"values": means}, "mark": {"type": "line", "point": True, "color": "#2471a3"},
         "encoding": {"x": x, "y": y, "detail": {"field": "line_segment"},
                      "tooltip": [{"field": "series"}, {"field": "subgroup"}, {"field": "value"}, {"field": "n"}]}},
    ]
    if target.baseline and target.baseline.valid and any(g.valid for g in target.groups):
        b = target.baseline
        for name, value, color in (("CL", b.cl, "#228844"), ("UCL", b.ucl, "#bb3333"), ("LCL", b.lcl, "#bb3333")):
            layers.append({"data": {"values": [{"value": value, "series": name}]},
                           "mark": {"type": "rule", "color": color, "strokeDash": [5, 3]},
                           "encoding": {"y": y, "tooltip": [{"field": "series"}, {"field": "value"}]}})
    alarms = [{"time": e.triggered_at, "value": e.value, "rule": e.rule, "id": e.event_id}
              for e in result.events if e.target == target_name]
    layers.append({"data": {"values": alarms}, "mark": {"type": "point", "color": "red", "size": 120},
                   "encoding": {"x": x, "y": y, "tooltip": [{"field": "rule"}, {"field": "value"}, {"field": "id"}]}})
    return {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "height": 320,
            "title": f"{TARGET_LABELS[target_name]} X-bar（實測）", "layer": layers}


def render_spc_panel(result, workspace=None):
    st.subheader("X-bar 管制圖")
    choice = st.selectbox("SPC 品質目標", tuple(TARGET_LABELS), format_func=TARGET_LABELS.get, key=widget_key(workspace, "ui_spc_target"))
    target = result.target(choice)
    st.caption(f"實測來源 {result.source_id} · 截止 {result.cutoff or '尚無資料'} · 規則 {result.rule_version}")
    st.caption("灰點為原始試片量測，藍線為子組均值；管制界限用於均值，不能據此判定個別試片允收。")
    if result.raw:
        st.vega_lite_chart(spec=chart_spec(result, choice), width="stretch", key=widget_key(workspace, "ui_spc_chart"))
    else:
        st.info("無可顯示的實測資料；無法判定 SPC 狀態。")
    if target.baseline and target.baseline.valid and any(g.valid for g in target.groups):
        b = target.baseline
        st.text(f"CL={b.cl:.10g}　UCL={b.ucl:.10g}　LCL={b.lcl:.10g}（{target.unit}）")
    st.write(f"目前狀態：{target.status}")
    if target.reasons:
        st.warning("；".join(target.reasons))
    if not any(g.valid for g in target.groups):
        st.info("目前沒有完整有效子組，不顯示有效管制界限。")
    if result.baseline:
        b = result.baseline
        st.caption(f"{b.source} · 基準版本 {b.version} · n={b.n} · 目標歷史組數 {b.target(choice).groups}")
        with st.expander("SPC 基準來源與適用條件"):
            st.json({"來源": b.source, "歷史內容指紋": b.history_hash, "版本": b.version,
                     "時間窗": [b.start, b.end], "固定監控起點": b.origin,
                     "產品": b.product, "配方": b.recipe, "子組大小": b.n,
                     "條件": dict(b.conditions), "目標": choice, "單位": target.unit,
                     "常數版本": b.constants_version, "穩定性版本": b.stability_version,
                     "歷史目標狀態": list(b.target(choice).reasons)})
    else:
        st.info("沒有已確認可用的 SPC 基準；不畫有效管制界限。")
    st.caption(f"外觀實測標籤：有效 {result.appearance_count} 筆，NG {result.appearance_ng} 筆；外觀不適用 X-bar，未計算模型風險。")
    with st.expander("子組完整性與原始列追溯"):
        st.dataframe(pd.DataFrame([{"批號":g.batch,"子組":g.subgroup,"區段":g.segment,
                                   "完成時間":g.completed_at,"n":g.n,"均值":g.mean,
                                   "狀態":"有效" if g.valid else "無效",
                                   "原因":"；".join(g.reasons),"來源列":str(g.source_rows)} for g in target.groups]),
                     hide_index=True)
    st.subheader("SPC 實測事件（全目標）")
    render_spc_events(result)
    with st.expander("SPC 事件識別與規則序列"):
        st.dataframe(pd.DataFrame([{**asdict(e),"sequence":str(e.sequence),"source_rows":str(e.source_rows)}
                                  for e in result.events]),hide_index=True)
