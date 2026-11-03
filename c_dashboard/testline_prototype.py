"""Gate 0 UI fixture for the future test-line control room.

This module deliberately has no model, simulator, filesystem, or equipment I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import math

import altair as alt
import pandas as pd
import streamlit as st


PROTOTYPE_SOURCE = "Gate 0 靜態 fixture｜非執行中模擬"
PAGES = ("生產控制台", "SPC 詳細監控", "What-if／Heatmap", "Run 紀錄")


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    unit: str
    setpoint: float
    actual: float
    recipe_min: float
    recipe_max: float
    ui_min: float
    ui_max: float
    step: float
    station: str


MAIN_PARAMETERS = (
    Parameter("line_speed", "線速", "m/min", 4.80, 4.77, 4.40, 5.20, 4.00, 5.60, 0.05, "塗佈"),
    Parameter("coating_gap", "塗佈間隙", "μm", 28.0, 27.9, 26.5, 29.5, 25.0, 31.0, 0.1, "塗佈"),
    Parameter("curing_temp", "熟化溫度", "°C", 171.0, 170.6, 168.0, 174.0, 165.0, 177.0, 0.5, "熟化"),
    Parameter("exhaust_airflow", "排風量", "m³/h", 2100.0, 2088.0, 1900.0, 2300.0, 1700.0, 2500.0, 10.0, "熟化"),
    Parameter("curing_time", "熟化時間", "min", 12.5, 12.5, 11.8, 13.2, 11.0, 14.0, 0.1, "熟化"),
    Parameter("lamination_temp", "壓合溫度", "°C", 181.0, 180.7, 178.0, 184.0, 175.0, 187.0, 0.5, "壓合"),
    Parameter("lamination_pressure", "壓合壓力", "MPa", 2.55, 2.52, 2.35, 2.75, 2.20, 2.90, 0.05, "壓合"),
)

ADVANCED_PARAMETERS = (
    Parameter("coating_temp", "塗佈溫度", "°C", 82.0, 81.8, 78.0, 86.0, 76.0, 88.0, 0.5, "塗佈"),
    Parameter("viscosity", "黏度", "mPa·s", 1180.0, 1172.0, 1080.0, 1280.0, 1000.0, 1360.0, 10.0, "塗佈"),
    Parameter("lamination_time", "壓合時間", "min", 18.0, 18.0, 16.0, 20.0, 15.0, 21.0, 0.5, "壓合"),
)


def _css() -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
          background: #f4f7fb !important; color: #152238 !important;
        }
        .block-container { max-width: 1500px; padding: 1.4rem 2.2rem 3rem; }
        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label,
        .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stMetricLabel"],
        .stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricDelta"] {
          color: #152238 !important;
        }
        h1 { font-size: 2.15rem !important; letter-spacing: -.02em; }
        h2 { font-size: 1.55rem !important; margin-top: .6rem !important; }
        h3 { font-size: 1.18rem !important; }
        p, label, [data-testid="stMetricLabel"] { font-size: 1rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.85rem !important; }
        .proto-banner { background:#fff4d6; border:1px solid #e6b94b; color:#6b4b00;
          border-radius:14px; padding:12px 16px; font-weight:700; margin-bottom:12px; }
        .hero { display:flex; justify-content:space-between; align-items:center; gap:20px;
          background:white; border:1px solid #dce5f1; border-radius:18px; padding:18px 22px; margin-bottom:14px; }
        .hero-title { font-size:1.65rem; font-weight:800; color:#13213a; }
        .hero-sub { color:#5b6b82; margin-top:3px; }
        .source-chip { background:#eaf1ff; color:#1749a8; padding:8px 12px; border-radius:999px; font-weight:700; }
        .line { display:flex; align-items:center; gap:8px; background:white; border:1px solid #dce5f1;
          border-radius:16px; padding:20px 14px; overflow-x:auto; margin:8px 0 18px; }
        .station { min-width:145px; text-align:center; border:2px solid #a9c3f6; border-radius:14px;
          padding:13px 10px; background:#f7faff; font-weight:750; }
        .station.active { border-color:#2457d6; background:#eaf1ff; box-shadow:0 0 0 4px #dce7ff; }
        .tracking-badge { display:inline-block; margin-top:6px; padding:3px 8px; border-radius:999px;
          background:#2457d6; color:#ffffff !important; font-size:.78rem; }
        .arrow { color:#7387a8; font-size:1.6rem; font-weight:800; }
        .small-note { color:#64748b; font-size:.92rem; }
        [data-testid="stVerticalBlockBorderWrapper"] {
          background:#ffffff !important; border-color:#d7e0ec !important; border-radius:16px;
        }
        [data-testid="stVerticalBlockBorderWrapper"] * { color:#152238 !important; }
        [data-testid="stRadio"] > div { gap: .45rem; }
        [data-testid="stRadio"] label { background:#ffffff !important; border:1px solid #cbd7e6;
          border-radius:10px; padding:.42rem .8rem; }
        [data-testid="stRadio"] label p, [data-testid="stRadio"] label span { color:#152238 !important; }
        [data-testid="stNumberInput"] > div > div,
        [data-testid="stNumberInput"] input {
          background:#ffffff !important; color:#152238 !important; border-color:#b9c8dc !important;
        }
        [data-testid="stNumberInput"] button { background:#eef3fa !important; color:#152238 !important; }
        [data-testid="stSelectbox"] > div > div { background:#ffffff !important; color:#152238 !important; }
        [data-testid="stExpander"] { background:#ffffff !important; border-color:#d7e0ec !important; }
        [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color:#152238 !important; }
        [data-testid="stForm"] { background:#f8fbff !important; border-color:#d7e0ec !important; }
        [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
          flex-direction:row !important; flex-wrap:nowrap !important; gap:12px !important;
        }
        [data-testid="stForm"] [data-testid="column"] { min-width:0 !important; flex:1 1 0 !important; }
        [data-testid="stForm"] [data-testid="stVerticalBlockBorderWrapper"] { padding:10px 12px !important; }
        [data-testid="stAlert"] { background:#ffffff !important; color:#152238 !important; border:1px solid #d7e0ec !important; }
        [data-testid="stAlert"] * { color:#152238 !important; }
        [data-testid="stTabs"] button { color:#42526b !important; }
        [data-testid="stTabs"] button[aria-selected="true"] { color:#1749a8 !important; font-weight:750; }
        .stButton button, [data-testid="stFormSubmitButton"] button {
          background:#ffffff !important; color:#1749a8 !important; border-color:#9bb7ea !important;
        }
        .stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
          background:#2457d6 !important; color:#ffffff !important;
        }
        [data-testid="stCodeBlock"], [data-testid="stJson"] { background:#f0f4f9 !important; }
        [data-testid="stCodeBlock"] *, [data-testid="stJson"] * { color:#152238 !important; }
        .light-table { width:100%; border-collapse:separate; border-spacing:0; overflow:hidden;
          border:1px solid #d7e0ec; border-radius:12px; background:#ffffff; color:#152238; }
        .light-table th { background:#edf3fb; color:#23344f; font-weight:750; text-align:left; }
        .light-table td { background:#ffffff; color:#152238; }
        .light-table th, .light-table td { padding:9px 11px; border-bottom:1px solid #e3eaf3; }
        .light-table tr:last-child td { border-bottom:0; }
        .quality-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:8px 0 16px; }
        .quality-card { background:#ffffff; border:1px solid #d7e0ec; border-radius:14px; padding:14px; }
        .quality-label { color:#42526b; font-size:.92rem; }
        .quality-value { color:#152238; font-size:1.55rem; font-weight:800; margin:5px 0 8px; }
        .status-chip { display:inline-block; border-radius:999px; padding:4px 9px; font-size:.84rem; font-weight:750; }
        .status-ok { color:#0d6b47; background:#dcf5e9; border:1px solid #91d5b6; }
        .status-warning { color:#805400; background:#fff1c7; border:1px solid #e5c56a; }
        .status-danger { color:#a12622; background:#fde3e1; border:1px solid #eba19d; }
        .status-unknown { color:#536176; background:#edf1f6; border:1px solid #cbd5e1; }
        @media (max-width:900px) { .quality-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    if "prototype_applied" not in st.session_state:
        st.session_state.prototype_applied = {p.key: p.setpoint for p in MAIN_PARAMETERS + ADVANCED_PARAMETERS}
    if "prototype_notice" not in st.session_state:
        st.session_state.prototype_notice = ""


def _header() -> None:
    st.markdown('<div class="proto-banner">⚠ Gate 0 靜態 UI 原型｜所有數值均為固定 fixture，不會啟動模型、模擬器或真實設備</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="hero"><div><div class="hero-title">3L FCCL 測試線模擬控制台</div>'
        '<div class="hero-sub">塗佈 → 熟化 → 壓合｜單一產品測試情境</div></div>'
        f'<div class="source-chip">{PROTOTYPE_SOURCE}</div></div>',
        unsafe_allow_html=True,
    )


def _line_diagram() -> None:
    st.subheader("模擬產線與材料位置")
    st.caption("整線連續運轉中｜卷材同時通過各站；藍色框表示目前選取追蹤的邏輯區段，不代表其他站沒有材料。")
    st.markdown(
        '<div class="line">'
        '<div class="station">放捲<br><span class="small-note">連續卷材供料</span></div><div class="arrow">→</div>'
        '<div class="station">塗佈<br><span class="small-note">處理 SEG-019</span></div><div class="arrow">→</div>'
        '<div class="station active">熟化<br><span class="small-note">處理 SEG-018</span><br><span class="tracking-badge">目前追蹤區段</span></div><div class="arrow">→</div>'
        '<div class="station">壓合<br><span class="small-note">處理 SEG-017</span></div><div class="arrow">→</div>'
        '<div class="station">品質預測<br><span class="small-note">完成 SEG-016</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _product_recipe() -> None:
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("本批產品規格")
        st.caption(PROTOTYPE_SOURCE)
        st.markdown("**產品**　FCCL-DEMO-001　　**規格版本**　DEMO-SPEC-1.0")
        st.metric("乾膠厚度目標", "25.0 μm", "允收 23.0–27.0 μm", delta_color="off")
        st.write("抗剝離度、尺寸安定性 MD／TD、耐熱度：Gate 0 僅展示品質預測版位。")
    with right, st.container(border=True):
        st.subheader("機台配方標準")
        st.caption("SIM-RECIPE-3.0｜Synthetic demo 假設，非工廠標準")
        rows = [{"製程": p.station, "參數": p.label, "標準值": f"{p.setpoint:g} {p.unit}",
                 "配方範圍": f"{p.recipe_min:g}–{p.recipe_max:g} {p.unit}"} for p in MAIN_PARAMETERS]
        _light_table(pd.DataFrame(rows))


def _light_table(frame: pd.DataFrame) -> None:
    """Render fixture tables with deterministic light colors in either host theme."""
    headings = "".join(f"<th>{escape(str(column))}</th>" for column in frame.columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
        for row in frame.itertuples(index=False, name=None)
    )
    st.markdown(f'<table class="light-table"><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table>', unsafe_allow_html=True)


def _light_heatmap(frame: pd.DataFrame) -> None:
    """Render a light diverging correlation matrix without host-theme leakage."""
    headings = "<th>製程參數</th>" + "".join(f"<th>{escape(str(column))}</th>" for column in frame.columns)
    rows = []
    for index, values in frame.iterrows():
        cells = [f"<td><strong>{escape(str(index))}</strong></td>"]
        for value in values:
            strength = min(abs(float(value)), 1.0)
            if value >= 0:
                red, green, blue = 255 - int(45 * strength), 255 - int(25 * strength), 255
            else:
                red, green, blue = 255, 255 - int(45 * strength), 255 - int(45 * strength)
            cells.append(f'<td style="background:rgb({red},{green},{blue});text-align:center;font-weight:700">{value:.2f}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(f'<table class="light-table"><thead><tr>{headings}</tr></thead><tbody>{"".join(rows)}</tbody></table>', unsafe_allow_html=True)


def _parameter_form() -> None:
    st.subheader("機台參數調整")
    st.caption("數字欄位只修改候選值；按下確認才更新本頁 fixture setpoint。actual 為獨立固定示意值。")
    with st.form("prototype_parameter_form"):
        for start in range(0, len(MAIN_PARAMETERS), 3):
            cols = st.columns(3)
            for col, p in zip(cols, MAIN_PARAMETERS[start:start + 3]):
                applied = float(st.session_state.prototype_applied[p.key])
                with col, st.container(border=True):
                    st.markdown(f"**{p.station}｜{p.label}**")
                    st.number_input(
                        f"候選值 ({p.unit})", min_value=p.ui_min, max_value=p.ui_max,
                        value=applied, step=p.step, key=f"prototype_input_{p.key}",
                    )
                    st.caption(f"Setpoint {applied:g}　｜　Actual {p.actual:g} {p.unit}")
                    st.caption(f"配方 {p.recipe_min:g}–{p.recipe_max:g}　｜　UI {p.ui_min:g}–{p.ui_max:g}")
        with st.expander("進階參數（Gate 0 fixture）"):
            adv_cols = st.columns(3)
            for idx, p in enumerate(ADVANCED_PARAMETERS):
                applied = float(st.session_state.prototype_applied[p.key])
                with adv_cols[idx]:
                    st.number_input(
                        f"{p.label} ({p.unit})", min_value=p.ui_min, max_value=p.ui_max,
                        value=applied, step=p.step, key=f"prototype_input_{p.key}",
                    )
                    st.caption(f"Setpoint {applied:g}｜Actual {p.actual:g}｜配方 {p.recipe_min:g}–{p.recipe_max:g}")
        submitted = st.form_submit_button("確認套用至靜態 fixture", type="primary")
    if submitted:
        for p in MAIN_PARAMETERS + ADVANCED_PARAMETERS:
            st.session_state.prototype_applied[p.key] = float(st.session_state[f"prototype_input_{p.key}"])
        st.session_state.prototype_notice = "候選值已更新至本頁 fixture；未建立 ParameterEvent，也未控制任何設備。"
    if st.session_state.prototype_notice:
        st.success(st.session_state.prototype_notice)


def _series(center: float, amplitude: float, drift: float = 0.0) -> pd.DataFrame:
    values = [center + math.sin(i / 5) * amplitude + max(0, i - 38) * drift for i in range(60)]
    return pd.DataFrame({"模擬點序": range(1, 61), "actual": values}).set_index("模擬點序")


def _chart(title: str, frame: pd.DataFrame, caption: str, center: float, upper: float, lower: float) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        data = frame.reset_index()
        base = alt.Chart(data).encode(
            x=alt.X("模擬點序:Q", title="模擬點序", axis=alt.Axis(labelColor="#42526b", titleColor="#42526b", grid=False)),
        )
        actual = base.mark_line(color="#2474b5", strokeWidth=2.5).encode(
            y=alt.Y("actual:Q", title="Actual", scale=alt.Scale(zero=False),
                    axis=alt.Axis(labelColor="#42526b", titleColor="#42526b", gridColor="#dfe6ef")),
            tooltip=["模擬點序:Q", alt.Tooltip("actual:Q", format=".2f")],
        )
        limits = pd.DataFrame([
            {"kind": "中心／目標", "value": center},
            {"kind": "上限／警戒", "value": upper},
            {"kind": "下限／警戒", "value": lower},
        ])
        rules = alt.Chart(limits).mark_rule(strokeDash=[6, 4], strokeWidth=1.5).encode(
            y="value:Q",
            color=alt.Color("kind:N", scale=alt.Scale(
                domain=["中心／目標", "上限／警戒", "下限／警戒"],
                range=["#2457d6", "#d84a3a", "#d84a3a"],
            ), legend=alt.Legend(title=None, orient="bottom", labelColor="#42526b")),
        )
        chart = (actual + rules).properties(height=210, background="#ffffff").configure_view(
            fill="#ffffff", stroke="#d7e0ec"
        ).configure_legend(labelColor="#42526b", titleColor="#42526b")
        st.altair_chart(chart, theme=None)
        st.caption(f"{caption}｜最近 60 點｜{PROTOTYPE_SOURCE}")


def _monitoring_summary() -> None:
    st.subheader("製程 SPC 即時總覽")
    st.caption("全部 5 項製程訊號均顯示；詳細規則與事件群請至 SPC 詳細監控。")
    charts = (
        ("乾膠厚度 X-bar", _series(25.0, .22, .012), "CL 25.0｜UCL 26.0｜LCL 24.0", 25, 26, 24),
        ("熟化溫度 I-MR", _series(171.0, .35, -.025), "CL 171.0｜UCL 172.4｜LCL 169.6", 171, 172.4, 169.6),
        ("排風量 EWMA", _series(2100, 15, -1.1), "Target 2100｜警戒 2250／1950", 2100, 2250, 1950),
        ("線速 I-MR", _series(4.8, .035, .001), "CL 4.80｜UCL 4.95｜LCL 4.65", 4.8, 4.95, 4.65),
        ("壓合壓力 I-MR", _series(2.55, .025, -.001), "CL 2.55｜UCL 2.68｜LCL 2.42", 2.55, 2.68, 2.42),
    )
    for start, count in ((0, 3), (3, 2)):
        columns = st.columns(count)
        for column, args in zip(columns, charts[start:start + count]):
            with column:
                _chart(*args)


def _quality_and_alarm() -> None:
    st.subheader("完成材料品質預測")
    st.caption("固定區段 SEG-012｜Prototype RF fixture v0｜不是正式模型推論")
    cards = (
        ("抗剝離度", "1.31 N/mm", "高於規格下限 0.11 N/mm", "status-ok"),
        ("尺寸安定性 MD", "0.08 %", "符合規格", "status-ok"),
        ("尺寸安定性 TD", "0.06 %", "符合規格", "status-ok"),
        ("耐熱度", "238 °C", "高於規格下限 8 °C", "status-ok"),
    )
    html = "".join(
        f'<div class="quality-card"><div class="quality-label">{escape(label)}</div>'
        f'<div class="quality-value">{escape(value)}</div>'
        f'<span class="status-chip {status}">{escape(message)}</span></div>'
        for label, value, message, status in cards
    )
    st.markdown(f'<div class="quality-grid">{html}</div>', unsafe_allow_html=True)
    st.subheader("異常警報摘要")
    st.warning("2 項警告｜排風量下降趨勢、乾膠厚度趨勢｜0 項嚴重｜等待後續量測復歸")
    if st.button("查看 SPC 警報明細", key="prototype_open_spc_alarm"):
        st.session_state.prototype_active_page = "SPC 詳細監控"
        st.rerun()


def _production_page() -> None:
    _line_diagram()
    _product_recipe()
    _parameter_form()
    _monitoring_summary()
    _quality_and_alarm()


def _spc_page() -> None:
    st.header("SPC 詳細監控")
    st.caption(f"製程 actual 與品質預測分離｜{PROTOTYPE_SOURCE}")
    st.info("全部 5 項製程訊號同頁顯示。產品規格、配方範圍與統計管制界限是三種不同界線；本頁數值全為 fixture。")
    charts = (
        ("乾膠厚度 X-bar／R", _series(25, .24, .014), "CL 25.0｜UCL 26.0｜LCL 24.0；R 圖正式版獨立呈現", 25, 26, 24),
        ("熟化溫度 I-MR", _series(171, .45, -.02), "CL 171.0｜UCL 172.4｜LCL 169.6", 171, 172.4, 169.6),
        ("排風量 EWMA", _series(2100, 15, -1.1), "Target 2100｜警戒 2250／1950", 2100, 2250, 1950),
        ("線速 I-MR", _series(4.8, .035, .001), "CL 4.80｜UCL 4.95｜LCL 4.65", 4.8, 4.95, 4.65),
        ("壓合壓力 I-MR", _series(2.55, .025, -.001), "CL 2.55｜UCL 2.68｜LCL 2.42", 2.55, 2.68, 2.42),
    )
    for start in range(0, len(charts), 2):
        columns = st.columns(2)
        for column, args in zip(columns, charts[start:start + 2]):
            with column:
                _chart(*args)
    with st.container(border=True):
        st.subheader("全訊號目前狀態")
        status_cols = st.columns(4)
        status_cols[0].metric("正常", "3")
        status_cols[1].metric("警告", "2")
        status_cols[2].metric("嚴重", "0")
        status_cols[3].metric("證據不足", "0")
        st.caption("製程失控：排風量下降、厚度趨勢｜產品超規：尚未觀測｜Baseline：stable-reference-fixture-v1")
    st.subheader("事件群")
    _light_table(pd.DataFrame([
        {"狀態": "進行中", "等級": "警告", "訊號": "排風量", "規則": "EWMA 下降", "影響點": 12},
        {"狀態": "已結束", "等級": "警告", "訊號": "乾膠厚度", "規則": "中心線同側", "影響點": 8},
    ]))
    with st.expander("事件群原始證據"):
        st.json({"source": "gate0-static-fixture", "event_group": "PROTO-AIRFLOW-001", "raw_event_count": 12})
    st.subheader("異常警報中心")
    st.warning("SPC 製程警報｜排風量 EWMA 下降趨勢｜進行中｜12 個影響點｜等待有效後續量測復歸")
    st.info("品質預測警示｜目前 4 項完成材料預測皆符合 fixture 規格；這不代表產品已由真實檢驗判定合格。")
    with st.expander("SPC 警報技術明細（預設收合）"):
        st.code("fixture_event_id=PROTO-AIRFLOW-001\nrule=EWMA_DOWNWARD_TREND\nsource=gate0-static-fixture\nraw_events=12")
        st.caption("原型不提供確認、靜音、簽核、工單或 MES 動作；調整參數不會立即清除警報。")
    if st.button("前往生產控制台調整參數", key="prototype_alarm_to_parameters", type="primary"):
        st.session_state.prototype_active_page = "生產控制台"
        st.session_state.prototype_notice = "由 SPC 警報中心返回；請檢查排風量與相關製程參數。"
        st.rerun()


def _whatif_heatmap_page() -> None:
    st.header("What-if／Heatmap")
    st.caption(f"按需分析區｜與 live Run 隔離｜{PROTOTYPE_SOURCE}")
    whatif_tab, heatmap_tab = st.tabs(("What-if", "Heatmap"))
    with whatif_tab:
        st.subheader("固定材料區段比較")
        st.info("固定 SEG-012；候選只供比較，不會修改 live fixture 或 SPC。相關與模型輸出不代表真實因果效果。")
        speed = st.number_input("候選線速 (m/min)", 4.0, 5.6, 4.65, .05, key="prototype_whatif_speed")
        temp = st.number_input("候選熟化溫度 (°C)", 165.0, 177.0, 172.0, .5, key="prototype_whatif_temp")
        if st.button("計算靜態比較", key="prototype_calculate_whatif", type="primary"):
            st.session_state.prototype_whatif_ready = True
        if st.session_state.get("prototype_whatif_ready"):
            _light_table(pd.DataFrame([
                {"品質": "抗剝離度", "目前": 1.31, "候選": 1.34, "差異": "+0.03 N/mm"},
                {"品質": "尺寸安定性 MD", "目前": 0.08, "候選": 0.07, "差異": "-0.01 %"},
                {"品質": "尺寸安定性 TD", "目前": 0.06, "候選": 0.06, "差異": "0.00 %"},
                {"品質": "耐熱度", "目前": 238, "候選": 239, "差異": "+1 °C"},
            ]))
            st.caption(f"候選：線速 {speed:g} m/min、熟化 {temp:g} °C｜靜態 fixture，不是正式推論")
            if st.button("帶回生產控制台候選表單", key="prototype_return_candidate"):
                st.session_state.prototype_applied["line_speed"] = speed
                st.session_state.prototype_applied["curing_temp"] = temp
                st.session_state.prototype_notice = "What-if 候選已帶回；仍需在生產控制台再次確認。"
                st.success("已帶回候選；請回到生產控制台檢查並再次確認。")
    with heatmap_tab:
        source = st.selectbox("Heatmap 資料來源", ("Synthetic v3 reference fixture", "目前 Run fixture（18 個完成區段）"), key="prototype_heatmap_source")
        if source.startswith("目前"):
            st.warning("樣本不足：目前 18 個完成區段，至少需要 30 個；不會混入 reference 或重複品質值。")
        else:
            if st.button("計算靜態 Heatmap", key="prototype_calculate_heatmap"):
                st.session_state.prototype_heatmap_ready = True
            if st.session_state.get("prototype_heatmap_ready"):
                frame = pd.DataFrame({
                    "抗剝離度": [.48, .62, -.21, .16], "尺寸 MD": [-.35, -.18, .54, .22],
                    "尺寸 TD": [-.27, -.12, .46, .38], "耐熱度": [.19, .57, -.08, .31],
                }, index=("乾膠厚度", "熟化溫度", "線速", "壓合壓力"))
                _light_heatmap(frame)
                st.success("最強正相關：熟化溫度 ↔ 抗剝離度 r=0.62；最強負相關：線速 ↔ 抗剝離度 r=-0.21。相關不代表改善或因果。")


def _runs_page() -> None:
    st.header("Run 紀錄")
    st.caption(f"Gate 0 唯讀 fixture｜不會建立 runtime_data 或觸發訓練｜{PROTOTYPE_SOURCE}")
    runs = pd.DataFrame([
        {"run_id": "RUN-PROTO-003", "狀態": "completed", "情境": "穩定", "模擬截止": "00:30:00", "checkpoint": "完整"},
        {"run_id": "RUN-PROTO-002", "狀態": "interrupted", "情境": "排風量衰減", "模擬截止": "00:18:00", "checkpoint": "唯讀可檢視"},
        {"run_id": "RUN-PROTO-001", "狀態": "completed", "情境": "厚度增厚", "模擬截止": "00:25:00", "checkpoint": "完整"},
    ])
    _light_table(runs)
    selected = st.selectbox("檢視 Run", tuple(runs.run_id), key="prototype_run_select")
    row = runs.loc[runs.run_id == selected].iloc[0]
    with st.container(border=True):
        st.subheader(selected)
        st.json({"source": "gate0-static-fixture", "status": row["狀態"], "scenario": row["情境"],
                 "resume_supported": False, "training_eligible": False, "files_written": False})
        if row["狀態"] == "interrupted":
            st.warning("中斷 Run 只能唯讀檢視，初版不提供續跑。")
        else:
            st.success("完成狀態 fixture；不會自動加入模型訓練或 SPC baseline。")


def _page_navigation() -> str:
    """Render version-compatible navigation without Streamlit radio state."""
    current = st.session_state.get("prototype_active_page", PAGES[0])
    if current not in PAGES:
        current = PAGES[0]
        st.session_state.prototype_active_page = current
    st.caption("控制台頁面")
    columns = st.columns(len(PAGES))
    for column, label in zip(columns, PAGES):
        with column:
            if st.button(
                label,
                key=f"prototype_nav_{PAGES.index(label)}",
                type="primary" if label == current else "secondary",
            ):
                st.session_state.prototype_active_page = label
                st.rerun()
    return current


def render_testline_prototype() -> None:
    _css()
    _init_state()
    _header()
    page = _page_navigation()
    st.divider()
    if page == "生產控制台":
        _production_page()
    elif page == "SPC 詳細監控":
        _spc_page()
    elif page == "What-if／Heatmap":
        _whatif_heatmap_page()
    else:
        _runs_page()
    st.divider()
    st.caption("Gate 0 只驗收版面與互動；不接真實資料、模型、PLC、MES 或設備，也不代表製程因果效果。")
