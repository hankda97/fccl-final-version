# C6 專用測試資料

`hand_calculation.csv` 是四列人工設計的介面／算法測試，非真實 FCCL 資料，不是 A 的正式生成器輸出。線速對抗剝離的 Pearson 為 +1，對尺寸 MD 為 −1，對尺寸 TD 為 0；濕度是常數。配對最小數量 3 是 C 顯示設定，不代表獨立採樣或統計顯著性。

SHAP 測試由測試 Provider 注入明確標為 render-test 的固定 payload／Figure；不使用公式 Mock 值計算或假裝真正 SHAP。相關測試程式與標示只證明呈現接點，正式模型／尺度／背景與參考結果仍待 C9。
