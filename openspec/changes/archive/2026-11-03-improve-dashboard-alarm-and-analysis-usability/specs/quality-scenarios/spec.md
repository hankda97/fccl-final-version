# Spec Delta

## ADDED Requirements

### Requirement: Q-11 What-if 就緒條件與可恢復空狀態

系統 SHALL 分別驗證資料已載入、目前篩選非空、區段識別有效、必要製程特徵可用及所選 Adapter 能力；未就緒時 MUST 指出失敗層級、保留有效工作區狀態並提供可執行下一步，不得只顯示「尚無建議」或暗色控制項。

#### Scenario: Canonical 只選取未載入
- **WHEN** 使用者已選 Canonical 來源但工作區尚無成功載入的 dataset
- **THEN** What-if 顯示資料尚未載入並指示執行「載入 Canonical projection」，不顯示成資料本身缺少區段

#### Scenario: 篩選造成空切片
- **WHEN** dataset 已載入但批次／時間篩選沒有任何有效區段
- **THEN** What-if 顯示目前篩選為空、已載入資料來源及清除／調整篩選的下一步，不清除原 dataset 或使用篩選外資料

#### Scenario: 區段或特徵不完整
- **WHEN** 目前切片有資料但缺少有效批次／材料區段識別、sample ID、線速或 Adapter 必要特徵
- **THEN** 系統列出缺少的識別或特徵，僅停用相依控制與目標，不把所有缺陷統稱為沒有資料

#### Scenario: Mock 與正式來源一致性
- **WHEN** 使用者選擇 C 公式 Mock 或 Synthetic 正式 artifact
- **THEN** What-if 標題、比較、Alarm、建議與能力提示均使用同一 Adapter；正式模型不可用時不得以 Mock 結果補值，Mock 模式須明示不提供真正 SHAP

#### Scenario: 就緒後參數比較
- **WHEN** 有有效區段、線速與相容 Adapter，且使用者調整允許參數
- **THEN** 系統顯示調整前後五目標預測、差值、來源、版本、情境風險與建議或具體無建議原因，不修改實測資料與 SPC
