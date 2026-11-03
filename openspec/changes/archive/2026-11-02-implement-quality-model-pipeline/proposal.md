# Proposal

## Why

專案已具備可重現的 `generated_data/v2` 七表、資料與模型治理契約，以及可替換的 Streamlit Adapter／SHAP 呈現接點，但目前仍以確定性公式 Mock 運作，尚無可由資料重訓、驗證與載入的正式品質模型。本變更要把既有契約落實為可追溯的 canonical model dataset、五個逐目標模型及正式儀表板整合。

## What Changes

- 依 `define-seven-table-integration` 的既有契約實作並驗證 `build_model_dataset`，從七表建立逐目標 canonical dataset、lineage、排除原因與不可變資料 manifest。
- 以完整卷及時間隔離的既有 120／40／40 split，分別建立抗剝離、尺寸 MD、尺寸 TD、耐熱度四個迴歸資料集與外觀 NG 分類資料集，禁止目標、規格判定及漂移真值洩漏。
- 建立常數／線性或 Logistic 基準、Random Forest 初版 Champion，以及 HistGradientBoosting Challenger；XGBoost 只保留可插拔接點，LSTM／GRU、LightGBM、Autoencoder 不列入本次必要交付。
- 產生版本化 model bundle、registry、manifest、metrics、資料與程式 hash、逐目標可用性、穩定／漂移分層結果及回退資訊；合成訓練來源必須明示，不能宣稱真實產線模型。
- 以正式 Model Adapter 取代「未接入」狀態，但保留 C 公式 Mock 作獨立示範與降級路徑；模型或 manifest 不相容時不得偽造預測。
- 提供真正的樹模型 SHAP Summary／Dependence 解釋，沿用既有來源、manifest、尺度、樣本與分類標籤驗證接點。
- 將模型接入 Streamlit 的目前監控、固定區段 What-if、預測 Alarm 與 AI 圖表；不新增「當下預測良率」，不寫入 PLC／MES／機台，也不把 What-if 解讀為製程因果保證。

## Capabilities

### New Capabilities

- `quality-model-training`: 定義逐目標資料切分、基準／Champion／Challenger 訓練與比較、模型 artifact／manifest／metrics、重現性、回退及合成來源限制。

### Modified Capabilities

- `quality-scenarios`: 讓既有 What-if、五目標比較與預測 Alarm 可消費版本相容的正式模型 Adapter，同時保留 Mock 隔離與降級行為。
- `quality-visualization`: 讓既有 SHAP 呈現接點消費正式樹模型解釋，並驗證模型 manifest、來源、尺度、類別與資料相容性。
- `csv-ingestion`: 讓 Streamlit 消費由七表 builder 產生且具 lineage／版本的正式 canonical projection，不在 C 端重新 JOIN 七表。

## Impact

- 新增模型資料建置、訓練、評估、artifact 載入及 SHAP provider 模組，並擴充測試與依賴鎖檔。
- 影響 `generated_data/v2` 的唯讀消費方式、模型輸出目錄、`c_dashboard/adapters/`、`c_dashboard/visualization/`、資料來源 profile、Streamlit 模型選擇與錯誤提示。
- 前置契約來自 `define-seven-table-integration` 與 `define-model-selection-governance`；本變更不改寫七份來源 CSV、模擬規格或既有 C Mock 驗收。
- 初版模型只證明合成資料流程可運作；正式產線部署、線上自動學習、未來 horizon 預測及設備控制均不在本次範圍。
