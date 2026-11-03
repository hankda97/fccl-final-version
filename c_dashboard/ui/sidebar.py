"""C2 source controls and data context; parsing/state live in data modules."""

import pandas as pd
import streamlit as st
from pathlib import Path
from c_dashboard.workspace_modes.state import widget_key

from c_dashboard.data.fixtures import MOCK_CHOICES, load_mock_fixture
from c_dashboard.data.canonical import load_canonical_projection
from c_dashboard.data.session import attempt_upload, commit_dataset, selected_rows, set_filters
from c_dashboard.state import WorkspaceState


def _render_filters(workspace: WorkspaceState) -> None:
    dataset = workspace.data.dataset
    if dataset is None:
        return
    frame = dataset.frame
    token = dataset.source_id[:12]
    batches = [None, *sorted(frame.loc[frame.identity_valid, "product_batch"].unique())]
    selected = workspace.data.selected_batch
    batch = st.selectbox(
        "批次篩選", batches, index=batches.index(selected) if selected in batches else 0,
        format_func=lambda value: "全部批次" if value is None else value,
        key=widget_key(workspace, f"ui_batch_{token}"),
    )
    times = sorted({value.isoformat() for value in frame.timestamp.dropna()})
    start = workspace.data.time_start if workspace.data.time_start in times else times[0]
    end = workspace.data.time_end if workspace.data.time_end in times else times[-1]
    if len(times) > 1:
        start, end = st.select_slider(
            "時間範圍（含起訖，Asia/Taipei）", options=times, value=(start, end),
            key=widget_key(workspace, f"ui_time_{token}"),
        )
    else:
        st.caption(f"資料時間：{times[0]}")
    set_filters(workspace, batch, start, end)
    st.caption(f"目前篩選：{len(selected_rows(workspace))}／{len(frame)} 列")


def _render_context(workspace: WorkspaceState) -> None:
    dataset = workspace.data.dataset
    st.text("資料來源：" + (workspace.data.source_name or "尚未載入"))
    st.text("資料版本：" + (workspace.data.source_version or "—"))
    st.text("目前批號：" + (workspace.data.selected_batch or "全部／尚未選取"))
    if dataset:
        if dataset.source_kind == "mock":
            st.caption("C 專用 Mock · 非真實產線資料")
        elif dataset.source_kind == "canonical-projection":
            st.caption("版本化 Synthetic canonical projection · 非真實產線資料")
        else:
            st.caption("上傳來源 · 正式契約及產線來源未驗證")
    st.divider()
    st.subheader("產品規格")
    view = selected_rows(workspace)
    for column, label in (("product_id", "產品"), ("recipe_id", "製程條件／配方")):
        values = view[column].dropna().unique() if column in view else []
        st.text(f"{label}：" + ("、".join(str(value) for value in values if value) or "未提供"))
    if dataset and dataset.source_kind == "mock":
        st.warning("以下僅 C 專用示範設定，非正式品質允收規格。")
        st.caption(f"設定版本：{dataset.settings['version']} · {dataset.settings['source']}")
        labels = {
            "peel_strength_n_mm": "抗剝離度（N/mm）", "dimensional_stability_md_pct": "尺寸 MD（%）",
            "dimensional_stability_td_pct": "尺寸 TD（%）", "heat_resistance_c": "耐熱度（°C）",
            "appearance_ng": "外觀 NG",
        }
        for name, config in dataset.settings["quality_specs"].items():
            st.caption(f"{labels[name]}：{config}")
        st.caption("此資料的 SPC 適用性及固定歷史基準由 C3 示範設定提供。")
    else:
        st.info("正式規格來源待團隊交接；目前未套用正式品質允收數值。")
    st.subheader("材料資訊")
    valid = view.loc[view.identity_valid] if "identity_valid" in view else pd.DataFrame()
    latest = valid.iloc[-1] if not valid.empty else None
    if latest is not None:
        st.caption(f"最新篩選列：{latest['segment_id']} · {latest['timestamp'].isoformat()}")
        length = latest.get("length_m")
        st.text(f"區段長度：{length:g} m" if pd.notna(length) else "區段長度：未提供／無效")
        if "position_m" in view and view.position_m.notna().any():
            st.caption(f"材料位置：{view.position_m.min():g}～{view.position_m.max():g} m（不累加試片長度）")
    else:
        st.caption("目前無可用的批次／時間區段。")
    st.subheader("環境參數")
    for name, label in (("ambient_temp_c", "環境溫度（°C）"), ("ambient_rh_pct", "相對濕度（%RH）")):
        value = latest.get(name) if latest is not None else None
        st.metric(label, f"{value:.2f}" if pd.notna(value) else "—")
    st.caption("顯示最新篩選有效識別列的環境量測；缺值不以 0 代替。")


