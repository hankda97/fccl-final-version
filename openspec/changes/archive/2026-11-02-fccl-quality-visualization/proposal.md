# Proposal

## Why

C1～C5 已交付資料載入、SPC、What-if 與公式 Mock。本案最初針對 AI 圖表三個占位建立規劃；目前磁碟已含前輪部分 C6 實作（6／12），尚未完成整案驗收。本次僅依組長 main `058dfa35` 校正計畫與來源契約，暫停 Apply，不刪除部分實作或既有交付。此 Change 讓 C 可獨立交付觀測相關性呈現及模型解釋的顯示／驗證接點，正式 SHAP 計算仍由 C9 與 B 整合。

## What Changes

- 以目前載入且符合批號／時間篩選的實測 CSV，呈現製程／環境特徵對五個品質目標的相關性 Heatmap；提供欄位選擇、單位、有效配對數與不可計算原因，MD／TD 分列且不以預測補品質量測。
- 保留 SHAP Summary Plot 與 SHAP Dependence Plot，提供圖型、品質目標與特徵選擇，以及能力／模型／解釋資料不可用提示。
- 提供 C 內部、可選的解釋資料與圖形呈現接點，驗證來源、樣本／特徵對齊、目標、單位、分類標籤與輸出尺度。以明確標示的測試 payload／圖形獨立驗收，不使用公式 Mock 產生假 SHAP。
- 管理圖表的未載入、計算中、可用、過期、不可用與錯誤狀態；變更資料、選項或模型版本時不誤顯示舊圖為最新，切 Tab 保留既有工作狀態。
- 保留正式 B Random Forest／SHAP 轉接空間；C7 回放、C9 真正 SHAP 與正式資料／模型契約仍由後續 Change 驗收。
- 依組長 v2 區分區段模擬抽檢、完整合成真值與卷級檢驗；Heatmap 消費版本化來源投影、逐目標標籤 availability／原因，排除不相容粒度及衝突結果，合成資料獨立標示。缺標籤不等同模型不能預測或解釋；三種 availability 分開呈現。
- 在解釋接點與來源 key 補入模型 manifest 身分／版本、model type、schema／feature／label／spec／dataset versions、class=1 與輸出尺度相容性；用明確測試 manifest 獨立驗證，不強迫 B 採 C 結構。

## Capabilities

### New Capabilities

- `quality-visualization`: 實測 Heatmap、SHAP 顯示與能力提示、解釋呈現資料驗證，以及快照圖表的來源／計算狀態。

### Modified Capabilities

- `dashboard-workspace`: 將 AI 圖表占位提升為可操作 Heatmap 與 SHAP 呈現接點，保留四 Tabs、原監控功能、獨立圖表狀態及局部降級。

## Impact

預計新增 C 專用 visualization 純服務、可選 explanation port、AI 圖表 UI 與測試；局部延伸 WorkspaceState、資料切換重設與 UI 組合。現有 ModelAdapter 的預測介面與公式 Mock 不承擔 SHAP 計算，亦不強制 B 採用 C 的內部資料結構。圖形相依套件如有需要，於 Apply 時依既有 Python 環境鎖版；不引入模型訓練或 SHAP 計算依賴。原始 28 需求／47 情境／39 任務追蹤不變，對應 C6 原任務 6.1～6.4。

新版對照見 [同步報告](../../../docs/C_LEADER_ALIGNMENT.md)。七表 JOIN、MD 對齊、重測選取、規格 pivot、標籤及模型訓練仍由 A／B；C6 只定義來源接點、測試 fixture 與顯示，正式接入 C9。coverage、對齊錨點、重測規則及方法別名不一致不在 C 決定；品質值、NG 門檻及推薦策略維持跨組待確認。原三圖／五目標不變，不新增當下預測良率。12 tasks／28 情境保留；前輪勾選僅指原版局部驗證，新版差異仍須重新驗收，原完成進度不超過 20／39。


本輪 Apply 結案註記（2026-11-02）：前文 6／12／暫停是文件同步當輪狀態；續作授權後已依 D9 完成局部功能及新版差異驗收，最終 204 passed，原 C1～C5 回歸 126。詳見 [28 情境證據](../../../docs/C6_VISUALIZATION_ACCEPTANCE.md) 及 tasks；未 Archive／同步主 specs，不表示真正 SHAP／正式 A／B 整合完成。
