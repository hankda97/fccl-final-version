# Spec Delta

## ADDED Requirements

### Requirement: WS-08 Gate 0 可操作靜態原型

Gate 0 MUST 提供可啟動的 Streamlit 靜態 UI 原型，使用固定 fixture 展示完整資訊架構與互動；頁面 SHALL 持續標示「靜態原型／非執行中模擬」，不得將 fixture 宣稱為模型、SPC 或即時模擬結果。

#### Scenario: 原型驗收
- **WHEN** 使用者啟動 Gate 0 原型
- **THEN** 可操作頁面導航、數字欄位、提交按鈕、圖表／Alarm 展開、What-if／Heatmap 控制與 Run 紀錄 fixture，且不需 Synthetic v3 或模型 artifact

#### Scenario: 原型數值互動
- **WHEN** 使用者修改欄位或切換 fixture 情境
- **THEN** 畫面可展示預定狀態與版面，但以明確標籤說明不會執行真實模擬、正式模型或設備控制

### Requirement: WS-09 控制台資訊架構

正式控制台 MUST 提供「生產控制台」「SPC 詳細監控」「What-if／Heatmap」「Run 紀錄」四個固定頁面；首頁 SHALL 顯示模擬產線位置、產品規格／配方標準、七項主要數字調參、最多三張關鍵 SPC 圖、四項品質預測與有界 Alarm 摘要。

#### Scenario: 首頁正常運轉
- **WHEN** Run 已啟動且已有適用資料
- **THEN** 使用者不離開首頁即可看到材料所在站別、setpoint／actual、規格與標準來源、最新 60 點、四目標可得性及目前開啟警報

#### Scenario: 查看完整資訊
- **WHEN** 使用者需要其他訊號、完整事件、分析或歷史 Run
- **THEN** 可從固定頁面進入相應詳細內容，首頁不堆疊全部技術欄位或歷史紅色事件

### Requirement: WS-10 主要與進階參數表單

首頁 MUST 以可精確輸入的數字欄位提供線速、塗佈間隙、熟化溫度、排風量、熟化時間、壓合溫度及壓合壓力；塗佈溫度、黏度與壓合時間 SHALL 置於進階區。所有變更須整組確認，不以滑桿作唯一輸入。

#### Scenario: 檢視標準與限制
- **WHEN** 使用者編輯任一參數
- **THEN** 同區顯示單位、目前 setpoint、actual、配方標準、UI 操作範圍及模型支援提示

#### Scenario: 尚未確認候選值
- **WHEN** 使用者修改欄位但未按下確認套用
- **THEN** live Run、actual、SPC 與品質預測不改變，畫面明示候選尚未生效

### Requirement: WS-11 四項品質預測與來源

控制台 SHALL 顯示抗剝離、尺寸安定性 MD／TD 與耐熱度四項預測、單位、模型版本及材料區段；外觀與預測良率不得出現在初版品質摘要。未完成三站或輸入超出支援時 MUST 顯示不可得原因。

#### Scenario: 材料完成且模型相容
- **WHEN** 某區段完成三站、品質延遲到期且 v3 模型輸入相容
- **THEN** 四項預測以同一區段及模型版本顯示，並與實測／模擬真值及製程 SPC 分開標示

#### Scenario: 尚無可預測材料
- **WHEN** Run 剛開始或沒有完成三站的材料
- **THEN** 四項顯示等待材料完成，不沿用 fixture、舊 Run 或 v2 預測

## REMOVED Requirements

### Requirement: WS-01 單一主畫面與原定功能配置

**Reason**: 舊需求以模式 A、四 Tabs、五目標及 SHAP 一般入口為核心，與已確認的單一 Mode B 控制台不相容。

**Migration**: 以 WS-08 至 WS-11 的 Gate 0 與四頁控制台取代；可重用服務保留，SHAP UI 暫停且不刪除底層程式。
