# Spec Delta

## ADDED Requirements

### Requirement: WS-05 模型預測與實測 SPC 分區摘要

系統 SHALL 將目前區段的五項模型結果與四項連續品質的實測 SPC 分成具獨立標題、來源與狀態的摘要區；模型區不得以 SPC 子組均值代替預測，SPC 區不得以模型預測代替實測，外觀模型風險不得混入 X-bar 摘要。

#### Scenario: 正式模型與 SPC 同時可用
- **WHEN** canonical projection、正式五目標模型與實測 SPC 均可用
- **THEN** 模型區顯示四項連續預測及外觀 NG 類別／風險，SPC 區另顯示四項最新有效實測子組均值、管制狀態與基準來源

#### Scenario: 模型可用但 SPC 不可判定
- **WHEN** 正式模型可推論但 SPC 缺少有效取樣證據或基準
- **THEN** 模型區仍顯示五項正式模型結果，SPC 區逐目標顯示不可判定及原因，不以預測值補成 SPC 數值

#### Scenario: SPC 可用但模型不可用
- **WHEN** 實測 SPC 可用但選定 Adapter 無法推論
- **THEN** SPC 區仍顯示實測結果，模型區逐目標顯示不可用原因，不以 SPC 值、Mock 或舊預測冒充模型輸出

### Requirement: WS-06 摘要來源文字與當前能力一致

系統 MUST 依當前 Adapter、資料、SPC profile 與基準的實際狀態產生摘要及 Alarm 說明；正式模型模式不得顯示 Mock 或「正式模型尚未接入」，Mock 模式不得標示為正式模型，且不可用模式不得暗示已有模型結果。

#### Scenario: 選用正式模型
- **WHEN** 使用者選擇 Synthetic 正式模型 artifact
- **THEN** 模型摘要與預測 Alarm 顯示正式模型來源、版本、合成資料限制及逐目標能力，不出現 Mock 或「尚未接入」過時文字

#### Scenario: 主動選用 C 公式 Mock
- **WHEN** 使用者明確選擇 C 公式 Mock
- **THEN** 模型摘要與預測 Alarm 標示公式 Mock、版本、示範及非校準限制，不沿用正式模型或真正 SHAP 標示

#### Scenario: 來源或能力在重跑後改變
- **WHEN** 資料、Adapter、模型 profile 或 SPC profile 切換使來源或能力改變
- **THEN** 所有摘要、caption、Alarm 與不可用說明於同次重跑一致更新，不保留前一來源的文字或結果
