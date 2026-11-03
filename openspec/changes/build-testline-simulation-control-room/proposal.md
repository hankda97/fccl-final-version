# Proposal

## Why

目前的 A／B／C 導覽、歷史 CSV 分析與一次性回放，無法形成使用者要驗收的「可持續運轉、可調參、可觀察延遲影響」測試線控制台；同時現有 Synthetic v2 與五目標模型未涵蓋乾膠厚度、排風量等正式調參特徵。現在需要先鎖定單一 Mode B 產品面，再以可驗收 Gate 逐步補齊資料、模型、模擬器、製程 SPC 與正式整合。

## What Changes

- **BREAKING**：使用者可見導覽改為單一「測試線模擬控制台」；隱藏原模式 A／C 入口，但保留可重用的模型、What-if、Heatmap、資料與 SPC 服務，不刪除舊 artifact 或程式碼。
- 先交付 Gate 0 可操作 Streamlit 靜態 UI 原型，使用固定 fixture 展示產線位置、產品規格、配方標準、數字調參、三張監控圖、四項品質預測、Alarm、What-if、Heatmap 與 Run 紀錄；所有數值須標為原型，不冒充執行中模擬。
- Gate 1 建立單一產品 `FCCL-DEMO-001`、單一配方 `SIM-RECIPE-3.0`、setpoint／actual、材料區段、參數事件、品質延遲、Run 檔案與相容版本的正式契約，並同步 AGENTS.md／SKILL.md。
- Gate 2 產生 Synthetic v3：200 卷、約 20,000 個區段、120／40／40 完整卷切分，加入乾膠厚度、排風量及三製程參數；只訓練抗剝離、MD、TD、耐熱度四個連續目標，外觀 v2 artifact 保留但不進新控制台。
- Gate 3 建立每 5 模擬秒產生訊號的連續測試線、穩態與六種固定 seed 漂移情境、站別／材料傳遞延遲、每 30 模擬秒或適用參數後的品質預測，以及厚度 X-bar／R 與其他訊號 I-MR／EWMA 製程 SPC。
- Gate 4 整合正式控制台：首頁三張關鍵圖與四項品質預測、警報事件群、詳細 SPC、按需 Heatmap／What-if、Run 紀錄與效能降級；SHAP Summary／Dependence 不在一般導覽中顯示。
- Run 僅寫入本機 `runtime_data/testline_runs/<run_id>/`，不中斷既有訓練資料，也不寫入 PLC、MES 或真實設備；新 Run 不會自動成為訓練資料。

## Capabilities

### New Capabilities

- `testline-simulation`: 連續測試線的模擬時鐘、站別材料流、參數事件、固定情境、延遲與品質釋出行為。
- `process-signal-monitoring`: 乾膠厚度 X-bar／R、溫度／風量／線速／壓力 I-MR／EWMA、獨立基準、狀態分級與事件生命週期。
- `testline-run-management`: 本機 Run 建立、checkpoint、完成／中斷、manifest、雜湊、檢視與訓練隔離契約。

### Modified Capabilities

- `mode-workspace`: 將使用者可見三模式導航改為單一 Mode B 測試線控制台，保留內部舊能力但不混用狀態。
- `dashboard-workspace`: 定義 Gate 0 原型及正式控制台的資訊架構、數字輸入、首頁摘要與分頁配置。
- `data-generation`: 將合成資料契約升級為 v3 製程特徵、材料區段與固定資料量／切分。
- `quality-model-training`: 改為 v3 四連續目標模型、RF Champion／HGB Challenger、模型支援範圍與推論時點。
- `quality-scenarios`: 將 What-if 固定於已完成材料區段，與 live run 隔離，候選值須回填並確認後才套用。
- `quality-visualization`: Heatmap 改以已完成材料區段聚合，支援 v3 reference／current run，並暫停一般導覽的 SHAP。
- `spc-monitoring`: 區分品質 SPC 與新增製程 SPC，明定配方目標、產品規格、管制界限及 Alarm 復歸邊界。

## Impact

- 影響 Streamlit 導覽與版面、合成資料生成器、canonical／v3 schema、模型訓練與 artifact manifest、模擬器、SPC／Alarm、What-if／Heatmap、Run 儲存及相應測試。
- 需更新 AGENTS.md、SKILL.md 與正式 OpenSpec 契約；`runtime_data/` 必須排除 Git 追蹤。
- 不接真實生產資料、PLC 或 MES；不提供預測良率、外觀新模型、早期站別品質模型、SHAP 一般入口、Alarm 確認／靜音／工單或中斷 Run 續跑。
