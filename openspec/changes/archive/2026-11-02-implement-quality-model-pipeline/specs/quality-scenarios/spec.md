# Spec Delta

## ADDED Requirements

### Requirement: Q-06 正式品質模型 Adapter

系統 SHALL 透過版本化正式 Model Adapter 對齊輸入索引及特徵順序，輸出四項連續品質預測、外觀 NG 類別與標籤 1 的校準風險；Adapter MUST 驗證模型 manifest 與資料來源相容性，並與 C 公式 Mock 保持獨立來源及狀態。

#### Scenario: 正式五目標推論

- **WHEN** 選定的 canonical projection 與五個 Champion artifact 均通過 manifest、hash、欄位、單位及版本檢查
- **THEN** 目前監控與固定 What-if 依原樣本順序取得五目標結果、模型版本、來源、適用範圍及逐目標狀態

#### Scenario: 部分目標模型不可用

- **WHEN** 某目標 artifact 缺失、不相容或必要特徵無效
- **THEN** 只將受影響目標標示不可用並說明原因，不以零、Mock、其他目標或舊結果冒充正式預測

### Requirement: Q-07 正式 What-if 與模型限制

正式模型 What-if SHALL 只改動已解鎖且位於訓練支援範圍的 allowlist 參數，固定不可控特徵及原始區段識別；候選結果 MUST 標示為模型情境推論，不得宣稱因果改善或直接控制設備，也不得新增「當下預測良率」。

#### Scenario: 支援範圍內候選

- **WHEN** 使用者調整允許參數且候選仍位於模型 manifest 的訓練支援範圍
- **THEN** 系統顯示目前與候選的五目標預測、差值、規格狀態、外觀 NG 風險、模型版本與非因果限制

#### Scenario: 候選超出支援範圍

- **WHEN** 任一候選參數超出允許或訓練支援範圍，或相依衍生特徵無法一致重算
- **THEN** 系統拒絕正式候選建議並顯示具體範圍或相依原因，不外推改善幅度

### Requirement: Q-08 正式模型降級與來源切換

正式模型載入或推論失敗時，系統 SHALL 保留有效資料、SPC 與介面狀態，並明確提供不可用原因；只有使用者明確選擇 C 公式 Mock 時才可顯示 Mock 結果，MUST NOT 靜默由正式模型切換成 Mock。

#### Scenario: 正式 artifact 載入失敗

- **WHEN** bundle 無法載入、manifest hash 不符或套件版本不相容
- **THEN** 正式預測、正式 What-if 與相依 SHAP 標示不可用，其他不依賴模型的功能仍可使用

#### Scenario: 使用者切換至公式 Mock

- **WHEN** 使用者在正式模型不可用後主動選擇 C 公式 Mock
- **THEN** 系統以 Mock 來源與版本重新計算示範結果，且不得保留正式模型、校準機率或真正 SHAP 的標示
