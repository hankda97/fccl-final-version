---
name: fccl-quality-spc
description: 建置本專案的 FCCL 模擬資料、Random Forest 與 SHAP 品質預測及 Streamlit SPC 儀表板；適用於此專案的開發與驗證。
---

# FCCL 技術實作規範

狀態：待確認的 v0.1 草案。先閱讀 AGENTS.md；本次僅編寫規範，Python 程式於使用者確認後實作。

## 1. 工具鏈與檔案

- 採 Python 3.11 與 venv；資料處理用 numpy、pandas，模型用 scikit-learn、joblib，解釋用 shap，圖表用 matplotlib、seaborn、plotly，介面用 streamlit，驗證用 pytest。
- 實作時確認相容版本並鎖定依賴；模型 manifest 記錄 Python 及套件版本，不依賴浮動 latest。
- 保留三個入口：mock_data_generator.py、model_training.py、app.py；必要時抽出共用的特徵、SPC 與驗證模組。
- 預定輸出：data/mock_fccl.csv、data/mock_fccl.metadata.json、artifacts/model_bundle.joblib、artifacts/manifest.json、artifacts/metrics.json、artifacts/plots/。
- 隨機生成、抽樣及 Random Forest 均使用可設定 seed；預設 42。時間含時區、CSV 使用 UTF-8，檔案路徑可設定。

## 2. 資料契約 v1

一列代表同一產品批次、同一材料區段，經三製程完成後對齊的取樣紀錄。timestamp 為取樣完成時間，採含 Asia/Taipei 偏移的 ISO 8601。各段特徵必須能對應同一區段，且在品質預測時已取得。

| 欄位 | 型別／單位 | 定義 |
|---|---|---|
| timestamp | datetime | 時區明確的取樣時間 |
| product_batch | string | 批次識別；單一產品／配方為初版範圍 |
| length_m | float／m | 本次取樣代表的材料長度，必須 > 0 |
| ambient_temp_c | float／°C | 環境溫度 |
| ambient_rh_pct | float／%RH | 環境相對濕度，0–100 |
| line_speed_m_min | float／m/min | 線速，必須 > 0；生成與 UI 皆可設定 |
| coating_temp_c | float／°C | 塗佈段設定溫度 |
| coating_gap_um | float／μm | 塗佈間隙設定 |
| coating_viscosity_mpa_s | float／mPa·s | 塗液黏度 |
| curing_temp_c | float／°C | 熟化段設定溫度 |
| curing_time_min | float／min | 熟化時間設定 |
| lamination_temp_c | float／°C | 壓合溫度設定 |
| lamination_pressure_mpa | float／MPa | 壓合壓力設定 |
| lamination_time_s | float／s | 壓合保持時間設定 |
| peel_strength_n_mm | float／N/mm | 目標：抗剝離度 |
| dimensional_stability_md_pct | float／% | 目標：MD 尺寸變化，保留正負號 |
| dimensional_stability_td_pct | float／% | 目標：TD 尺寸變化，保留正負號 |
| heat_resistance_c | float／°C | 目標：固定測試條件下的模擬最高通過溫度 |
| appearance_ng | int／0,1 | 目標：0=OK、1=NG |

- metadata 記錄 schema_version、seed、起始時間、取樣間隔、批次長度、參數範圍、生成係數、漂移起訖與時區。
- 產品規格及測試條件保存在版本化設定與 manifest，不以未說明的常數散落程式；實測資料需另確認測試方法。
- 四大品質類別共五個目標欄位：抗剝離、尺寸 MD/TD、耐熱、外觀。品質規格與 SPC 管制界限分開管理。
- 提供明確標示的「模擬示範」規格設定；實際允收值與設備範圍尚待製程負責人提供，不宣稱符合通用 FCCL 規範。
- 訓練 CSV 需要所有特徵與目標；推論可缺目標，但必須保留識別欄與必要特徵。缺少實測品質時，SPC 顯示無實測資料。

## 3. 模擬資料生成

