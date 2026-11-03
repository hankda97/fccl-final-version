# Tasks

## 1. SPC 事件群組基礎

- [x] 1.1 建立由 `SpcResult.events` 投影事件群組的純函式，依品質目標、批號、連續子組與 break 邊界分組，產生穩定事件群 ID 且保留原始事件 ID。（SPC-08 Scenario 1）
- [x] 1.2 提供事件群摘要欄位，包括狀態、開始／最新時間、規則、子組數、事件數、最大偏離及來源識別，並以 fixtures 驗證重疊規則不重複計算。（SPC-08 Scenario 9）
- [x] 1.3 以 Canonical Synthetic 全量資料與 ROLL-0121 驗證大量原始事件可壓縮為可操作事件群，且事件守恆、不改動 baseline 與規則結果。（SPC-08 Scenario 6）

## 2. Alarm 呈現與導覽

- [x] 2.1 將 Overview Alarm 改為有界摘要，只呈現進行中事件、各目標最新歷史摘要、受影響目標與數量，不逐筆渲染歷史原始事件。（SPC-08 Scenario 9；WS-07 Scenario 2）
- [x] 2.2 在 SPC Tab 提供目標、批號、規則、狀態篩選、預設每頁 10 個事件群與可展開技術明細；同一原始事件不得在 Overview 與 SPC 重複完整顯示。（SPC-08 Scenario 9）
- [x] 2.3 調整主要版面，使 Canonical 大量歷史 Alarm 不妨礙直接進入 What-if、AI 圖表、SPC 與資料檢查，並加入 AppTest。（WS-07 Scenario 2）

## 3. 就緒狀態與 What-if

- [x] 3.1 建立可測試的功能就緒矩陣，區分 ready、computing、error，並為 Data、What-if、Heatmap、Summary、Dependence 提供原因與下一步。（WS-07；C-11；VIS-09）
- [x] 3.2 在側欄與主區明確區分「選定資料來源」與「已載入 dataset」，以 AppTest 驗證只選 Canonical radio 不得顯示為已載入。（WS-07 Scenario 3）
- [x] 3.3 What-if 顯示精確阻塞原因與操作指引；Canonical ROLL-0124 可執行正式 Adapter 情境比較，Mock 維持明確示範標示。（C-11 Scenario 3）

## 4. Heatmap 可解讀摘要

- [x] 4.1 從 Heatmap cell result 建立純函式摘要，為每個品質目標列出最強正相關、負相關與樣本數，並驗證 tie、缺值與排序。（VIS-08 Scenario 4）
- [x] 4.2 加入版本化品質方向 metadata：higher-is-better、lower-is-better、bounded／target-centered，且外觀 1=NG。（VIS-08 Scenario 4）
- [x] 4.3 在 Heatmap 顯示就緒狀態、文字摘要與樣本數；無資料時提供操作指引且不得出現 `No options to select`。（VIS-08 Scenario 9）

## 5. SHAP 就緒與說明

- [x] 5.1 為 Summary／Dependence 顯示用途、provider 就緒狀態、阻塞原因及下一步，並以 AppTest 覆蓋未載入、Canonical+Mock、Canonical+正式模型及缺 manifest。（VIS-09 Scenario 5）
- [x] 5.2 只有 ready 狀態可送出 SHAP 請求；保留 Mock 的示範標示與正式 Tree SHAP 的 Summary／Dependence 圖、樣本、方向及限制說明。（VIS-09 Scenario 5）

## 6. 驗證與紀錄

- [x] 6.1 補齊 Alarm、SPC、導覽、What-if、Heatmap、SHAP 的單元與 Streamlit 測試，涵蓋 Canonical 極端大量事件案例。（以上需求）
- [x] 6.2 執行資料、Mock、正式模型、CSV、Canonical、SPC、What-if、Heatmap、SHAP 回歸測試、`git diff --check` 與 `openspec validate improve-dashboard-alarm-and-analysis-usability --strict`，修復回歸。（以上需求）
- [x] 6.3 依 AGENTS.md 同步 `docs/DEVELOPMENT_LOG.md`、必要的 `docs/DECISION_LOG.md` 與 TCP-003／004／006 狀態，清楚記錄 Synthetic／Mock 來源、限制、測試證據與 Git 未提交狀態。（流程要求）

## Workflow follow-up

- 使用者確認並驗收後，才執行 OpenSpec Sync／Archive；本 Change 不自行歸檔。
- Git Commit／Push 不在本次授權範圍。
