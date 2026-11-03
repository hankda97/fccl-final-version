# Spec Delta

## ADDED Requirements

### Requirement: Q-09 目前區段五目標模型摘要

系統 SHALL 對目前可見區段依選定 Adapter 顯示抗剝離度、尺寸安定性 MD／TD、耐熱度與外觀 NG 的模型結果；每項須包含預測值或類別／風險、單位、可用狀態，並共同顯示樣本識別、模型來源及版本。部分目標失敗不得阻擋其他有效目標。

#### Scenario: 正式五目標結果完整
- **WHEN** 正式 Adapter 對目前區段成功產生四項迴歸及外觀分類結果
- **THEN** 摘要顯示四項預測值與單位、外觀 NG 類別及標籤 1 的校準風險，並標示正式模型來源、版本與 Synthetic 限制

#### Scenario: 只有部分正式目標可用
- **WHEN** 一項或多項正式 artifact、特徵或推論結果不可用
- **THEN** 有效目標照常顯示，失敗目標顯示具體原因，且不得由 Mock、SPC、實測真值或先前結果補值

#### Scenario: Mock 五目標結果
- **WHEN** 使用者主動選擇 C 公式 Mock 且目前區段輸入有效
- **THEN** 摘要顯示五項公式結果並清楚標示 Mock、公式版本及外觀風險未校準，不宣稱為正式模型結果

### Requirement: Q-10 模型來源切換的原子一致性

系統 MUST 讓摘要、預測 Alarm、What-if 與解釋能力使用同一個已選 Adapter 來源；來源切換或正式模型失效時，所有相依結果須一併失效或重算，且只有使用者明確選擇 Mock 才能產生 Mock 結果。

#### Scenario: 正式模型切換至 Mock
- **WHEN** 使用者由正式模型主動切換至 C 公式 Mock
- **THEN** 正式摘要、Alarm、What-if 與 SHAP 狀態一併失效，重新產生的結果全部標示 Mock，真正 SHAP 不再可用

#### Scenario: 正式模型載入或推論失敗
- **WHEN** 使用者仍選擇正式模型但其 registry、artifact、相容性或推論驗證失敗
- **THEN** 正式模型相依結果顯示不可用與原因，SPC／資料檢視保持獨立可用，系統不得自動改用 Mock