- 支援 seed、筆數、取樣間隔、批次大小、線速與漂移強度設定；預設建立多批次的穩定期及後續漂移期。
- 以製程合理的非線性、交互作用及隨機噪音生成品質；例如濕度與熟化條件交互影響抗剝離，壓合條件影響尺寸及外觀機率。
- 使用環境濕度漸變與設備偏移事件，模擬連續劣化及突發異常；分別記錄觀測特徵漂移與設備狀態導致的品質關係變化。
- 連續製程的滯留時間若由爐長／線速推導，必須宣告該依賴，調參時同步重算；獨立批次熟化時間不得誤當線速的函數。
- 保留批次效應與時間自相關；不得將批號、時間索引或隱藏漂移標籤用成品質捷徑。漂移真值只存 metadata／驗證資料。
- 驗證相同設定可重現、時間有序、欄位範圍合理、批次足夠，並量化漂移前後均值及 NG 率；不要把噪音全部裁成邊界值。

## 4. 特徵工程與 Random Forest

- 特徵採明確 allowlist；排除所有目標、產品批號及漂移真值。原始 timestamp 預設只供排序及分割使用。
- 數值缺值以訓練資料擬合的中位數填補；全空必要特徵拒絕訓練。型別、物理範圍與單位錯誤不得靜默轉成缺值。
- 初版使用當下可取得的製程特徵及已定義衍生特徵；若增加 rolling／lag，先按批次排序並 shift，禁止使用未來資料。
- 按完整批次的時間先後切分 train／validation／test，比例約 60／20／20，以批次邊界為準；樣本不足時明確回報，不退回隨機切分。
- 所有前處理僅在 train 擬合；validation 用於調參、分類門檻及警報門檻選擇；test 留到最終評估。時間重疊／滯後特徵需要額外隔離間隔。
- 為四個連續目標建立 RandomForestRegressor，為 appearance_ng 建立 RandomForestClassifier；同一特徵轉換與欄位順序供訓練及推論共用。
- 迴歸逐目標報告 MAE、RMSE、R²及常數基準；分類報告 PR-AUC、precision、recall、F1、confusion matrix 與類別比例。單一類別時將不適用指標標為 N/A，不製造虛假分數。
- 分開報告穩定／漂移區間表現；不預先承諾準確率。單一類別訓練需顯示限制，不能提供有意義的 NG 風險排序。
- joblib bundle 包含前處理、模型與輸出映射；manifest 包含 schema／模型版本、特徵單位與順序、時間切分、seed、套件版本、訓練範圍、品質規格、警報門檻及 SPC 基準來源。
- 僅載入本專案可信路徑下的 joblib；CSV 上傳不提供模型反序列化入口。

## 5. Heatmap 與 SHAP

- Heatmap 顯示數值製程參數與五個目標的關係，保留 MD／TD 分欄，標示資料範圍、單位及相關係數方法；相關不解讀為因果。
- SHAP 使用 TreeExplainer，背景樣本取自 train，解釋樣本取自隔離資料並限制抽樣量與 seed。
- 每個迴歸目標可選 Summary／Dependence；分類明確選取 classes_ 中標籤 1 的輸出，說明 SHAP 尺度，不能假設它必為機率或固定陣列位置。
- 解釋輸入必須與模型實際前處理一致；繪圖函式回傳 Figure／Plotly Figure，不呼叫阻塞式 show，Streamlit 顯示後釋放不用的圖形。

## 6. SPC 與警報

