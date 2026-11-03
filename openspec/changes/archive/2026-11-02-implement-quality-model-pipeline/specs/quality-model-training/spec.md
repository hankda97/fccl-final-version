# Spec Delta

## Purpose

建立可由版本化 canonical dataset 重現的五目標品質模型訓練、比較與交付契約，使模型產物可驗證、可回退，並明確限制合成資料模型的適用範圍。

## ADDED Requirements

### Requirement: 逐目標訓練資料與防洩漏

系統 SHALL 為抗剝離、尺寸 MD、尺寸 TD、耐熱度與外觀 NG 分別建立訓練資料，只納入該目標 availability 有效的列；特徵 MUST 來自預測當下已可取得的 allowlist，並排除品質真值、規格判定、預測輸出、識別捷徑及漂移真值。

#### Scenario: 部分標籤可用

- **WHEN** canonical 列只有部分品質標籤有效
- **THEN** 每個目標模型只取得自己的有效列，其他空白目標不補值且不使有效目標整列被刪除

#### Scenario: 洩漏欄位出現在候選特徵

- **WHEN** 候選特徵包含目標、pass flag、availability、規格值、卷／批號識別或 drift ground truth
- **THEN** 訓練驗證 SHALL 拒絕該特徵集合並回報具體欄名

### Requirement: 完整卷時間隔離

系統 MUST 使用不可跨分割的完整卷及其時間順序建立 train、validation、test；前處理、特徵選擇與超參數調整只可由 train／validation 決定，test MUST 保留至最終評估。

#### Scenario: v2 預定分割

- **WHEN** 使用 `generated_data/v2` 的版本化分割
- **THEN** train／validation／test 分別包含 120／40／40 個互斥完整卷，且所有模型比較使用相同卷集合

#### Scenario: 卷跨越分割

- **WHEN** 任一 `root_roll_id` 同時出現在多個 split 或時間順序與 manifest 不一致
- **THEN** 系統 MUST 停止訓練，不得退回隨機逐列切分

### Requirement: 基準與 Champion／Challenger

系統 SHALL 為四個連續目標建立簡單迴歸基準，為外觀 NG 建立常數或 Logistic 基準；Random Forest SHALL 作初版 Champion，HistGradientBoosting SHALL 作必要 Challenger，並依相同資料、前處理版本及指標比較。

#### Scenario: 初版模型比較

- **WHEN** 五個目標資料通過訓練前檢查
- **THEN** 每個目標均產生基準、Random Forest 與 HistGradientBoosting 的 validation／test 結果及相對基準改善

#### Scenario: 選配模型未安裝

- **WHEN** XGBoost、LightGBM 或深度學習套件未安裝
- **THEN** 必要訓練流程仍可完成，且不得把選配模型缺失記為核心流程失敗

### Requirement: 逐目標評估與分層報告

系統 SHALL 對迴歸模型報告 MAE、RMSE、R²及相對基準表現，對外觀分類報告 PR-AUC、precision、recall、F1、confusion matrix、類別比例及適用時的機率校準；結果 MUST 同時按 split 與穩定／漂移驗證區間分層。

#### Scenario: 分類測試集含 NG

- **WHEN** test split 含有效外觀 OK 與 NG 標籤
- **THEN** 系統以明確 NG 標籤 1 計算分類指標、門檻結果與 confusion matrix，不固定假設輸出陣列位置

#### Scenario: 評估資料不足

- **WHEN** 某目標缺少類別、有效卷或足夠標籤而無法計算指定指標
- **THEN** 該指標標示不可用及原因，模型不得因虛構分數升為 Champion

### Requirement: 模型升版與回退

Challenger 只有在預先記錄的主要指標、重大目標退化、漂移穩定性、推論延遲及相容性條件均通過後才可升版；系統 MUST 保留現任 Champion、候選比較證據與可執行回退資訊。

#### Scenario: Challenger 單一指標較佳

- **WHEN** Challenger 只在單一指標優於 Champion，但其他必要條件未通過
- **THEN** 現任 Champion 保持不變，差異與拒絕原因寫入比較結果

#### Scenario: 新 Champion 不可載入

- **WHEN** 新模型 artifact 缺失、hash 不符或與執行環境不相容
- **THEN** 正式 Adapter 回退至已驗證 Champion或明示不可用，不得靜默改用未驗證模型

### Requirement: 版本化可信模型產物

每次成功訓練 SHALL 產生受信任模型 bundle、registry、manifest 與 metrics；manifest MUST 記錄模型／資料／schema／feature／preprocessing／label／spec 版本、來源、split、seed、套件、超參數、指標、類別映射及檔案 hash。

#### Scenario: 相同版本重現

- **WHEN** 使用相同資料 hash、設定、seed 與相容套件環境重新訓練
- **THEN** 系統產生可比較的資料列數、分割、特徵順序、模型設定與評估結果，任何非決定性差異須明示

#### Scenario: 未受信任模型來源

- **WHEN** 使用者上傳序列化模型或 artifact 不在可信專案路徑且無相符 manifest／hash
- **THEN** 系統 MUST 拒絕反序列化或推論，不將 CSV 上傳作為模型載入入口

### Requirement: 合成模型適用範圍

以 `synthetic_ground_truth` 或 `simulated_inspection` 訓練的模型 MUST 在 manifest、metrics 與 UI 標示 Synthetic／Mock 來源；其結果不得宣稱為真實產線效能、因果效果或設備控制依據。

#### Scenario: v2 模型交付

- **WHEN** 模型使用 `generated_data/v2` 訓練並接入 Streamlit
- **THEN** 畫面與產物清楚顯示合成資料版本、標籤來源與限制，且不移除 C 公式 Mock 的獨立來源標示
