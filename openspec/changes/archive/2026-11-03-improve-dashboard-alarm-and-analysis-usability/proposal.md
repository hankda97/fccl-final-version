# Proposal

## Why

Canonical Synthetic 資料一次產生數千筆有效 SPC 歷史事件，目前 Overview 與 SPC Tab 將每筆事件展開成紅色卡片，造成 alarm fatigue、頁面過長並把 What-if／AI 圖表入口推到難以找到的位置。同時「選取來源」容易被誤認為「已載入資料」，使 What-if、Heatmap 與 SHAP 只呈現暗色停用元件或模糊空狀態，無法引導使用者完成模擬分析。

## What Changes

- 保留所有原始 SPC 事件及規則判定供稽核，但將連續、相同脈絡的訊號彙整為可追溯事件群；Overview 只顯示目前狀態、影響目標、事件群數與最近事件，不再逐筆展開完整歷史。
- 完整 SPC 歷史只在 SPC Tab 以摘要、篩選、有限筆數／分頁及可展開技術細節呈現；同一事件不得因 Overview 與 SPC Tab 重複渲染成兩張紅色 Alarm。
- 將功能分頁置於不會被大量 Alarm 推離主要操作區的位置，紅色只用於目前／最新且需注意的狀態，歷史事件採較低干擾的呈現。
- 增加一致的資料、模型與分析就緒狀態，明確區分「已選來源」與「已成功載入」；不可用時顯示原因及可執行的下一步，而非只有暗色控制項。
- What-if 在 Canonical 資料與相容 Adapter 就緒時顯示區段、參數與比較；未就緒時指出需載入資料、清除無效篩選或選擇模型來源，且不以 Mock 冒充正式模型。
- Heatmap 增加每個品質目標的最強正／負相關摘要、係數與有效配對數，並依品質規格方向避免把單純正負相關誤稱為改善；保留「相關不代表因果」。
- SHAP Summary／Dependence 增加明確能力狀態、阻塞原因與下一步；只有正式 Synthetic artifact 與相容資料可顯示真正 SHAP，Mock 維持不可用且不得偽造解釋。
- 維持純 Synthetic／Mock 模擬定位，不接入真實設備、不新增預測良率、不變更模型 Champion 或 SPC 原始判定規則。

## Capabilities

### New Capabilities

無。

### Modified Capabilities

- `dashboard-workspace`: 調整主要操作順序、來源載入／模型／分析就緒狀態與可操作下一步，避免功能入口被大量 Alarm 淹沒。
- `spc-monitoring`: 在不刪除原始事件的前提下定義事件群、目前狀態、歷史明細與去重呈現契約。
- `quality-scenarios`: 明確規範 What-if 的資料／區段／Adapter 就緒條件、空狀態診斷與來源一致性。
- `quality-visualization`: 增加 Heatmap 可讀相關摘要及 SHAP 能力／阻塞／下一步狀態，避免停用元件被誤認為已完成計算。

## Impact

- 主要影響 `c_dashboard/ui/overview.py`、`spc_alarm.py`、`spc_panel.py`、`tabs.py`、`layout.py`、`whatif_panel.py`、`visualization_panel.py`，以及 SPC 事件呈現投影與圖表狀態控制器。
- 原始 `SpcEvent`、固定 baseline、SPC 規則、正式模型 artifact、What-if 模型輸入及 SHAP 計算核心維持不變；新增的事件群是呈現／互動投影，不取代稽核事件。
- 需擴充 Streamlit AppTest、SPC 彙整單元測試、Heatmap 摘要測試、正式／Mock／未載入來源生命週期測試及完整回歸。
- 不新增外部服務或必要執行期依賴；不進行 Git Commit／Push、OpenSpec Sync／Archive 或 Python 實作，直到使用者另行啟動 Apply。
