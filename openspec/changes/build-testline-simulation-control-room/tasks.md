# Tasks

## 0. Gate 0 — 可操作 Streamlit 靜態 UI 原型

- [x] 0.1 建立獨立的測試線控制台原型入口與原型 banner，固定 fixture 不載入正式模型或模擬器；以啟動命令及 smoke test 驗證頁面可開啟且所有 fixture 明示「靜態原型」。
- [x] 0.2 建立四頁固定導航「生產控制台／SPC 詳細監控／What-if／Heatmap／Run 紀錄」，以 UI 測試驗證頁面順序、標題、返回狀態及一般導覽不顯示 A／B／C 選擇或 SHAP。
- [x] 0.3 建立模擬產線與機台位置示意、單一產品／配方卡片，展示乾膠厚度等產品規格與七項機台標準；以快照或瀏覽器測試驗證資訊可讀、單位完整且 fixture 來源清楚。
- [x] 0.4 建立七項主要數字輸入、三項進階輸入、候選／確認互動及 setpoint／actual 區分；以 UI 測試驗證不使用滑桿作唯一輸入、未確認不改變 fixture live 值、無效值有逐欄訊息。
- [x] 0.5 建立首頁最多三張最近 60 點圖、四項品質預測、分級 Alarm 摘要及展開明細 fixture；以瀏覽器測試驗證大量事件不產生逐點紅卡淹沒且技術 ID 預設收合。
- [x] 0.6 建立詳細 SPC、What-if／Heatmap 與 Run 紀錄的可操作 fixture 狀態；以 UI 測試驗證 Heatmap 來源／樣本不足、What-if 帶回表單、completed／interrupted Run 呈現及非因果限制。
- [x] 0.7 依桌面常用解析度調整字級、間距、欄寬與資訊密度，執行 Streamlit smoke、UI 與瀏覽器回歸並保存驗收截圖／命令結果；確認未改寫 v2 資料、模型或既有正式入口。
- [x] 0.8 更新本 Change 的 tasks 與開發日誌，提交 Gate 0 成品供使用者人工驗收；未取得明確驗收前 MUST 停止，不得開始 Gate 1。

## 1. Gate 1 — 契約、設定與安全邊界

- [ ] 1.1 依已批准 specs 更新 AGENTS.md、SKILL.md、資料字典及單一 Mode B／四目標／Run／製程 SPC 責任邊界；以文件交叉檢查驗證 OpenSpec 與技術契約無衝突。
- [ ] 1.2 建立 `FCCL-DEMO-001`、`SIM-RECIPE-3.0` 的版本化產品規格、配方標準、UI 範圍與單位設定；以 schema 測試驗證四種範圍不可互換且預設數值符合 design。
- [ ] 1.3 定義 process signal、五點厚度子組、material segment、parameter event、SPC event、quality prediction 與 manifest schema；以有效／缺欄／錯單位／版本不相容 fixture 驗證拒絕原因。
- [ ] 1.4 建立 Run 目錄與五 CSV／manifest 介面、生命週期及 hash 契約，並將 `runtime_data/` 納入 Git 排除；以檔案契約測試驗證不寫入 raw data、generated_data 或 artifacts。
- [ ] 1.5 建立 setpoint／actual、站別適用邊界、品質延遲及模型支援範圍的共享型別與驗證器；以邊界測試驗證未來特徵、部分事件及 UI 範圍冒充模型範圍會被拒絕。
- [ ] 1.6 執行 Gate 1 schema、文件與既有回歸測試，記錄相容／刻意 breaking 的結果並更新 tasks／日誌；所有必要契約測試通過後才進 Gate 2。

## 2. Gate 2 — Synthetic v3 與四目標模型

- [ ] 2.1 擴充合成生成設定與生成器，輸出三站 setpoint／actual、五點乾膠厚度、排風量、材料時間及四目標可得性；以相同 seed 重跑 hash 與欄位／單位驗證測試確認可重現。
- [ ] 2.2 生成隔離的 Synthetic v3：200 卷、約 20,000 完成區段及 120／40／40 完整卷切分；以 manifest 檢查驗證卷、時間、demo seed、v2、runtime Run 與 reference 無交叉污染。
- [ ] 2.3 建立穩定 reference 與六種漂移驗證資料，保留 drift truth 但從模型／線上 SPC 輸入排除；以穩定基準足量及固定情境差異測試驗證。
- [ ] 2.4 建立四目標 canonical v3 dataset 與 feature allowlist，納入乾膠厚度／排風量並排除目標、識別、規格旗標、未來與漂移真值；以洩漏測試及逐目標列數報告驗證。
- [ ] 2.5 對四目標訓練 baseline、Random Forest 與 HistGradientBoosting，依相同 split 報告 MAE／RMSE／R²、基準改善及穩定／漂移表現；以訓練命令與 metrics 驗證，外觀模型不在 v3 bundle。
- [ ] 2.6 產出可信四模型 bundle、registry、manifest、feature 支援範圍與 hash；以載入／推論／不相容／超範圍測試驗證，且 v2 外觀 artifact 保持未改寫。
- [ ] 2.7 執行 v3 生成、資料、訓練與既有 ML 回歸套件，記錄效能、限制及 Gate 2 證據並更新 tasks／日誌；所有必要測試通過後才進 Gate 3。

