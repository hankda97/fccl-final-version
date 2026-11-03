# Spec Delta

## ADDED Requirements

### Requirement: SPC-10 品質 SPC 與製程 SPC 分離

既有品質 SPC 與測試線製程 SPC MUST 使用不同目標、取樣契約、baseline、事件類型及頁面標示；乾膠厚度屬製程量測，四項模型預測不得作製程或品質 SPC 的實測點。

#### Scenario: 同時存在品質與製程訊號
- **WHEN** Run 同時有厚度、溫度等 actual 與四項品質預測
- **THEN** 製程 SPC 只使用適用 actual，品質預測另區顯示，不合併界限、狀態或 Alarm

### Requirement: SPC-11 產品規格、配方與管制界限

所有 SPC 畫面 SHALL 分開顯示產品允收規格、配方 setpoint／標準範圍及統計管制界限；系統 MUST 分別判定製程失控與產品超規，不得由其中一項推定另一項。

#### Scenario: 受控但偏離配方目標
- **WHEN** 訊號仍在固定管制界限內但偏離配方標準
- **THEN** 畫面分別呈現其配方偏差與 SPC 狀態，不產生虛假的產品合格結論

#### Scenario: 製程失控但未超規
- **WHEN** SPC 規則觸發但目前量測仍在產品允收範圍
- **THEN** 事件標示製程失控且尚未觀測產品超規，仍保留警告或嚴重分級

### Requirement: SPC-12 連續 Run 的增量與效能邊界

製程 SPC SHALL 每 tick 增量更新並只保留首頁最近 60 點的繪圖視窗；完整事件與資料由 Run 紀錄保存。計算延遲不得造成重疊 tick，超時時 MUST 配合模擬器降速或暫停。

#### Scenario: 長時間 Run
- **WHEN** Run 已累積超過 60 個訊號點
- **THEN** 首頁圖表只渲染最近 60 點，固定 baseline 與完整事件統計仍使用正確歷史且可由詳細頁查閱

### Requirement: SPC-13 Alarm 生命週期與無人工簽核範圍

製程 Alarm SHALL 由有效後續證據自動復歸，初版不提供 acknowledge、sign-off、silence、工單或 MES 動作；任何 UI 操作不得被描述為產線處置完成。

#### Scenario: 使用者查看開啟事件
- **WHEN** 事件尚未取得復歸證據
- **THEN** 使用者只能查看、篩選或調整本機模擬參數，不能以按鈕將事件標為已處理或靜音
