# Proposal：定義模型選擇與生命週期治理

## 目的

在不一次實作所有模型的前提下，先固定可插拔模型介面、Champion／Challenger 比較、序列模型與異常模型啟用條件，避免後續擴充時重寫資料與 UI 契約。

## 範圍

- 保留 Random Forest 作初版 Champion。
- 加入簡單基準及 HistGradientBoosting Challenger。
- 為 XGBoost／LightGBM 預留樹模型 Adapter。
- 為 LSTM／GRU 與 Autoencoder 定義啟用門檻，不列為初版必交。
- 分開品質預測、異常偵測與 SPC。

## 審查狀態

使用者已授權更新本機模型治理草案；實際新增外部套件與模型實作仍須在對應 task 明確執行與驗證。
