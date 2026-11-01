# Data Generation v2 Delta Spec

## ADDED Requirements

### Requirement: 資料規模與切分

生成器 SHALL 預設建立 200 個獨立卷、每卷約 100 個最終 canonical segments，並按完整卷及時間順序切為 120／40／40 個 train／validation／test 卷。

#### Scenario: 預設生成

- WHEN 使用 v2 預設設定與 seed 42
- THEN 產生約 20,000 個 final segments，且同一卷不得跨資料分割

### Requirement: 區段聯合良率

`overall_pass_flag` SHALL 由四個連續品質符合規格且 `appearance_ng=0` 共同決定。預設全資料區段聯合良率 MUST 落在 78% 至 82%。

#### Scenario: 良率驗證

- WHEN 七表生成完成
- THEN 驗證器以固定規格重新計算良率，且結果與輸出旗標一致

### Requirement: 合理失敗機制

超規 MUST 由環境、塗佈、熟化、壓合、批次效應、時間自相關及漂移事件的可追溯組合產生。生成器 MUST NOT 以隨機翻轉標籤、修改規格、複製 NG 或邊界裁切湊良率。

#### Scenario: 多目標共同失敗

- WHEN 同一製程失敗機制影響多項品質
- THEN 相關目標可合理共同超規，並在 drift ground truth 保留事件來源

### Requirement: 穩定期與漂移期

生成器 SHALL 提供足量穩定資料建立 Phase I 基準，並提供輕微與明顯漂移驗證 SPC。穩定基準資料 MUST 與漂移監控資料分開識別。

#### Scenario: Phase I 基準

- WHEN 選取穩定卷與穩定區間
- THEN 每個適用條件至少可形成 25 個有效子組，且不含已知漂移事件

### Requirement: synthetic ground truth 與 inspection 分離

完整區段品質 SHALL 標示 `synthetic_ground_truth`；依實際頻率抽樣的品質檢驗 SHALL 標示 `simulated_inspection`。兩者不得混稱為真實量測。

#### Scenario: inspection 缺少部分目標

- WHEN 檢驗類型只量測部分品質
- THEN 未量測欄位保持空白，逐目標 availability 正確反映可用性

### Requirement: 可重現與隔離輸出

相同版本設定與 seed SHALL 產生相同 CSV 位元組。v2 MUST 輸出至獨立目錄，不覆寫 `raw data`。

#### Scenario: 重跑

- WHEN 對同一輸出目錄重跑生成器
- THEN 七份 CSV 與 metadata 的內容 hash 保持一致
