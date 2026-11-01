---
name: fccl-quality-spc
description: 建置本專案的 FCCL 七表模擬資料、品質預測、模型比較、SHAP、SPC 與 Streamlit 調參介面；適用於本專案的資料生成、整合、訓練與驗證。
---

# FCCL 技術實作規範

狀態：使用者已授權本機實作的 v0.2 工作草案；跨組正式契約仍待團隊確認。先閱讀 AGENTS.md 與相關 OpenSpec Change。

## 1. 工具鏈與檔案

- 採 Python 3.11 與 venv；資料處理用 numpy、pandas，模型用 scikit-learn、joblib，解釋用 shap，圖表用 matplotlib、seaborn、plotly，介面用 streamlit，驗證用 pytest。
- 實作時確認相容版本並鎖定依賴；模型 manifest 記錄 Python 及套件版本，不依賴浮動 latest。
- 保留資料生成、模型訓練及應用程式三個入口；共用的 schema、整合、特徵、SPC、模型 adapter 與驗證邏輯抽成模組。
- v2 來源資料固定輸出至 `generated_data/v2/`，包含七份 CSV 與 `metadata.json`。既有 `raw data/` 是歷史基準，不覆寫、不作 v2 預設輸入。
- 模型預定輸出為 `artifacts/model_bundle.joblib`、`artifacts/manifest.json`、`artifacts/metrics.json`、`artifacts/plots/`；只有可信專案路徑可載入序列化模型。
- 隨機生成、抽樣與模型均使用可設定 seed；預設 42。時間含時區、CSV 使用 UTF-8，檔案路徑可設定。

## 2. 七表來源契約與 canonical model table

七份來源表保留各自粒度，不直接以寬 JOIN 取代來源資料。模型訓練前建立版本化 canonical model table；一列代表同一 `root_roll_id` 上一個完成壓合的材料 MD 區段。`drift_ground_truth.csv` 僅供驗證，所有事件識別、方向、強度與區間禁止進入模型特徵。

| 來源檔 | 主要粒度 | 用途 |
|---|---|---|
| `roll_master.csv` | 一列一卷 | 產品、時間、分割、改善週期與卷級摘要 |
| `process_segments.csv` | 一列一站別材料區段 | 塗佈、熟化、壓合與環境觀測 |
| `process_traceability.csv` | 一列一站別材料區段 | 上下游區段、材料 MD 與設備追溯 |
| `quality_timeseries.csv` | 一列一最終材料區段 | 完整合成真值，供生成驗證與模擬研究 |
| `quality_inspection.csv` | 一列一檢驗事件／特性 | 模擬線上或實驗室抽檢標籤 |
| `quality_specifications.csv` | 一列一產品／版本／特性 | 規格、單位、測試方法與有效期 |
| `drift_ground_truth.csv` | 一列一漂移事件 | 生成驗證專用，不得作模型特徵 |

### 2.1 三站材料 MD 區間對齊

- 站別區段以 `root_roll_id`、`material_md_start_m`、`material_md_end_m` 表示，採半開區間 `[start, end)`；必須滿足 `end > start`、同站不重疊且落在卷長內。
- canonical 區段以最終壓合區段為錨點。與每個上游區段的重疊長度為 `max(0, min(end)-max(start))`，數值特徵以重疊長度加權，識別欄保留所有來源 ID。
- 每站覆蓋率 `covered_length / canonical_length` 預設必須至少 0.98；低於門檻或存在材料斷裂時，記錄 `ALIGNMENT_INCOMPLETE`，該站特徵不可靜默補成完整資料。
- 產出穩定 `aligned_sample_id`、各站來源區段清單、覆蓋率與對齊版本，禁止只用最近時間戳配對。

### 2.2 標籤來源與整卷檢驗

- 正式 inspection-supervised 模型標籤來源：抗剝離、尺寸 MD／TD、耐熱度採有效實驗室區段檢驗；外觀採線上 `appearance_ng_flag`。每個目標分別建資料集，不要求同列五個標籤都存在。
- `quality_timeseries.csv` 的完整數值標示 `label_source=synthetic_ground_truth`，只供合成資料驗證、方法開發及壓力測試；使用時必須在 manifest 明確標示，不可宣稱為實測模型。
- 整卷資格檢驗保留 `label_scope=roll`，只供卷級放行或獨立驗證，禁止複製到所有區段當訓練標籤。若未來要分配到區段，必須另立弱監督規格及驗證。
- `quality_label_available=1` 表示該列至少有一個通過有效性檢查的品質標籤；另設 `peel_label_available`、`md_label_available`、`td_label_available`、`heat_label_available`、`appearance_label_available`。目標值空白時其 availability 必須為 0，訓練時排除，不得填成 0 或以統計值插補。

