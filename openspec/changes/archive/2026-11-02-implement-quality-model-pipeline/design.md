# Design

## Context

參見 [proposal.md](proposal.md) 的動機。現況有可重現 v2 七表與 metadata、兩個尚未完成實作的資料整合／模型治理 Change，以及已驗收的 C 端 Mock Adapter、What-if、SHAP 呈現接點與 Streamlit 狀態管理。正式七表 projection、訓練程式、模型 artifact、正式 Adapter 與真正 SHAP Provider 均不存在。

v2 提供 200 卷、20,000 canonical lamination 區段及固定 120／40／40 卷級分割；`quality_timeseries` 是完整 `synthetic_ground_truth`，`quality_inspection` 是稀疏 `simulated_inspection`。任何初版成果都只能標示為合成模型。

## Goals / Non-Goals

**Goals:**

- 將既有七表與模型治理契約落實成可重現、逐目標、無洩漏的完整 pipeline。
- 產生基準、Random Forest Champion、HistGradientBoosting Challenger、模型 registry／manifest／metrics 與可回退 artifact。
- 以不破壞 C1～C7 Mock 行為的方式接入正式 Adapter 與真正樹模型 SHAP。
- 讓資料、模型、解釋與 UI 版本可獨立驗證及失效，不把 Synthetic 結果冒充產線證據。

**Non-Goals:**

- 不實作 XGBoost、LightGBM、LSTM、GRU、Autoencoder 或未定義 horizon 的未來預測。
- 不建立線上自動學習、即時重訓、PLC／MES／機台寫入或「當下預測良率」。
- 不修改七份 v2 來源 CSV、合成公式、產品示範規格或既有 C Mock 驗收結果。
- 不以合成 test 分數批准真實產線部署或因果調參效果。

## Decisions

### D1：三階段門檻式交付

實作分為 Dataset、Training、Integration 三個門檻。後一階段只有在前一階段的契約測試及 manifest 驗證通過後才能開始；單次 CLI 可依 tasks 逐段執行，但不得因最終 UI 需求跳過資料／模型驗證。

替代方案是直接從 `quality_timeseries.csv` 訓練並接 UI；此方案無法驗證七表 lineage、抽檢 availability、規格版本與重測規則，因此拒絕。

### D2：來源表唯讀，輸出版本化 canonical projection

建立獨立 ML pipeline 模組，讀取七表及 `metadata.json`，不覆寫來源。builder 以 lamination 區段及 `[start,end)` MD 重疊為 synthetic 錨點，以有效區段檢驗為 inspection 錨點；數值特徵採重疊長度加權，保留來源 segment IDs、coverage、label timestamp、排除 code 與 hash。

每次建置輸出一份不可變 dataset manifest、lineage／排除摘要及五個逐目標 projection。coverage 門檻不寫死在 C UI：v2 依 metadata／SKILL 使用 0.98，manifest 必須記錄實際值；舊 `define-seven-table-integration/design.md` 的 0.99 預設在 Apply 前需同步校正，避免雙重契約。

### D3：兩種標籤 profile 絕不混訓

初版建立兩種可辨識 profile：

- `synthetic-ground-truth-v2`：使用完整 20,000 區段，作 pipeline、模型比較與 Streamlit 正式 artifact 介面驗證的主要 profile。
- `simulated-inspection-v2`：依逐目標 availability 使用模擬抽檢，驗證稀疏標籤、重測與實際取樣形態；不得與完整真值混成同一訓練分母。

正式 UI 預設載入哪個 artifact 必須由 registry 明確指定並顯示來源。重測歷史全部保留；`invalid`／`superseded` 不可作標籤，具 parent／reason 的最新有效重測可被選取並在 lineage 保留原始關係，缺 metadata 的衝突全部排除。

### D4：分割來源唯一且不可降級

split 只接受 `roll_master.dataset_split` 與 dataset manifest 的 120／40／40 完整卷集合。builder 驗證卷互斥、時間順序、列數與 hash；任何不一致立即失敗，不退回逐列 random split。前處理、缺值策略及特徵選擇只在 train 擬合；validation 選超參數、分類門檻及校準，test 每個 model version 只作最終報告。

漂移真值只能在預測完成後以 evaluation sidecar 分層統計，不得出現在特徵矩陣、前處理或調參輸入。

### D5：逐目標 pipeline 與共同 registry

四個連續目標及一個分類目標各自擁有資料列、前處理、基準、Champion、Challenger 與指標；不用多輸出模型強迫五標籤同列完整。數值前處理與 estimator 封裝為同一可信 bundle，確保訓練與推論欄位順序一致。

迴歸基準使用 train mean 與線性模型；分類基準使用 train prevalence 與 Logistic 模型。Random Forest 是初版 Champion，HistGradientBoosting 是必要 Challenger。初版不因 Challenger 單一分數較高自動替換 RF；所有升版條件與理由寫入 registry。

