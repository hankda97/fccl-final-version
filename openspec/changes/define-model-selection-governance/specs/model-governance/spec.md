# Model Governance Delta Spec

## ADDED Requirements

### Requirement: 統一模型介面

所有品質模型 SHALL 透過版本化 Adapter 提供 fit、predict、必要時 predict_proba、explain、serialize 與 compatibility validation。manifest MUST 記錄 model type、版本、feature schema、資料 hash、seed、超參數與套件版本。

#### Scenario: 新增候選模型

- WHEN 新模型符合 Adapter 與 manifest 契約
- THEN 可用相同資料分割與指標進行 Challenger 評估，不需修改 canonical data contract

### Requirement: Champion／Challenger

Random Forest SHALL 作初版 Champion；常數／線性模型 SHALL 作基準；HistGradientBoosting SHALL 作初版 Challenger。XGBoost 或 LightGBM MAY 作外部 Challenger，但不得因單一指標較高自動取代 Champion。

#### Scenario: Challenger 升級

- WHEN Challenger 在未來完整卷測試上達到預先定義的主要指標且沒有重大目標退化
- THEN 經版本化審查後才可成為新 Champion

### Requirement: 序列模型啟用條件

LSTM／GRU MUST NOT 作初版必交模型。只有在定義 forecast horizon、固定序列、卷界線、缺測處理及足夠獨立序列，且樹模型加 lag／rolling 基準仍不足時，才可建立序列 Challenger。

#### Scenario: horizon 未定義

- WHEN 尚未定義預測未來的時間距離與標籤對齊
- THEN 系統不得宣稱 LSTM／GRU 預測未來品質

### Requirement: 異常偵測分層

SPC SHALL 保留為主要可解釋監控。PCA／Isolation Forest SHALL 作無監督基準；Autoencoder MAY 作非線性 Challenger。anomaly score MUST NOT 被稱為品質 NG 機率。

#### Scenario: Autoencoder 評估

- WHEN Autoencoder 只以穩定正常資料訓練
- THEN 門檻須由獨立 validation 選擇，並以漂移真值報告 precision、recall、誤報率及偵測延遲

### Requirement: 相同分割與降級

所有候選模型 MUST 使用相同的卷級時間切分及 target availability。模型不可用或不相容時 SHALL 回退至有效 Champion、基準模型或 SPC，且不得偽造輸出。

#### Scenario: 分類模型缺少類別

- WHEN train split 不含足夠 NG 類別
- THEN 分類模型不得提供有意義的風險排序或升級為 Champion