### 2.3 規格 pivot

- 規格以 `product_id + spec_version + characteristic` 唯一識別，並以檢驗時間匹配 `effective_from`／`effective_to`；不得直接取全表最新版本。
- characteristic 必須經版本化 mapping 轉成 canonical 欄位，pivot 後保留 `lsl`、`usl`、`target`、`unit`、`test_method` 與 `spec_version`。同鍵重複或單位不一致時拒絕整合。
- 找不到有效規格時輸出 `SPEC_NOT_FOUND`，保留數值但不宣稱合格，不用模型預測或其他列反推規格。
- 產品規格與 SPC 管制界限分開管理；模擬規格明確標示為示範值，不能宣稱為通用 FCCL 或工廠標準。

### 2.4 重複檢驗與外觀旗標

- 檢驗唯一鍵至少包含 `inspection_id`；同一取樣事件以 `sampling_event_id` 關聯。重測必須提供 `is_retest=1`、`parent_inspection_id`、`retest_reason`、`validity_status` 與完成時間。
- 正式標籤先排除 `invalid`／`superseded`，再依已批准、完成時間最新的有效重測取代原測；若同優先級仍有多筆且缺少重測關係，輸出 `DUPLICATE_INSPECTION_AMBIGUOUS` 並排除該標籤，不任意平均。
- `appearance_ng_flag` 是外觀模型真值，0=OK、1=NG；無 waiver／disposition 時 `appearance_spec_pass_flag = 1 - appearance_ng_flag`。若不一致且無處置紀錄，輸出 `APPEARANCE_FLAG_CONFLICT`，外觀標籤不可用；不得以 spec pass 覆寫 NG 真值。

### 2.5 canonical 欄位

| 欄位 | 型別／單位 | 定義 |
|---|---|---|
| `timestamp` | datetime | 時區明確的最終區段完成時間 |
| `root_roll_id`／`product_batch` | string | 卷及批次識別；只供追溯與分割，不直接作特徵 |
| `material_md_start_m`／`material_md_end_m` | float／m | canonical 材料 MD 半開區間 |
| `ambient_temp_c` | float／°C | 環境溫度 |
| `ambient_rh_pct` | float／%RH | 環境相對濕度，0–100 |
| `line_speed_m_min` | float／m/min | 線速，必須 > 0 |
| `coating_temp_c` | float／°C | 塗佈段設定溫度 |
| `coating_gap_um` | float／μm | 塗佈間隙設定 |
| `coating_viscosity_mpa_s` | float／mPa·s | 塗液黏度 |
| `curing_temp_c` | float／°C | 熟化段設定溫度 |
| `curing_time_min` | float／min | 熟化時間設定 |
| `lamination_temp_c` | float／°C | 壓合溫度設定 |
| `lamination_pressure_mpa` | float／MPa | 壓合壓力設定 |
| `lamination_time_s` | float／s | 壓合保持時間設定 |
| `peel_strength_n_mm` | float／N/mm | 目標：抗剝離度 |
| `dimensional_stability_md_pct` | float／% | 目標：MD 尺寸變化，保留正負號 |
| `dimensional_stability_td_pct` | float／% | 目標：TD 尺寸變化，保留正負號 |
| `heat_resistance_c` | float／°C | 目標：固定測試條件下的模擬最高通過溫度 |
| `appearance_ng` | int／0,1 | 目標：0=OK、1=NG |

## 3. 模擬資料生成 v2