def render_sidebar(workspace: WorkspaceState) -> None:
    with st.sidebar:
        st.header("資料與製程資訊")
        st.caption("C2 CSV／canonical 載入｜C3 SPC｜C4／C5 What-if｜Synthetic 正式模型或公式 Mock")
        choice = st.radio("資料載入來源", ["尚未載入", "C 專用 Mock", "Canonical Synthetic projection", "上傳 CSV"], key=widget_key(workspace, "ui_source_choice"))
        st.caption(f"目前選定來源：{choice}")
        st.caption("目前已載入資料集：" + (workspace.data.source_name or "尚未載入；選定來源不等於完成載入"))
        scenario = st.selectbox("Mock 測試情境", list(MOCK_CHOICES), key=widget_key(workspace, "ui_mock_scenario"),
                                disabled=choice != "C 專用 Mock")
        if st.button("載入 Mock 資料", key=widget_key(workspace, "ui_load_mock"), disabled=choice != "C 專用 Mock"):
            commit_dataset(workspace, load_mock_fixture(MOCK_CHOICES[scenario]))
        canonical_profile = st.selectbox(
            "Canonical 標籤 profile", ["synthetic-ground-truth-v2", "simulated-inspection-v2"],
            key=widget_key(workspace, "ui_canonical_profile"), disabled=choice != "Canonical Synthetic projection",
        )
        if st.button("載入 Canonical projection", key=widget_key(workspace, "ui_load_canonical"), disabled=choice != "Canonical Synthetic projection"):
            try:
                root = Path(__file__).resolve().parents[2]
                commit_dataset(workspace, load_canonical_projection(root / "generated_data" / "model_dataset_v2" / canonical_profile))
            except (OSError, ValueError, KeyError) as exc:
                st.error(f"Canonical projection 載入失敗：{exc}")
        uploaded = st.file_uploader("CSV 上傳", type=["csv"], key=widget_key(workspace, "ui_csv_upload"),
                                    help="選擇上傳來源後按載入；失敗時保留上一份有效資料。")
        with st.expander("欄位／單位映射（上傳資料）"):
            st.caption("預設明確採 C 標準欄名及單位；非標準來源請提供映射，不猜測正式契約。")
            mapping = st.text_area(
                "自訂映射 JSON（可留白）", key=widget_key(workspace, "ui_mapping_json"),
                help='例如 {"columns":{"line_speed_m_min":{"column":"速度","unit":"mm/s"}}}',
            )
        if st.button("載入上傳 CSV", key=widget_key(workspace, "ui_load_upload"), disabled=choice != "上傳 CSV" or uploaded is None):
            commit_dataset(workspace, attempt_upload(uploaded.getvalue(), uploaded.name, mapping))
        if workspace.data.last_attempt is not None and not workspace.data.last_attempt.accepted:
            st.warning("本次載入未成功；請至資料檢查查看原因。上一份有效資料（若有）仍保留。")
        elif workspace.data.dataset is not None:
            st.caption("顯示已按載入確認的資料；選擇其他來源或檔案但未載入，不會覆蓋目前資料。")
        from c_dashboard.ui.replay_controls import render_temporal_config
        render_temporal_config(workspace)
        _render_filters(workspace)
        _render_context(workspace)
