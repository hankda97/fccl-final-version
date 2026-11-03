# Spec Delta

## ADDED Requirements

### Requirement: VIS-05 正式樹模型 SHAP 解釋

系統 SHALL 由已載入的正式 Champion 與其 manifest 提供真正的 SHAP Summary／Dependence 解釋；解釋 MUST 使用與推論相同的前處理、特徵順序與模型版本，背景資料只可來自對應 train split，並以固定 seed 及有界樣本量建立。

#### Scenario: 迴歸目標解釋

- **WHEN** 使用者選擇任一可用連續品質 Champion 及相容資料切片
- **THEN** 系統回傳與樣本及特徵對齊的回歸輸出貢獻值、基準值、背景來源、模型／manifest／解釋版本與單位

#### Scenario: 外觀 NG 解釋

- **WHEN** 使用者選擇外觀 NG Champion
- **THEN** 系統依 manifest 的 class labels 明確選擇標籤 1，並標示 SHAP 的 probability、raw margin 或 log-odds 尺度，不固定取陣列第二個輸出

### Requirement: VIS-06 解釋相容性與失效

正式解釋 SHALL 驗證 dataset source、schema、feature、preprocessing、label、spec、model、manifest、background 與 class mapping；任何相依版本、資料範圍、模型或選項改變時，舊 SHAP 結果 MUST 失效且不得以新標籤繼續顯示。

#### Scenario: Manifest 不匹配

- **WHEN** Explanation Provider 與目前選定模型的 manifest、特徵順序、輸出尺度或背景版本不一致
- **THEN** 系統拒絕解釋並顯示不一致欄位，不影響有效預測、Heatmap、SPC 或資料檢查

#### Scenario: 模型切換後舊結果抵達

- **WHEN** 使用者切換 Champion／資料來源後收到舊模型的延遲 SHAP 回應
- **THEN** 該回應保持過期或被丟棄，不得取代目前模型的圖表狀態

### Requirement: VIS-07 SHAP 資源與失敗隔離

系統 MUST 限制正式 SHAP 的資料列與背景樣本量，提供計算中、可用、不可用及錯誤狀態；計算錯誤或不支援目標只可影響相依圖區，且暫時圖形與運算資源 SHALL 在完成或失敗後釋放。

#### Scenario: 解釋計算失敗

- **WHEN** SHAP 計算超出限制、模型不支援或 Provider 回報可處理錯誤
- **THEN** 相依圖區顯示具體原因及可重試狀態，不保留舊圖冒充完成結果，其他模型與儀表板功能保持可用
