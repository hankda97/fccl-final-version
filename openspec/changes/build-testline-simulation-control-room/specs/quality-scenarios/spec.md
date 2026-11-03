# Spec Delta

## ADDED Requirements

### Requirement: Q-12 Run 隔離的材料區段 What-if

What-if MUST 固定一個已完成三站且四目標可推論的材料區段，在獨立情境比較基準與候選參數；計算 SHALL 不改變 live Run、過去材料、actual 訊號、SPC、Alarm 或參數事件。

#### Scenario: 建立可用情境
- **WHEN** 使用者從目前 Run 選擇已完成且 v3 特徵相容的材料區段
- **THEN** 系統固定其識別、來源、模型與基準輸入，顯示四目標前後值、差異、支援範圍及非因果限制

#### Scenario: live Run 繼續推進
- **WHEN** What-if 開啟期間新的 tick、預測或 Alarm 到達
- **THEN** 固定情境不改用最新材料，live Run 也不套用候選值

### Requirement: Q-13 候選回填與二次確認

What-if 結果不得直接控制 Run；使用者若採用候選值，系統 SHALL 將支援的值回填至生產控制台表單，並要求再次驗證及確認後才建立參數事件。

#### Scenario: 採用候選值
- **WHEN** 使用者在 What-if 選擇「帶回控制台」
- **THEN** 系統只更新尚未提交的候選表單、保留來源情境，且 live setpoint 不變

#### Scenario: 回填後拒絕或修改
- **WHEN** 使用者取消、修改或驗證失敗
- **THEN** 不建立參數事件，What-if 結果與 live Run 仍可分別追溯

### Requirement: Q-14 四目標與操作限制

測試線 What-if SHALL 只顯示四個 v3 連續品質目標與七項主要參數及明確支援的進階參數；不得顯示外觀、預測良率或把相關／模型貢獻宣稱為因果改善。

#### Scenario: 候選超出模型支援
- **WHEN** 任一候選值超出相依模型 manifest 支援範圍
- **THEN** 系統拒絕正式比較或明示不可外推，不以配方或 UI 範圍保證品質結果
