"""Data preview and validation presentation; does not compute SPC or models."""

from dataclasses import asdict

import pandas as pd
import streamlit as st

from c_dashboard.data.loader import input_eligibility
from c_dashboard.data.session import selected_rows
from c_dashboard.state import WorkspaceState


def render_data_inspection(workspace: WorkspaceState) -> None:
    st.subheader("CSV 匯入與欄位驗證")
    dataset = workspace.data.dataset
    attempt = workspace.data.last_attempt
    if attempt is not None and not attempt.accepted:
        st.error(f"本次未載入：{attempt.source_name}。" + ("下方仍為上一份有效資料。" if dataset else "尚無有效資料。"))
        attempt_issues = [i for i in attempt.issues if workspace.replay.mode != "replay" or i.row is None]
        st.dataframe(pd.DataFrame([asdict(item) for item in attempt_issues]), hide_index=True)
        if not attempt.raw_frame.empty and workspace.replay.mode != "replay":
            with st.expander("失敗匯入的原始列預覽"):
                st.dataframe(attempt.raw_frame.head(200))
    if dataset is None:
        st.info("尚未匯入資料。請於側欄載入 C 專用 Mock、canonical projection 或上傳 CSV。")
        return
    source_label = ("C 專用 Mock（非真實產線）" if dataset.source_kind == "mock" else
                    "Synthetic canonical projection（非真實產線）" if dataset.source_kind == "canonical-projection" else
                    "上傳資料（來源待確認，非已驗證產線資料）")
    st.success(f"已載入 {dataset.source_name} · {len(dataset.frame)} 列 · 映射版本 {dataset.profile.version}")
    st.caption(source_label)
    view = selected_rows(workspace)
    st.caption(f"目前篩選 {len(view)} 列；保留來源列號與本地樣本識別。")
    st.dataframe(view.head(200), hide_index=True)
    if len(view) > 200:
        st.caption("預覽顯示前 200 列；篩選與輸入檢查使用完整篩選範圍。")
    st.subheader("資料問題")
    issues, raw_preview = dataset.issues, dataset.raw_frame
    if workspace.replay.mode == "replay":
        from c_dashboard.replay.controller import snapshot_for
        snapshot = snapshot_for(workspace)
        from c_dashboard.replay.temporal import IDENTIFIERS
        raw_preview = snapshot.raw
        duplicate_rows = set(snapshot.rows.loc[snapshot.rows.duplicate_record, "source_row"])
        issues = [i for i in issues if i.row is None or
                  ((i.row, "__identity__") in snapshot.released and
                   (i.field is None or i.field in IDENTIFIERS or (i.row, i.field) in snapshot.released)
                   and (i.code != "DUPLICATE_RECORD" or i.row in duplicate_rows))]
    if issues:
        st.caption("回放僅列出已可得欄位的問題；快照顯示完整驗證。原始數值不補造。")
        st.dataframe(pd.DataFrame([asdict(item) for item in issues]), hide_index=True)
        with st.expander("原始 CSV 預覽（未做補值或更動）"):
            st.dataframe(raw_preview.head(200))
    else:
        st.info("目前未發現已實作檢查範圍內的資料問題；不代表品質合格。")
    eligibility = input_eligibility(view)
    st.subheader("功能輸入完整度")
    st.caption("僅檢查可供後續功能使用的輸入；不代表已執行 SPC、模型或品質判定。")
    st.write(f"有效識別列：{eligibility['view_rows']}；C 預設特徵完整列：{eligibility['prediction_input_rows']}")
    rows = [
        {"目標": name, "有效實測列": count,
         "具子組識別的輸入列（非 SPC 判定）": str(eligibility["grouped_quality_rows"].get(name, "不適用"))}
        for name, count in eligibility["quality_rows"].items()
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