## 3. Gate 3 — 連續模擬器、Run Store 與製程 SPC

- [ ] 3.1 實作單一 in-flight 的 5 模擬秒時鐘、穩態預載、倍率與降速／自動暫停；以虛擬時鐘測試驗證無重疊、跳點、重複序號或 backlog。
- [ ] 3.2 實作塗佈／熟化／壓合材料區段流與站別延遲；以參數事件前後的材料邊界測試驗證過去材料不被改寫且未完成材料不產生品質。
- [ ] 3.3 實作整組參數驗證、不可變 ParameterEvent 與 setpoint 到 actual 的模擬響應；以合法／部分無效／超範圍／多次調整測試驗證原子性及追溯。
- [ ] 3.4 實作穩定、厚度增／減、溫度下降、風量衰減、壓力漂移及複合漂移固定情境；以相同 seed hash 與不同情境統計測試驗證可重現且 drift truth 隔離。
- [ ] 3.5 實作記憶體 Run 狀態、每 60 模擬秒一致 checkpoint、finalize／hash 與 interrupted 唯讀檢視；以故障注入測試驗證部分寫入不標完成、重寫不重複列且初版不能續跑。
- [ ] 3.6 實作乾膠厚度五點 X-bar／R 及溫度／風量／線速／壓力 I-MR／EWMA 的增量計算；以已知序列測試驗證圖型、中心線、界限、缺組及固定 reference。
- [ ] 3.7 實作正常／警告／嚴重／證據不足、製程失控／產品超規分離、事件群與後續證據復歸；以長漂移測試驗證調參不會立即清警報且首頁摘要有界。
- [ ] 3.8 接入四模型的完成材料推論，每 30 模擬秒或新適用材料更新；以時間可得性及 manifest 測試驗證不使用未來特徵、不複製舊區段、不輸出外觀或預測良率。
- [ ] 3.9 執行 Gate 3 模擬器、Run、SPC、Alarm、模型整合與長時間效能測試，更新 tasks／日誌及限制；所有必要測試通過後才進 Gate 4。

## 4. Gate 4 — 正式控制台整合與驗收

- [ ] 4.1 將一般 Streamlit 入口切至單一測試線控制台並以正式服務取代 Gate 0 fixture；以導航及來源測試驗證不顯示 A／C／SHAP，且舊 v2／Mock 不會靜默補值。
- [ ] 4.2 串接首頁產線位置、規格／配方、參數表單、三張關鍵圖、四目標預測與 Alarm 摘要；以穩定及各漂移瀏覽器情境驗證資料更新、字級、密度與錯誤狀態。
- [ ] 4.3 串接 SPC 詳細頁的全部適用圖、事件篩選、事件群與技術明細；以大量長漂移測試驗證首頁不被紅字淹沒、原始事件可稽核且無重複事件身分。
- [ ] 4.4 串接材料區段 Heatmap，支援 v3 reference／目前 Run、30 區段門檻、聚合 metadata 與按需快取；以重複品質防護、來源切換及過期結果測試驗證。
- [ ] 4.5 串接隔離 What-if、四目標比較及「帶回控制台再確認」流程；以 live Run 同步推進測試驗證候選不污染實際資料、SPC、Alarm 或參數事件。
- [ ] 4.6 串接 Run 紀錄、completed／interrupted 唯讀檢視與必要匯出；以重啟應用測試驗證 manifest／hash／來源限制可查且不觸發訓練。
- [ ] 4.7 完成快取、最近 60 點、增量 SPC、按需分析與單一 tick 的效能整合；以目標硬體長時間測試驗證無排程堆積，過慢時降速／暫停而不跳資料。
- [ ] 4.8 執行 Streamlit smoke、四模型、SPC、Alarm、What-if、Heatmap、Run、瀏覽器及全部既有回歸測試，記錄通過／失敗／未執行與修復重測，更新 tasks、DEVELOPMENT_LOG、DECISION_LOG 及必要 TEAM_CHANGE_PROPOSALS。
- [ ] 4.9 依規格逐項人工驗收單一產品的穩定與六種漂移情境，確認無真實設備／因果／良率／外觀／SHAP 誤導文字；取得使用者最終確認後才視為 Apply 完成。

## Workflow follow-up

- Gate 0 Apply 完成後停止並讓使用者先驗收面板；未確認不得自動繼續 Gate 1。
- Gate 4 完成且驗證證據齊全後，再依使用者指示 Sync／Archive 本 Change。
- 本 Change 不授權自動 Commit 或 Push；Git 操作需另行明確指示。
