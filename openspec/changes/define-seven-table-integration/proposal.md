# Proposal：定義七表資料整合契約

## 目的

將卷料、三站製程、材料追溯、品質時間序列、品質檢驗、產品規格與漂移真值建立成可重現、無標籤洩漏的模型資料來源，保留七份來源表並為後續 canonical model table 定義一致規則。

## 範圍

- 定義七表資料粒度、主鍵與版本欄位。
- 定義以材料 MD 區間對齊塗佈、熟化與壓合的規則。
- 定義五個模型目標的正式標籤來源與 synthetic ground truth 模式。
- 定義整卷檢驗、規格 pivot、重複檢驗、衝突與 availability。
- 定義禁止進入模型的衍生答案欄位。

## 不包含

- 不在本 Change 實作模型訓練或 C 儀表板正式 Adapter。
- 不改寫既有 C1～C3 Mock／SPC 歷史驗收。
- 不直接寫入 PLC、MES 或機台。

## 影響

- A：生成器需輸出可追溯的七表、schema metadata 及標籤來源。
- B：後續建立 canonical model table，按目標 availability 訓練。
- C：現有單 CSV 介面保持；正式七表整合留後續 Adapter／C9。

## 審查狀態

使用者已於 2026-11-02 授權依本提案更新本機規格；A／B／C 跨組正式介接仍待團隊確認。
