# Data Integration Delta Spec

## ADDED Requirements

### Requirement: 七表來源層與 canonical model table 分離

系統 SHALL 保留七份來源表的原始粒度與追溯鍵，並在模型訓練前建立版本化 canonical model table。`drift_ground_truth` MUST 僅供驗證，不得作模型特徵。

#### Scenario: 來源表載入

- WHEN 七份來源表通過 schema 與版本驗證
- THEN 系統保留原始列與識別欄，且不以平面 JOIN 覆寫來源資料

#### Scenario: 漂移真值隔離

- WHEN 建立模型特徵 allowlist
- THEN 所有漂移事件識別、方向、強度與事件區間 MUST 被排除

### Requirement: 三站材料 MD 區間對齊

系統 SHALL 使用 `root_roll_id` 與材料 MD 區間對齊 coating、curing、lamination。區間 MUST 採 `[start, end)` 語意；多區段重疊的數值特徵 SHALL 依重疊長度聚合。

#### Scenario: 完整重疊

- WHEN 品質錨點在三站皆有足夠材料覆蓋
- THEN 系統產生唯一 `aligned_sample_id`、覆蓋率及來源區段清單

#### Scenario: 覆蓋不足或衝突

- WHEN 任一站無對應區段、覆蓋率低於設定門檻或同站區段衝突
- THEN 系統回報結構化問題，且 MUST NOT 以鄰近列靜默補齊

### Requirement: 目標標籤來源與粒度

系統 SHALL 分開管理 synthetic ground truth 與 simulated inspection。正式 inspection-supervised 模型 MUST 使用有效檢驗標籤；整卷結果 MUST NOT 複製為區段標籤。

#### Scenario: 區段品質模型

- WHEN 訓練剝離、MD、TD、耐熱或外觀模型
- THEN 系統只使用該目標 availability 通過且粒度相容的資料列

#### Scenario: 整卷資格檢驗

- WHEN 檢驗沒有 `segment_id` 或材料位置
- THEN 該結果只供卷級驗證或獨立卷級模型使用

### Requirement: 規格版本與 pivot

規格 SHALL 以 `product_id + spec_version + characteristic` 唯一識別，並以明確 characteristic mapping 轉為 canonical 欄位。缺少相符版本時 MUST NOT 自動取 latest 或其他版本。

#### Scenario: 規格缺失

- WHEN 找不到完全相符的產品與規格版本
- THEN 系統標示 `SPEC_NOT_FOUND`，且不得宣稱樣本合格

### Requirement: 重複檢驗與重測

原始檢驗事件 MUST 保留。預定平行試驗、失敗後重測與無效試驗 SHALL 分開識別；未能判定關係或有效標籤衝突時不得進入訓練。

#### Scenario: 失敗後重測

- WHEN 有效初次結果之後出現重測
- THEN 重測不得覆蓋初次結果，並保留 parent／reason 追溯

#### Scenario: 無法辨識的重複檢驗

- WHEN 相同區段與 characteristic 有多筆結果但缺少重測 metadata
- THEN 系統標示 `DUPLICATE_INSPECTION_AMBIGUOUS` 並排除該目標

### Requirement: 外觀標籤與允收旗標

`appearance_ng_flag` SHALL 作為外觀分類真值。`appearance_spec_pass_flag` SHALL 由明確允收規則產生；沒有豁免規則時兩者 MUST 互補。

#### Scenario: 外觀旗標衝突

- WHEN `appearance_ng_flag=1` 且 `appearance_spec_pass_flag=1`，但沒有 disposition／waiver 證據
- THEN 系統標示 `APPEARANCE_FLAG_CONFLICT`，不得以 spec pass 覆蓋 NG

### Requirement: 逐目標 availability

`quality_label_available` SHALL 表示至少一項有效品質標籤。系統 MUST 另計算五個逐目標 availability；目標空值不得補成 0。

#### Scenario: 部分標籤可用

- WHEN 一列只有部分目標通過有效性、方法、粒度及衝突檢查
- THEN 可用模型只使用自己的有效標籤，其他模型不得補造目標
