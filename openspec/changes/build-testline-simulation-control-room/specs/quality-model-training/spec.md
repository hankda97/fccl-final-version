# Spec Delta

## ADDED Requirements

### Requirement: QMT-08 v3 四目標模型組

Synthetic v3 SHALL 分別訓練抗剝離、尺寸安定性 MD、尺寸安定性 TD 與耐熱度四個連續目標；Random Forest MUST 作 Champion 候選、HistGradientBoosting 作 Challenger，並保留簡單 baseline。初版控制台不得訓練或載入新的外觀模型。

#### Scenario: v3 訓練完成
- **WHEN** v3 canonical dataset 通過防洩漏與 split 驗證
- **THEN** 四目標各產生 baseline、RF、HGB 指標與 Champion 選擇證據，且 manifest 不宣告外觀輸出

#### Scenario: v2 外觀 artifact 存在
- **WHEN** 專案仍保有 v2 外觀模型
- **THEN** artifact 可供舊測試或回退保存，但不被四目標 bundle 載入或顯示於測試線控制台

### Requirement: QMT-09 v3 特徵與支援範圍

四目標模型 MUST 使用完成三站且推論當下可得的 v3 allowlist，納入乾膠厚度與排風量等三站特徵；manifest SHALL 依訓練資料記錄每項連續特徵的模型支援範圍，且不得以 UI 操作範圍代替。

#### Scenario: 特徵契約驗證
- **WHEN** 訓練或推論特徵缺少乾膠厚度、排風量、順序、單位或版本
- **THEN** 相依目標停止並回報不相容欄位，不以 v2 feature set 靜默推論

#### Scenario: 超出支援範圍
- **WHEN** Run 的候選或 actual 超出某模型記錄範圍
- **THEN** 該預測顯示外插或不可用狀態，且不宣稱其為經驗證改善

### Requirement: QMT-10 完成材料推論節奏

正式品質推論 SHALL 只針對完成塗佈、熟化、壓合及品質延遲的材料區段，並每 30 模擬秒或適用參數事件造成新可預測區段時更新；不得建立站別早期品質模型或預測整批良率。

#### Scenario: 30 秒更新
- **WHEN** 到達更新邊界且有新的完成區段
- **THEN** 系統以該區段實際可得特徵產生四目標預測並記錄 sample、Run、模型與輸入版本

#### Scenario: 沒有新完成區段
- **WHEN** 更新邊界到達但沒有新的適用材料
- **THEN** 不複製上一區段為新預測，畫面保留最新結果並標示其材料與時間

### Requirement: QMT-11 v3 評估與 demo 隔離

模型比較 MUST 使用 v3 的 120／40／40 完整卷 split，報告四目標 MAE、RMSE、R²、基準改善及穩定／漂移表現；所有 demo Run 與其固定 seed SHALL 排除於訓練、選模及最終 test。

#### Scenario: demo 洩漏檢查
- **WHEN** 任一 demo Run 識別、seed 或資料 hash 出現在模型資料來源
- **THEN** 訓練驗證失敗，不得產生可供控制台載入的正式 bundle
