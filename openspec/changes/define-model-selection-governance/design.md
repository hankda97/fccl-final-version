# Design：模型治理

## 模型層級

- Tier 0：常數、Linear／Logistic 基準。
- Tier 1：Random Forest Champion。
- Tier 2：HistGradientBoosting；選配 XGBoost 或 LightGBM Challenger。
- Tier 3：達到啟用條件後的 GRU／LSTM 序列 Challenger。
- Anomaly：SPC → PCA／Isolation Forest → Autoencoder。

初版不強制安裝 XGBoost、LightGBM 或深度學習套件。依賴只有在實際建立對應 Change 並驗證序列化、SHAP／解釋與部署相容後才加入鎖檔。

## 比較原則

迴歸比較 MAE、RMSE、R²、規格判定錯誤及穩定／漂移分層表現；分類比較 PR-AUC、precision、recall、F1、confusion matrix 與機率校準。任何升級需在完整未來卷 holdout 驗證。

## 改善循環

採週期性離線重訓，不採逐筆無審核線上學習。每次訓練保存 dataset version、model version、recommendation version 與前後驗證結果。
