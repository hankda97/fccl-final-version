# Spec Delta

## ADDED Requirements

### Requirement: VIS-08 Heatmap 相關方向摘要

Heatmap 可用時，系統 SHALL 對每個選定品質目標摘要最強正相關與最強負相關的製程／環境特徵、Pearson r 及有效配對數；摘要 MUST 依品質目標規格方向避免把相關正負號直接宣稱為改善，並持續明示相關不代表因果。

#### Scenario: 同時存在正負相關
- **WHEN** 某品質目標有至少一個可計算的正相關及負相關特徵
- **THEN** 系統顯示兩個方向中絕對值最高的特徵、r、n、單位與目前資料範圍，且數值與 Heatmap 格子一致

#### Scenario: 只有單方向或不可計算
- **WHEN** 只有正或負方向可計算，或所有格子因樣本不足、無變異或標籤不可用而無法計算
- **THEN** 系統只顯示可支持的方向，並對缺少方向或整個目標顯示具體原因，不補零或挑選無效格子

#### Scenario: 品質規格方向解讀
- **WHEN** 摘要涉及越高越佳、越低越佳或需落在區間／接近中心的不同品質目標
- **THEN** 系統分別標示相關方向與品質規格方向；MD／TD 等區間型目標不得僅依 r 正負號稱為有利或不利，外觀 NG 亦須明示 1 代表 NG

#### Scenario: 篩選與選項更新
- **WHEN** 使用者改變批次、時間、特徵或品質目標選項
- **THEN** 相關摘要與 Heatmap 使用完全相同的有效配對、來源身分與版本重新計算，舊摘要不得留在新圖旁

### Requirement: VIS-09 Heatmap 與 SHAP 可用性導引

系統 MUST 對 Heatmap、SHAP Summary 與 SHAP Dependence 分別顯示未載入、可用、計算中、不可用或錯誤狀態，以及資料來源、模型來源、阻塞原因與下一步。選項控制可停用，但狀態說明 SHALL 保持正常可讀對比。

#### Scenario: 尚未載入資料
- **WHEN** 工作區沒有成功載入的 dataset
- **THEN** Heatmap 與 SHAP 明示尚未載入資料並指示載入動作，不將已選來源誤寫成已載入，也不只顯示 `No options to select`

#### Scenario: Canonical 已載入且選用 Mock
- **WHEN** Canonical 資料可供 Heatmap 使用，但目前 Adapter 為 C 公式 Mock
- **THEN** Heatmap 可獨立計算；SHAP 顯示 Mock 不具真正解釋能力，提示如需真正 SHAP 應選 Synthetic 正式 artifact，且不產生偽造圖形

#### Scenario: 正式 SHAP 已就緒
- **WHEN** Synthetic 正式 artifact、Explanation Provider、manifest 與目前 Canonical 切片相容
- **THEN** Summary／Dependence 顯示可用狀態、模型與解釋版本並產生匹配圖形；控制項與圖形使用正常可讀對比

#### Scenario: 正式模型或解釋不相容
- **WHEN** artifact、manifest、來源 profile、必要特徵、目標或 Explanation Provider 驗證失敗
- **THEN** SHAP 顯示具體不相容欄位或缺項及恢復方式，不保留舊圖、不自動切換 Mock，且 Heatmap、What-if、SPC 與資料檢查保持獨立

#### Scenario: Summary 與 Dependence 的用途說明
- **WHEN** 使用者查看 SHAP 分析入口
- **THEN** Summary 說明其呈現整體特徵貢獻分布，Dependence 說明橫軸特徵值與縱軸 SHAP 貢獻；兩者均標示輸出尺度、單位及非因果限制
