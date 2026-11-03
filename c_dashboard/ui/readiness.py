"""Pure capability-readiness projection shared by dashboard panels."""

from dataclasses import dataclass
from typing import Mapping

from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS


@dataclass(frozen=True)
class CapabilityReadiness:
    status: str
    reason: str
    next_step: str

    @property
    def ready(self) -> bool:
        return self.status == "ready"


ReadinessMatrix = Mapping[str, CapabilityReadiness]


def build_readiness_matrix(workspace, rows, segment_options, adapter_info, explanation_info) -> dict[str, CapabilityReadiness]:
    """Return deterministic readiness for each user-visible analytical capability."""
    dataset = workspace.data.dataset
    if dataset is None:
        data = CapabilityReadiness("error", "尚未載入已確認的資料集。", "在側欄選擇來源後按下對應的載入按鈕。")
    elif rows.empty:
        data = CapabilityReadiness("error", "資料集已載入，但目前批次／時間篩選沒有資料。", "放寬側欄的批次或時間範圍。")
    else:
        data = CapabilityReadiness("ready", f"已載入 {len(rows)} 列目前可見資料。", "可使用已就緒的分析功能。")

    if not data.ready:
        what_if = CapabilityReadiness("error", data.reason, data.next_step)
    elif not segment_options:
        what_if = CapabilityReadiness("error", "目前資料沒有可用的批號／材料區段識別。", "檢查 product_batch、segment_id 與 sample_id 欄位及目前篩選。")
    elif not adapter_info.available:
        what_if = CapabilityReadiness("error", "選定的模型 Adapter 不可用。", "在側欄模型來源選擇 C 公式 Mock 或可用的 Synthetic 正式 artifact。")
    else:
        what_if = CapabilityReadiness("ready", "區段識別與模型 Adapter 均可用。", "選擇區段並調整允許的模擬參數。")

    feature_count = sum(name in rows for name in FEATURE_UNITS)
    target_count = sum(name in rows for name in TARGET_UNITS)
    if not data.ready:
        heatmap = CapabilityReadiness("error", data.reason, data.next_step)
    elif not feature_count or not target_count:
        heatmap = CapabilityReadiness("error", "缺少可配對的製程／環境特徵或品質目標。", "檢查欄位映射與品質量測欄位。")
    else:
        heatmap = CapabilityReadiness("ready", f"找到 {feature_count} 個特徵與 {target_count} 個品質目標。", "選擇欄位後查看相關摘要。")

    if not data.ready:
        shap = CapabilityReadiness("error", data.reason, data.next_step)
    elif not adapter_info.supports_shap:
        shap = CapabilityReadiness("error", "目前模型來源未宣告 SHAP 能力。", "選擇含相容 manifest 的 Synthetic 正式 artifact。")
    elif not explanation_info or not explanation_info.available or explanation_info.manifest is None:
        detail = getattr(explanation_info, "message", "") if explanation_info else ""
        reason = "SHAP Provider 或相容 manifest 尚未就緒。" + (f" {detail}" if detail else "")
        shap = CapabilityReadiness("error", reason, "檢查模型 artifact、registry 與 explanation manifest。")
    else:
        shap = CapabilityReadiness("ready", "模型與 SHAP Provider 已宣告可用。", "選擇 Summary 或 Dependence 圖與品質目標。")

    return {"data": data, "what_if": what_if, "heatmap": heatmap,
            "summary": shap, "dependence": shap}


def with_computing(state: CapabilityReadiness, reason: str) -> CapabilityReadiness:
    """Project a ready capability into the transient computing state."""
    return CapabilityReadiness("computing", reason, "請等待本次計算完成。") if state.ready else state


def render_readiness_matrix(matrix: ReadinessMatrix) -> None:
    """Render a compact status strip without hiding reasons or next actions."""
    import streamlit as st

    st.markdown("#### 功能就緒狀態")
    labels = {"data": "Data", "what_if": "What-if", "heatmap": "Heatmap",
              "summary": "SHAP Summary", "dependence": "SHAP Dependence"}
    icons = {"ready": "🟢", "computing": "🟡", "error": "🔴"}
    for name, column in zip(labels, st.columns(len(labels))):
        item = matrix[name]
        column.markdown(f"{icons[item.status]} **{labels[name]}**")
        column.caption(item.reason)
        if not item.ready:
            column.caption("下一步：" + item.next_step)
