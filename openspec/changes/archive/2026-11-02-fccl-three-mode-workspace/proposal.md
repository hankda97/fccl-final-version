# Proposal

## Why

C1～C7 已歸檔並交付單一品質分析與歷史回放工作區；測試線參數實驗與產線擾動／量測雜訊具有不同資料生命週期，直接混入既有 CSV／SPC／What-if 容易混淆來源。本次修訂既有提案，保留模式 A 為核心、對齊 C7，規劃三模式導航與 C 端獨立模擬來源的隔離接點。

## What Changes

- 預設模式 A「AI 品質預測與關鍵因子分析」，保留 C1～C7 的歷史 CSV、五目標預測、SPC、兩類 Alarm、固定區段 What-if、Pearson Heatmap、SHAP Summary／Dependence 及可信可得時間回放；七表投影與正式模型接點保持，正式交付仍留 C9，不宣稱已完成正式 JOIN／模型整合。
- 新增模式 B「測試線動態參數實驗」、模式 C「現場產線波動與動態線速補償」的導航與清楚標示待交付的入口。本 Change 只交付外殼、共用接點及隔離驗證，不實作完整模擬。
- 將每模式的資料、篩選、回放／實驗識別、What-if、SPC 基準／事件、Alarm、模型與圖表結果隔離；重用既有服務及 Model Adapter，不共享可變業務狀態、不改 A／B 正式資料契約。
- 沿用已交付 C7 的游標、計時與防未來資訊規則；應用模式選擇與 A 內快照／回放選擇分開。切出 A 暫停並保留進度，返回不自動播放；不把歷史列投入實驗、不啟動模擬或寫入機台。
- 組長 `generated_data/v2/` 七份 CSV 唯讀、不要求 A 重產、不改 B 正式模型契約。B／C 額外事件、訊號與模擬品質由 C 的後續獨立模擬器產生，使用獨立來源／run／儲存邊界及 Synthetic／Mock 標籤，不回寫七表。正式模型輸出、公式 Mock、模擬量測、隱藏真值與候選分開，不宣稱製程因果效果。
- 在 Roadmap 另列 `fccl-testline-experiment-simulation` 與 `fccl-production-disturbance-compensation` 的範圍、依賴及驗收方向，不建立其 active Changes，不將新增工作併入原 39 項。
- 三模式功能／呈現與模擬器具體設計仍為 Proposed；本次只更新既有規劃，未同步主規格。上述隔離是 C 端擬採約束，不將涉及共同契約的細節視為全組批准，後續 Apply／Archive 需另行授權並核對討論結果。

## Capabilities

### New Capabilities

- `mode-workspace`: A／B／C 導航、模式工作狀態及來源／結果隔離、未接入模擬 Port、C7 相容性。

### Modified Capabilities

- `dashboard-workspace`: WS-01 在模式 A 保留四 Tabs／全部已交付能力並加外層模式導航；WS-02 擴充為各模式獨立保留／重設，避免切換模式清空或污染工作內容。WS-03／04 保持既有需求，不以新增模式取消來源標示或降級邊界。

## Impact

未來可能新增 `c_dashboard/workspace_modes/` 與模式導航 UI，局部調整 app 組合、Session State 轉接及共用 widget key；重用 data／quality／spc／visualization／replay 服務與現有 ModelAdapter。本 Change 只提供不可用模擬 Port 與明示測試替身，不交付模擬器、持久儲存或新增 SQLite 相依；獨立 CSV／SQLite 的取捨及建議見 design D8，實作留 B／C 後續案。預期無新模型／硬體依賴，不訓練模型、不生成或覆寫七表、不 JOIN 七表。

C7 已存在於 `openspec/changes/archive/2026-11-02-fccl-csv-replay/`（23／23、54 情境）；原任務進度保持 **29／39**。本案仍為 5 ADDED＋2 MODIFIED、0／20 任務；情境由 26 增為 28，僅因補回 WS-01／02 的 C7 正式情境，沒有刪除三模式原有行為。模式字母 B／C 不改組員 A／B 正式責任；C 端模擬資料生成另案處理。提案來源／待決事項見 TCP-007～009；本輪不修改 Python、主 specs 或 Archive。
