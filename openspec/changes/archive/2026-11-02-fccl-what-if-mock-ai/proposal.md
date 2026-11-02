# Proposal

## Why

C1～C3 已提供可載入資料、SPC 監控與模型 Adapter 接點，但 What-if、品質預測、模型警報及調參建議仍是占位。此 Change 讓成員 C 可用明確標示的確定性 Mock 獨立完成互動與風險流程，並維持未來接入 B 正式模型的邊界。

## What Changes

- 提供與正式模型分離、具版本及可重現輸出的確定性公式 Mock Adapter，不重做 Random Forest 訓練。
- 實作固定已選材料區段的 What-if、線速滑桿及熟化／壓合參數模擬解鎖，顯示四項連續品質預測與外觀 NG 預測／風險的前後比較。
- 以可配置測試條件呈現預測超規、外觀 NG 風險、模型不可用、具體候選調整及無建議原因；將預測 Alarm 與既有實測 SPC Alarm 分別判定及標示。
- 將歷史實測及 SPC 輸入與 What-if 情境分離；情境只使用固定區段上下文及明確調整參數，不能改寫 CSV 或目前監控結果。
- 明確標示 Mock／測試規則及非因果性。正式品質允收、NG 門檻、多目標政策及 B 模型契約仍依 TCP-004 交接，不在本案決定。

## Capabilities

### New Capabilities

- `quality-scenarios`: 固定區段 What-if、確定性 Mock 預測、模型風險警報與可配置的模擬建議。

### Modified Capabilities

- `dashboard-workspace`: 將已交付占位提升為可操作 What-if 與模型預測警報，保留狀態、來源區分及局部降級。
- `csv-ingestion`: 明確定義缺失／不適用模型輸入時的預測降級，不合成品質實測值。
- `spc-monitoring`: 明確定義模型預測 Alarm 與既有 SPC 實測事件並列且互不覆寫。

## Impact

預計影響 `c_dashboard/adapters/`、`c_dashboard/state.py`、What-if／overview UI、純函式預測與建議服務，以及 C4+C5 測試與操作指南。沿用 C1～C3 的資料載入、固定 SPC 基準與事件服務；不修改 A／B 程式或正式契約，不實作 SHAP／Heatmap、CSV 回放或正式模型整合，也不控制真實機台。正式品質策略交接仍見 TCP-004。