- 預設 seed 42、200 個獨立卷、每卷約 100 個 canonical 區段，共約 20,000 區段；依完整卷與時間分成 train／validation／test 120／40／40 卷。
- `overall_pass_flag` 是最終區段在剝離、MD、TD、耐熱及外觀五項的聯合結果；全資料目標良率 78%–82%。這是合成區段良率，不是整卷放行良率或真實產線承諾。
- 個別失敗率的生成起始目標：剝離、MD、TD、耐熱各 4%–7%，外觀 NG 5%–8%；失敗機制須有合理共因與相關性，不以互相獨立硬配比例。
- 穩定期聯合良率約 93%–97%，輕度漂移約 75%–90%，強度漂移約 45%–70%；整體仍須落在 78%–82%。Phase I 穩定資料至少提供 25 個有效子組，且與漂移資料分離。
- 以合理非線性、交互作用、卷效應、時間自相關與製程事件生成品質；需覆蓋規格中心、接近上下限、超規，以及穩定／漸變／突發漂移。
- 禁止以隨機翻標籤、逐筆修改規格、複製 NG、將大量值裁到完全相同規格界限，或把隱藏漂移標籤加入特徵來達成目標良率。
- 完整真值與模擬抽檢分離：`quality_timeseries.csv` 保存 `synthetic_ground_truth`，`quality_inspection.csv` 依線上、實驗室及整卷資格檢驗頻率產生可缺測的 `simulated_inspection`。
- metadata 記錄 schema／生成器版本、seed、固定起始時間、時區、參數與規格版本、生成係數、漂移、分割、列數、良率、失敗率及七份 CSV 的 SHA-256。相同設定重跑應得到相同 CSV hash。

## 4. 特徵工程與模型治理

- 特徵採明確 allowlist；排除所有目標、規格判定、品質檢驗後資訊、產品／卷／批號識別及漂移真值。原始 timestamp 預設只供排序及分割。
- 特徵缺值只可由 train 擬合的中位數等策略處理；目標值永不插補。全空必要特徵、型別、物理範圍與單位錯誤不得靜默轉成缺值。
- rolling／lag 必須先按卷與時間排序再 shift，只用預測當下已取得資料；若要預測未來，先定義 horizon、製程延遲、標籤時間及隔離間隔。
- 按完整卷的時間先後切分 train／validation／test，約 60／20／20；所有前處理只在 train 擬合，validation 用於調參與門檻，test 只作最終評估。所有候選模型使用相同資料快照、切分、特徵版本與指標。
- 每個連續目標先建立平均值／線性基準，每個分類目標建立常數或簡單機率基準。Random Forest 是初版 Champion；HistGradientBoosting 是必要 Challenger。
- XGBoost、LightGBM 透過共同 adapter 作可插拔 Challenger；初期若只導入一個，優先 XGBoost。外部套件未安裝不得使核心流程失敗，也不得同時導入兩者只為增加模型名稱。
- LSTM／GRU 僅在明確預測 horizon、具足夠獨立序列與長度，且樹模型加 lag／rolling 在相同測試上仍不足時才可成為 Challenger；未滿足不得列為必要實作。
- SPC 是可解釋監控基線；PCA／Isolation Forest 是無監督異常基線；Autoencoder 僅為資料量與驗證策略足夠時的 Challenger。anomaly score 不得解讀為 NG 機率或直接取代品質規格。
- 連續目標報告 MAE、RMSE、R²與基準改善；外觀分類報告 PR-AUC、precision、recall、F1、confusion matrix、類別比例及適用時的校準。另分開報告穩定／漂移及各 split 表現，不預先承諾分數。
- Challenger 只有在預先定義的重要指標、穩定性、延遲與可維護性條件均通過時才可升為 Champion；升版保留舊版、比較證據、回退方式與 manifest。
- bundle 包含前處理、模型與輸出映射；manifest 至少包含模型／schema／特徵／標籤／規格版本、來源、availability、切分、seed、套件、訓練範圍、指標、門檻、SPC 基準及 hash。

## 5. Heatmap 與 SHAP

- Heatmap 顯示數值製程參數與五個目標的關係，保留 MD／TD 分欄，標示資料範圍、單位及方法；相關不解讀為因果。
- 樹模型使用合適的 SHAP explainer；背景樣本取自 train，解釋樣本取自隔離資料並固定抽樣量與 seed。
- 每個迴歸目標可選 Summary／Dependence；分類明確選取標籤 1 輸出，說明 SHAP 尺度，不假設它必為機率或固定陣列位置。
- 解釋輸入必須與實際前處理一致；繪圖函式回傳可嵌入圖形，不呼叫阻塞式 show。

## 6. SPC 與警報

- 四個連續品質目標各提供 X-bar 圖；外觀 NG 使用 p／np 類比例圖或明確的預測風險視圖，不將二元資料套 X-bar。
- 預設每組 n=5，按時間建立不跨卷、不跨產品／配方的合理子組；不足 n 的尾組不納入判定。Phase I 使用已確認穩定的至少 25 組基準。
- X-bar 基準：CL=基準組平均的平均，UCL/LCL=CL ± A2(n) × R-bar；n=5 時 A2=0.577。基準固定後才套 Phase II，不隨監控資料自動重算。
- 初版規則：一點超過管制界限、連續 6 點嚴格上升／下降、連續 9 點在中心線同側；相等值、缺組及換卷中斷相應序列。
- 畫面分開標示實測管制界限、產品規格與模型預測；參數滑桿不得重寫實測 SPC 歷史。資料不足、R-bar=0 或基準不穩時停止正式判定並顯示原因。
- Alarm 顯示觸發規則、目標、時間／卷及數值。連續預測超規或外觀 NG 機率達版本化門檻才觸發品質警報；缺規格不得宣稱合格。

