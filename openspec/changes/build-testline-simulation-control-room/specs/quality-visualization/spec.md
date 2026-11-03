# Spec Delta

## ADDED Requirements

### Requirement: VIS-10 材料區段層級 Heatmap

測試線 Heatmap MUST 以一個已完成材料區段為一列，將該區段各站的 5 秒訊號依版本化規則聚合後與四項品質配對；不得把同一品質值複製到每個 tick 以增加樣本數。

#### Scenario: 聚合目前 Run
- **WHEN** 一個區段完成且四項品質可用
- **THEN** 該區段最多貢獻一列，並記錄各特徵聚合方法、有效 tick 數、站別範圍與品質版本

#### Scenario: 區段資料不足
- **WHEN** 某站沒有足量有效訊號或品質尚未可得
- **THEN** 相依配對排除並顯示原因，不以鄰近區段或未來值補齊

### Requirement: VIS-11 v3 Reference 與目前 Run 來源

Heatmap SHALL 允許使用者選擇 Synthetic v3 reference 或目前 Run；目前 Run 至少須有 30 個完成且有效區段才可計算。兩來源 MUST 分別顯示版本、區段數、範圍及「相關不代表因果」限制。

#### Scenario: 目前 Run 樣本不足
- **WHEN** 目前 Run 有效完成區段少於 30
- **THEN** Heatmap 顯示尚缺數量並保持不可計算，不退回或混入 v3 reference

#### Scenario: 切換資料來源
- **WHEN** 使用者由 reference 切換至目前 Run
- **THEN** 舊結果失效，只有新來源通過門檻後才顯示匹配 Heatmap 與正負相關摘要

### Requirement: VIS-12 按需計算與 SHAP 暫停入口

Heatmap MUST 由使用者按鈕觸發並快取匹配結果，不得每個 5 秒 tick 重算；測試線一般導覽 SHALL 隱藏 SHAP Summary 與 Dependence 入口，但不得刪除既有解釋程式或 v2 測試能力。

#### Scenario: Run 持續更新
- **WHEN** 新 tick 或新完成區段到達但使用者未要求重算
- **THEN** 既有 Heatmap 標示其截止與是否過期，不自動執行重計

#### Scenario: 一般使用者導航
- **WHEN** 使用者瀏覽四個測試線頁面
- **THEN** 不顯示 SHAP Summary／Dependence 控制或空白占位，What-if 與 Heatmap 保持可尋得
