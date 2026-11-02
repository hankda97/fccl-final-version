# Spec Delta

## MODIFIED Requirements

### Requirement: WS-01 單一主畫面與原定功能配置

系統 SHALL 提供側欄 CSV／Mock 載入、產品與環境資訊，以及上方監控摘要、Alarm 區與 SPC、What-if、AI 圖表、資料檢查四個 Tabs。SPC 與實測 Alarm、固定區段 What-if／Mock 比較及預測風險 MUST 保留。AI 圖表 SHALL 提供實測 Heatmap 與 SHAP Summary／Dependence 的選擇及能力提示；SHAP 測試呈現、正式模型解釋與歷史回放須清楚區分，不顯示偽造結果。

AI 圖表 SHALL 依版本化來源 profile 區分 C Mock、區段抽檢與獨立合成真值分析，顯示卷／材料 MD、來源與逐目標狀態；不得把卷檢驗複製為區段結果，不增加「當下預測良率」。此要求是 C6 來源接點／測試顯示；A／B 七表整合、正式 manifest 及 C1～C5 的正式契約轉接留 C9，不回退既有 Mock 功能。

#### Scenario: 初次開啟與無資料畫面
- **WHEN** 首次開啟且沒有資料
- **THEN** 標題、側欄、上方監控及四個 Tabs 可辨識，品質值顯示「—」，SPC／Alarm 顯示尚無可判定資料，回放與解鎖停用

#### Scenario: 載入後功能可尋得
- **WHEN** 載入有效 C Mock
- **THEN** 資料檢查可用，SPC 依有效目標／基準顯示 X-bar 或限制；What-if 顯示固定區段、Mock 前後比較及來源標示；Heatmap 依有效實測配對呈現；兩種 SHAP 依解釋能力顯示匹配結果或限制，公式 Mock 模式明示待 B／C9 整合；可信時間投影可用時可操作歷史回放，否則明示限制

#### Scenario: 原定 AI 圖表入口
- **WHEN** 使用者開啟 AI 圖表 Tab 並切換圖表種類
- **THEN** Heatmap、SHAP Summary Plot、SHAP Dependence Plot 的名稱與入口均可辨識，五項品質目標及所需特徵選擇可尋得，其他三個 Tabs 及主畫面監控／Alarm 配置不變

#### Scenario: 回放控制及時間來源可辨識
- **GIVEN** 有可信時間投影的來源已載入
- **WHEN** 選擇回放模式
- **THEN** 顯示播放／暫停、單步、重啟、倍率、模擬時間、已播放筆數及進度；維持四 Tabs，無資料或無可信事件時停用相依控制，倍率不作製程線速

### Requirement: WS-02 分頁切換保留工作狀態

系統 MUST 在同一工作階段的重跑或 Tab 切換保留已載入資料、批號與時間篩選、固定 What-if 區段及候選參數，不重新初始化業務狀態。成功載入不同資料／映射／時間 profile 或實際改變篩選時 SHALL 清除舊資料相依的游標／情境；模式切換及重啟依回放生命週期使不可見情境失效；SPC 基準 SHALL 以歷史與設定版本固定，切 Tab 不追加事件；情境重算只使用其固定輸入及候選值，不修改實測或 SPC 結果。圖表選項及匹配結果 SHALL 獨立保留，圖表切換與失敗不重設既有業務狀態。

#### Scenario: 分頁切換與同源重載
- **WHEN** 已載入並篩選 CSV，切換 Tabs、重跑或載入相同來源／內容／映射
- **THEN** 資料、篩選與既有業務狀態保留；成功載入不同資料時才清除相依情境／游標，失敗嘗試不替換有效資料

#### Scenario: What-if 變更不污染監控
- **WHEN** 使用者調整固定區段的 What-if 參數並切換 Tabs
- **THEN** 固定識別、候選參數及預測結果保留，原始資料、SPC 界限／事件及目前監控預測狀態不變

#### Scenario: 圖表選項與相依結果的狀態界線
- **WHEN** 選定 Heatmap 欄位或 SHAP 圖型／目標／特徵後往返 Tabs，或成功切換不同來源／篩選
- **THEN** 一般重跑保留有效選項與匹配結果；新來源只保留仍有效的欄位選擇、清除相依圖表結果，僅 availability／來源／規格／manifest metadata 改變亦使相依結果失效，無效選項明確重設或提示，What-if／SPC 仍遵守各自既有重設及固定規則

#### Scenario: 回放重跑與失效生命週期
- **GIVEN** 回放已推進並固定 What-if
- **WHEN** 切換 Tabs、推進或重新開始
- **THEN** 一般重跑保留進度且不重複推進；推進不改寫固定情境；重啟則暫停歸零、失效情境不自動復活，舊計時及結果不能回寫