### D6：獨立 ML 依賴與可信 artifact 邊界

新增可讀的 ML 依賴來源與鎖檔，至少包含與現有 pandas／numpy 相容的 scikit-learn、joblib、shap 及測試工具；不把 XGBoost／深度學習加入必要依賴。C UI 依賴可引用已驗證 ML runtime，但不在 Streamlit 啟動時訓練。

artifact 位於專案設定的可信目錄並以 SHA-256 與 manifest 驗證。CSV／UI 上傳永遠不能觸發 joblib 反序列化。registry 以相對路徑指向各目標 Champion／Challenger；載入失敗時逐目標降級，不掃描任意檔案尋找替代模型。

### D7：沿用 C Adapter 協定，以 optional manifest hook 擴充

正式 Adapter 實作既有 `ModelAdapter.describe/predict`，保持 Mock 與現有測試相容；另提供目前 workspace 已能讀取的 optional manifest／explanation hook，不強迫公式 Mock 支援 SHAP。Adapter 在批次推論前一次驗證 feature schema、順序、單位、來源 profile、模型 hash 與套件版本，輸出維持輸入 `sample_id` 順序。

模型選擇在 UI 使用明確來源選項：正式 Synthetic artifact、C 公式 Mock、未接入。正式模型失敗不自動切換 Mock；使用者主動切換才建立新結果與狀態 generation。

### D8：Tree SHAP Provider 與有界計算

正式 Explanation Provider 只從已驗證的同一 Champion bundle 建立解釋器，背景資料由 train projection 以固定 seed 抽樣並記錄 hash。Summary／Dependence 的請求與回應沿用 C6 envelope；分類由 `classes_` 及 manifest 明確定位標籤 1，尺度記為 probability、raw margin 或 log-odds，不猜陣列位置。

UI 傳入有界資料切片，Provider 不回讀全域 CSV。模型、manifest、來源、feature、選項或回放 generation 改變即使舊結果失效；錯誤只影響 SHAP 圖區。

### D9：評估、通過條件與可重現性

metrics 同時保存逐模型、逐目標、split 與穩定／漂移分層結果，以及資料筆數、類別數、門檻與推論時間。驗收不使用任意「高準確率」門檻；必要條件是相對簡單基準、無洩漏、卷級 holdout、指標可計算、序列化前後一致及同 seed 重跑的結構／指標容差一致。

模型 hash 可能因套件或平台序列化細節不同而改變，因此重現性以資料 hash、設定、特徵順序、分割、超參數及預測／指標容差為主要證據；相同鎖定環境另比較 artifact hash。

## Risks / Trade-offs

- **[合成公式可被模型輕易學習，分數過度樂觀]** → 明示 Synthetic，分層報告、比較簡單基準，禁止外推為產線效能。
- **[完整真值與模擬抽檢混用造成標籤洩漏或樣本灌水]** → 分開 profile、manifest、artifact namespace 與 metrics，禁止跨 profile 混訓。
- **[既有 coverage 0.98／0.99 文件不一致]** → v2 由 metadata 取 0.98 並寫入 manifest，Apply 時同步既有 design／驗證證據。
- **[資料相鄰區段高度相關導致評估過度樂觀]** → 只按完整卷與時間切分，所有候選共用 holdout。
- **[joblib 反序列化可執行任意程式]** → 只載入可信路徑、驗證 hash／manifest，UI 不接受模型上傳。
- **[SHAP 延遲或記憶體過高]** → 固定背景、限制樣本、快取 explainer、圖區隔離及可重試狀態。
- **[正式 Adapter 改動破壞 C1～C7]** → 保留既有 Protocol 與 Mock，新增 optional hook，先跑完整 C regression 再啟用正式來源。

## Migration Plan

1. 完成 builder 與兩種 projection，驗證 v2 七表 hash、lineage、排除原因及 120／40／40 卷集合；來源仍唯讀。
2. 建立隔離 ML 環境與鎖檔，訓練基準、RF、HGB，輸出 staging registry／manifest／metrics，不影響目前 UI。
3. 驗證序列化前後預測、相同 seed 重跑、逐目標及分層指標；只有通過者標為 Synthetic Champion。
4. 實作正式 Adapter／SHAP Provider，以 feature flag 或明確模型來源選項接入；預設仍可回到 C Mock。
5. 跑 ML、Adapter、SHAP 與完整 C1～C7／三模式回歸測試，再將 registry 設為可選正式 Synthetic 來源。
6. 若整合失敗，移除／停用正式 registry 選項並回退至既有 C Mock／Unavailable Adapter；不需修改七表或歷史 SPC 資料。