## 7. 動態調參與 UI

- 側邊欄提供 CSV 上傳、模擬模式、產品規格、環境值及模型版本；清楚標示目前卷／區段。線速預設可調，熟化與壓合參數由按鈕解鎖。
- 以目前區段為基準，固定環境與不可控特徵，只搜尋已開放參數的允許範圍；依關聯規則重算衍生特徵並批次推論。
- 建議先降低預測超規風險，再偏好較小調整；五項品質都要檢查，避免改善一項卻使另一項超規。
- 顯示目前／候選參數、單位、參數差值、四個連續品質預測、外觀 NG 機率、各項規格狀態、適用範圍與限制。依使用者決定，不新增「當下預測良率」欄位。
- 無改善候選、模型不可用、超出訓練支援範圍或缺規格時明示限制，不編造改善幅度；SHAP 與 What-if 不視為因果或設備效果保證。
- 模型以 `st.cache_resource` 快取，資料與圖表依內容、版本與參數快取；滑桿變動不得觸發重訓。

## 8. 內部 API 與串接

初版以 Python 函式串接，不另建 HTTP 服務：

| 函式 | 輸入 | 輸出 |
|---|---|---|
| `generate_mock_data(config)` | 版本化生成設定 | 七表、metadata |
| `validate_source_tables(tables, metadata)` | 七表與版本 | 驗證後來源、結構化問題 |
| `build_model_dataset(tables, target, config)` | 來源表、目標、整合規則 | canonical 資料、lineage、排除原因 |
| `train_models(df, config)` | 逐目標訓練資料 | registry、bundle、manifest、metrics |
| `predict_quality(df, bundle)` | 具名特徵 | 五個預測、NG 機率與適用範圍警示 |
| `compute_spc(df, baseline, config)` | 已完成實測、固定基準 | 子組統計、界限、警報 |
| `recommend_adjustments(row, bundle, config)` | 現況、可調參數與範圍 | 候選設定、預測比較、限制與原因 |
| `plot_heatmap／plot_shap_*` | 資料、模型及目標 | 可嵌入圖形 |

- 預測欄位採 `pred_<target>`，另提供 `appearance_ng_probability`；輸入索引不可丟失。不可用結果以 null 加結構化原因表示，不偽造 0。
- 問題格式包含 `code`、`field`、`row`、`message`；區分 schema、對齊、標籤、規格、模型不相容、資料不足及超出支援範圍。
- 未來 HTTP／MES／PLC 串接另立 Change，定義認證、schema、單位、時區、逾時、重試、冪等與稽核；初版不得直接寫入機台。

## 9. 驗證重點

- 七表 schema、唯一鍵、外鍵、MD 半開區間、站別覆蓋率、spec pivot、重測選取、旗標一致性與逐目標 availability。
- 相同 seed 的七份 CSV hash 一致；卷數、區段數、120／40／40 分割、聯合良率 78%–82%、個別失敗率、NG 卷涵蓋、穩定／漂移分布及 Phase I 子組量符合 metadata。
- 完整卷與時間隔離、無目標／規格／漂移洩漏、序列化前後預測一致、Champion／Challenger 同切分比較、SHAP 目標正確。
- CSV 錯誤提示、SPC 界限與規則、滑桿只改情境預測、解鎖限制、建議不越界、模型缺類別或缺標籤時的降級行為。

## 10. 改善循環

- 每次改善建立不可變 `improvement_cycle_id`、資料快照與基準期；先比較良率、各失敗模式、SPC 穩定性及製程分布，再決定是否納入下一輪訓練。
- 新資料經 schema、標籤、規格、資料漂移與品質審核後，才在離線流程重新訓練 Challenger；不得在線自動學習或直接改動設備。
- 新模型需以相同時間／卷隔離測試與既有 Champion 比較，通過升版門檻才部署；保留舊版本、回退方式及決策紀錄。
- 合成資料只驗證流程與方法，不能證明實際產線改善；真實因果效果需受控試驗或製程負責人核准的驗證設計。
