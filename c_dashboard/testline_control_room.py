"""Formal Synthetic v3 single-mode test-line control room."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

import altair as alt
import pandas as pd
import streamlit as st

from fccl_testline.config import load_product_recipe
from fccl_testline.analysis import HeatmapService, WhatIfService
from fccl_testline.engine import TestlineEngine
from fccl_testline.generation import SCENARIOS, TARGETS
from fccl_testline.run_store import CSV_FILES, RunStore
from .testline_prototype import _css


ROOT = Path(__file__).resolve().parents[1]
PAGES = ("生產控制台", "SPC 詳細監控", "What-if／Heatmap", "Run 紀錄")
LABELS = {
    "line_speed_m_min": "線速", "coating_gap_um": "塗佈間隙", "curing_temp_c": "熟化溫度",
    "exhaust_airflow_m3_h": "排風量", "curing_time_min": "熟化時間",
    "lamination_temp_c": "壓合溫度", "lamination_pressure_mpa": "壓合壓力",
    "coating_temp_c": "塗佈溫度", "coating_viscosity_mpa_s": "黏度", "lamination_time_min": "壓合時間",
}
QUALITY_LABELS = {"peel_strength_n_mm": "抗剝離度", "dimensional_stability_md_pct": "尺寸安定性 MD", "dimensional_stability_td_pct": "尺寸安定性 TD", "heat_resistance_c": "耐熱度"}
QUALITY_UNITS = {"peel_strength_n_mm": "N/mm", "dimensional_stability_md_pct": "%", "dimensional_stability_td_pct": "%", "heat_resistance_c": "°C"}


@st.cache_resource
def _heatmap_service() -> HeatmapService:
    return HeatmapService()


@st.cache_resource
def _whatif_service() -> WhatIfService:
    return WhatIfService(ROOT/"artifacts/synthetic_v3/quality-v3.0")


def _new_engine(scenario: str) -> TestlineEngine:
    run_id = "RUN-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()
    seed = 9001 + SCENARIOS.index(scenario)
    return TestlineEngine(project_root=ROOT, run_id=run_id, seed=seed, scenario=scenario)


def _engine() -> TestlineEngine:
    if "testline_engine" not in st.session_state:
        RunStore(ROOT/"runtime_data").mark_unfinished_interrupted()
        st.session_state.testline_engine = _new_engine("stable")
    return st.session_state.testline_engine


def _header(engine: TestlineEngine) -> None:
    st.markdown('<div class="proto-banner">Synthetic v3 本機模擬｜不連接 PLC、MES 或真實設備｜結果不代表因果或真實產線效能</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero"><div><div class="hero-title">3L FCCL 測試線模擬控制台</div><div class="hero-sub">塗佈 → 熟化 → 壓合｜單一產品 FCCL-DEMO-001</div></div><div class="source-chip">{engine.run_id}｜{engine.simulator.scenario}</div></div>', unsafe_allow_html=True)


def _navigation() -> str:
    current = st.session_state.get("testline_page", PAGES[0]); columns = st.columns(4)
    for column, page in zip(columns, PAGES):
        if column.button(("🔴 " if page == current else "⚫ ") + page, key=f"testline_nav_{page}", use_container_width=True):
            st.session_state.testline_page = page; st.rerun()
    return current


def _run_controls(engine: TestlineEngine) -> None:
    c1,c2,c3,c4 = st.columns([1.4,1,1,1])
    scenario = c1.selectbox("模擬情境", SCENARIOS, index=SCENARIOS.index(engine.simulator.scenario), format_func=lambda x: {"stable":"穩定","thickness_increase":"厚度增厚","thickness_decrease":"厚度變薄","temperature_drop":"溫度下降","airflow_decay":"風量衰減","pressure_drift":"壓力漂移","compound_drift":"複合漂移"}[x])
    if c2.button("前進 1 點（5 秒）", use_container_width=True): engine.step(1); st.rerun()
    if c3.button("前進 12 點（60 秒）", type="primary", use_container_width=True): engine.step(12); st.rerun()
    if c4.button("新 Run", use_container_width=True):
        try: engine.stop()
        except Exception: pass
        st.session_state.testline_engine = _new_engine(scenario); st.rerun()
    st.caption(f"模擬時間 {engine.simulator.clock.simulated_seconds} 秒｜序號 {engine.simulator.clock.sequence}｜資料每 5 模擬秒一點；運算過慢會降速或暫停，不跳資料。")


def _line(engine: TestlineEngine) -> None:
    states = engine.simulator.segments_at_station(engine.simulator.clock.simulated_seconds)
    def latest(name: str) -> str:
        return states[name][-1].segment_id if states[name] else "等待材料"
    st.subheader("模擬產線與材料位置")
    st.caption("同一卷材同時分布於整條連續線；各框顯示該站目前最新邏輯區段，不代表其他站沒有材料。")
    st.markdown('<div class="line"><div class="station">放捲<br><span class="small-note">連續卷材</span></div><div class="arrow">→</div>'
                f'<div class="station">塗佈<br><span class="small-note">{latest("coating")}</span></div><div class="arrow">→</div>'
                f'<div class="station">熟化<br><span class="small-note">{latest("curing")}</span></div><div class="arrow">→</div>'
                f'<div class="station">壓合<br><span class="small-note">{latest("lamination")}</span></div><div class="arrow">→</div>'
                f'<div class="station">品質預測<br><span class="small-note">{latest("quality_ready")}</span></div></div>', unsafe_allow_html=True)


def _spec_recipe() -> None:
    cfg = load_product_recipe(); left,right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("本批產品規格"); st.write("產品 **FCCL-DEMO-001**　規格版本 **DEMO-SPEC-1.0**")
        st.metric("乾膠厚度目標", "25.0 μm", "允收 23.0–27.0 μm", delta_color="off")
        st.caption("其餘四項為完成材料模型預測；產品規格與製程管制界限分開。")
    with right, st.container(border=True):
        st.subheader("機台配方標準"); rows=[]
        for name,item in cfg["recipe"]["parameters"].items():
            if not item.get("advanced"): rows.append({"製程":item["station"],"參數":LABELS[name],"標準值":f'{item["default"]:g} {item["unit"]}',"配方範圍":f'{item["recipe_min"]:g}–{item["recipe_max"]:g} {item["unit"]}'})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _parameter_form(engine: TestlineEngine) -> None:
    cfg=load_product_recipe()["recipe"]["parameters"]; st.subheader("機台參數調整")
    with st.form("formal_parameter_form"):
        candidate={}; cols=st.columns(3)
        for i,(name,item) in enumerate(cfg.items()):
            if item.get("advanced"): continue
            with cols[i%3]:
                candidate[name]=st.number_input(f'{item["station"]}｜{LABELS[name]} ({item["unit"]})', min_value=float(item["ui_min"]), max_value=float(item["ui_max"]), value=float(engine.simulator.setpoints[name]), step=max((item["ui_max"]-item["ui_min"])/100, .01), key=f"candidate_{name}")
                st.caption(f'Actual {engine.simulator.actuals[name]:.2f}｜配方 {item["recipe_min"]:g}–{item["recipe_max"]:g}｜UI {item["ui_min"]:g}–{item["ui_max"]:g}')
        with st.expander("進階參數"):
            advanced=st.columns(3)
            for i,(name,item) in enumerate((x for x in cfg.items() if x[1].get("advanced"))):
                with advanced[i]: candidate[name]=st.number_input(f'{LABELS[name]} ({item["unit"]})', min_value=float(item["ui_min"]), max_value=float(item["ui_max"]), value=float(engine.simulator.setpoints[name]), key=f"candidate_{name}")
        submitted=st.form_submit_button("確認套用至後續材料", type="primary")
    if submitted:
        try: engine.apply_parameters(candidate); st.success("已建立不可變參數事件；只影響尚未通過適用站別的材料，Alarm 等待後續量測復歸。")
        except ValueError as exc: st.error(f"整組未套用：{exc}")


def _chart(engine: TestlineEngine, signal: str, title: str) -> None:
    rows=[r for r in engine.tables["process_signals"] if r["signal_name"]==signal][-60:]
    if not rows: st.info(f"{title}：尚待第一筆模擬訊號"); return
    frame=pd.DataFrame(rows); limits=engine.spc[signal].limits
    base=alt.Chart(frame).encode(x=alt.X("tick_sequence:Q",title="模擬序號"))
    line=base.mark_line(color="#246fbd",strokeWidth=2).encode(y=alt.Y("actual_value:Q",title="Actual"))
    rules=pd.DataFrame({"value":[limits.center,limits.ucl,limits.lcl],"kind":["中心／目標","上限／警戒","下限／警戒"]})
    rule=alt.Chart(rules).mark_rule(strokeDash=[6,4]).encode(y="value:Q",color=alt.Color("kind:N",scale=alt.Scale(range=["#2457d6","#d94b45","#d94b45"])))
    st.markdown(f"**{title}**"); st.altair_chart((line+rule).properties(height=220),use_container_width=True)
    st.caption(f"CL {limits.center:.3f}｜UCL {limits.ucl:.3f}｜LCL {limits.lcl:.3f}｜最近 {len(frame)} 點｜固定 reference {limits.baseline_version}")


def _quality(engine: TestlineEngine) -> None:
    st.subheader("完成材料品質預測"); latest={}
    for row in engine.tables["quality_predictions"]: latest[row["target"]]=row
    cols=st.columns(4)
    for col,target in zip(cols,TARGETS):
        with col:
            if target not in latest: st.metric(QUALITY_LABELS[target], "等待完成材料")
            else:
                row=latest[target]; status="範圍內" if row["support_status"]=="in_range" else "模型外插"
                st.metric(QUALITY_LABELS[target], f'{row["prediction"]:.3f} {QUALITY_UNITS[target]}', status, delta_color="normal" if status=="範圍內" else "inverse")
                st.caption(f'{row["segment_id"]}｜{row["model_version"]}')


def _alarm_summary(engine: TestlineEngine) -> None:
    st.subheader("AI Alarm 摘要"); groups=engine.alarms.summary()
    if not groups: st.success("目前沒有開啟中的製程 Alarm。")
    else:
        severe=sum(g.severity.value=="severe" for g in groups); st.warning(f"{len(groups)} 個開啟事件群｜嚴重 {severe}｜請至 SPC 詳細監控查看規則與後續復歸證據。")
        if st.button("開啟 SPC Alarm 中心"): st.session_state.testline_page=PAGES[1]; st.rerun()


def _production(engine: TestlineEngine) -> None:
    _run_controls(engine); _line(engine); _spec_recipe(); _parameter_form(engine)
    st.subheader("製程 SPC 監控摘要"); cols=st.columns(3)
    for col,args in zip(cols,(("dry_thickness_mean_um","乾膠厚度 X-bar／R"),("curing_temp_c","熟化溫度 I-MR"),("exhaust_airflow_m3_h","排風量 EWMA"))):
        with col: _chart(engine,*args)
    _quality(engine); _alarm_summary(engine)


def _spc(engine: TestlineEngine) -> None:
    st.header("SPC 詳細監控"); st.caption("一次顯示全部五項正式製程訊號；品質預測不作實測 SPC 點。")
    for row in (("dry_thickness_mean_um","乾膠厚度 X-bar／R"),("curing_temp_c","熟化溫度 I-MR"),("exhaust_airflow_m3_h","排風量 EWMA"),("line_speed_m_min","線速 I-MR"),("lamination_pressure_mpa","壓合壓力 I-MR")):
        _chart(engine,*row)
    st.subheader("AI Alarm 事件群")
    if not engine.alarms.events: st.info("尚無事件；證據會隨模擬訊號累積。")
    for event in reversed(engine.alarms.events):
        status="開啟" if event.ended_at is None else "已由後續證據復歸"
        with st.expander(f"{event.severity.value}｜{event.signal_name}｜{event.event_kind}｜{status}｜影響 {event.affected_points} 點"):
            st.json({"event_id":event.event_id,"rules":sorted(event.rule_codes),"started_at":event.started_at.isoformat(),"ended_at":event.ended_at.isoformat() if event.ended_at else None,"parameter_events":event.parameter_event_ids})


def _analysis(engine: TestlineEngine) -> None:
    st.header("What-if／Heatmap"); tabs=st.tabs(["What-if 參數比較","Heatmap"])
    with tabs[0]:
        if engine.candidates.empty or not engine.tables["quality_predictions"]: st.info("尚無已完成且可預測的材料區段；請先推進模擬。")
        else:
            segment_ids=sorted(set(r["segment_id"] for r in engine.tables["quality_predictions"])); selected=st.selectbox("完成材料區段",segment_ids)
            row=engine.candidates[engine.candidates.segment_id==selected].iloc[-1]; cfg=load_product_recipe()["recipe"]["parameters"]
            candidate={}; cols=st.columns(3)
            for i,name in enumerate([n for n,v in cfg.items() if not v.get("advanced")]):
                item=cfg[name]
                with cols[i%3]: candidate[name]=st.number_input(f'What-if {LABELS[name]} ({item["unit"]})',min_value=float(item["ui_min"]),max_value=float(item["ui_max"]),value=float(engine.simulator.setpoints[name]),key=f"whatif_{name}")
            if st.button("計算四目標比較",type="primary"):
                try: st.session_state.whatif_result=_whatif_service().compare(row,candidate)
                except ValueError as exc: st.error(str(exc))
            result=st.session_state.get("whatif_result")
            if result and result["segment_id"]==selected:
                st.dataframe(pd.DataFrame([{"品質":QUALITY_LABELS[t],**v} for t,v in result["targets"].items()]),hide_index=True,use_container_width=True)
                st.caption("模型比較僅供決策輔助；不代表真實 FCCL 製程因果效果或已驗證改善。")
                if st.button("帶回生產控制台再確認"):
                    for name,value in result["candidate"].items(): st.session_state[f"candidate_{name}"]=value
                    st.session_state.testline_page=PAGES[0]; st.rerun()
    with tabs[1]:
        source=st.selectbox("Heatmap 資料來源",["v3_reference","current_run"],format_func=lambda x:"Synthetic v3 穩定 reference" if x=="v3_reference" else "目前 Run 完成材料")
        if st.button("重新計算 Heatmap"):
            service=_heatmap_service()
            try:
                if source=="v3_reference": rows=pd.read_csv(ROOT/"generated_data/v3/stable_reference.csv"); version="SIM-RECIPE-3.0-STABLE-1"
                else: rows=service.current_rows(engine.candidates,engine.tables["quality_predictions"]); version=engine.run_id
                st.session_state.heatmap_result=service.calculate(rows,source=source,version=version,cutoff=str(engine.simulator.clock.sequence))
            except ValueError as exc: st.warning(str(exc))
        result=st.session_state.get("heatmap_result")
        if result and result["source"]==source:
            melted=result["correlation"].reset_index(names="製程參數").melt("製程參數",var_name="品質目標",value_name="Pearson r")
            chart=alt.Chart(melted).mark_rect().encode(x="品質目標:N",y="製程參數:N",color=alt.Color("Pearson r:Q",scale=alt.Scale(scheme="redblue",domain=[-1,1])),tooltip=["製程參數","品質目標",alt.Tooltip("Pearson r:Q",format=".3f")])
            st.altair_chart(chart.properties(height=420),use_container_width=True)
            strongest=melted.iloc[melted["Pearson r"].abs().argsort()[::-1][:5]]
            st.dataframe(strongest,hide_index=True,use_container_width=True)
            st.caption(f'{result["source"]}｜{result["segments"]} 個完成區段｜截止 {result["cutoff"]}｜相關不代表因果。')
        elif result: st.info("資料來源已切換；舊 Heatmap 已失效，請重新計算。")


def _runs(engine: TestlineEngine) -> None:
    st.header("Run 紀錄")
    if engine.store.load_manifest(engine.run_id).get("status")=="running": engine.checkpoint()
    root=ROOT/"runtime_data/testline_runs"
    rows=[]
    for path in sorted(root.glob("*/manifest.json"),reverse=True):
        try:
            m=__import__("json").loads(path.read_text(encoding="utf-8")); rows.append({"run_id":m["run_id"],"status":m["status"],"scenario":m["scenario"],"checkpoint":m.get("checkpoint_sequence",0),"synthetic_only":m.get("synthetic_only",True)})
        except Exception: continue
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    if rows:
        selected=st.selectbox("檢視 Run",[r["run_id"] for r in rows]); run_dir=root/selected
        manifest_text=(run_dir/"manifest.json").read_text(encoding="utf-8"); manifest=__import__("json").loads(manifest_text)
        if manifest.get("status")=="interrupted": st.warning("此 Run 非正常中斷，只能唯讀檢視；初版不支援續跑。")
        st.json(manifest)
        st.download_button("下載 manifest.json",manifest_text,file_name=f"{selected}-manifest.json",mime="application/json")
        with st.expander("下載 Run CSV"):
            for filename in CSV_FILES.values():
                path=run_dir/filename
                if path.exists(): st.download_button(f"下載 {filename}",path.read_bytes(),file_name=f"{selected}-{filename}",mime="text/csv",key=f"download_{selected}_{filename}")
    st.caption("Run 僅供本機 Synthetic 稽核；completed／interrupted 不會觸發訓練、baseline 重估或模型升版。")


def render_testline_control_room() -> None:
    _css(); engine=_engine(); _header(engine); page=_navigation()
    if page==PAGES[0]: _production(engine)
    elif page==PAGES[1]: _spc(engine)
    elif page==PAGES[2]: _analysis(engine)
    else: _runs(engine)