- 四個連續品質目標各提供 X-bar 圖；外觀 NG 顯示比例／預測風險，不將二元資料直接套用 X-bar。
- 預設每組 n=5，按時間建立不跨批次、同產品／配方的合理子組；不足 n 的尾組不納入判定。子組代表相近製程條件，不可只為湊數跨越配方或停機。
- Phase I 使用獨立、已確認穩定的至少 25 組基準；模擬可使用事件前穩定期。CL=基準組平均的平均，UCL/LCL=CL ± A2(n) × R-bar；n=5 時 A2=0.577。
- 基準固定後套用於 Phase II；不得隨監控資料自動重算而掩蓋漂移。資料不足、R-bar=0 或基準不穩定時顯示限制，停止正式 SPC 判定。
- 初版規則：一點超過管制界限、連續 6 點嚴格上升／下降、連續 9 點在中心線同側；相等值中斷嚴格趨勢，缺組／換批中斷連續序列。
- 畫面分開標示實測管制界限、產品規格及模型預測；參數滑桿不得重寫實測 SPC 歷史。只使用已完成實測子組判定 SPC。
- 紅字 Alarm 顯示觸發規則、目標、時間／批次與數值。品質警報在預測連續值超規，或 NG 機率達可設定門檻時觸發；缺規格的目標不得宣稱合格。
- 初版預測為當前材料區段的品質風險估計；若要宣稱預測未來幾分鐘，需另定 horizon、製程延遲及時間對齊標籤。

## 7. 動態調參與 UI

- 側邊欄提供 CSV 上傳、模擬模式標示、產品規格、環境值及模型版本；清楚標示目前選取批次／區段。
- 線速滑桿預設可用；熟化與壓合參數由按鈕解鎖。解鎖狀態使用 session_state，切換資料或模型時重設。
- 以目前區段為基準，固定環境與不可控特徵，只搜尋已開放參數的允許範圍；依關聯規則重算衍生特徵並批次推論。
- 建議採候選情境比較：先降低預測超規風險，再偏好較小調整；每項品質均需檢查，避免改善一項卻讓另一項超規。
- 顯示目前／候選設定、單位、五個目標的預測變化及範圍限制；僅在模型有改善證據時顯示「建議線速調慢 0.2 m/min」等實際差值。
- 無改善候選、分類模型不可用、超出訓練支援範圍或缺少規格時，明確顯示限制，不編造改善幅度。SHAP 用於解釋，建議不視為因果或設備效果保證。
- 模型以 st.cache_resource 快取，資料與圖表依資料內容、模型版本及參數快取；避免滑桿變動觸發重訓。

## 8. 內部 API 與未來串接

初版以 Python 函式串接，無須額外建置 HTTP 服務。以下是待實作契約：

| 函式 | 輸入 | 輸出 |
|---|---|---|
| generate_mock_data(config) | 版本化生成設定 | DataFrame、metadata |
| validate_data(df, mode) | train／inference／spc 模式 | 驗證後資料、結構化問題清單 |
| train_models(df, config) | 通過驗證的訓練資料 | bundle、manifest、metrics |
| predict_quality(df, bundle) | 具欄位名的特徵資料 | 與輸入索引對齊的五個預測、NG 機率及適用範圍警示 |
| compute_spc(df, baseline, config) | 已完成實測資料、固定基準 | 子組統計、界限、警報事件 |
| recommend_adjustments(row, bundle, config) | 現況、已開放參數與範圍 | 候選設定、預測比較、限制與原因 |
| plot_heatmap／plot_shap_summary／plot_shap_dependence | 資料、模型及目標等具名參數 | 可嵌入的圖形物件 |

- 預測欄位採 pred_<目標欄位>，另提供 appearance_ng_probability；樣本順序與索引不可丟失。不可用機率以 null／缺值加原因表示，不偽造 0。
- 問題格式包含 code、field、row、message；區分 schema 錯誤、模型不相容、資料不足及超出支援範圍。
- 未來 HTTP／MES 串接另立 OpenSpec change：定義認證、版本化 schema、單位、時區、逾時、重試、冪等與稽核；不在 UI 隱含新增外部服務。

## 9. 驗證重點

驗證可重現資料及漂移、時間與批次隔離、序列化前後預測一致、SHAP 輸出目標正確、CSV 錯誤提示，以及以已知序列檢查 SPC 界限與三項規則。另確認滑桿只改情境預測、解鎖限制有效、建議不越界及模型缺類別時的降級行為。
