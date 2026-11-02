# Proposal

## Why

C1～C6 已交付快照分析，原始 C7 尚缺歷史 CSV 動態回放。完整 CSV 含未來品質結果，不能直接將目前的快照切片當作歷史當下可見資料；現有 loader 的 `AVAILABILITY_ASSUMED` 也不是正式可得時間證據。本 Change 建立可驗收的時間／可得性邊界，不改變 A／B 的正式契約。

## What Changes

- 以單一 Replay Cursor 推進可信可得時間的原子事件群，提供播放／暫停、單步、重新開始、倍率、模擬時間與進度。
- 為目前批號及事件時間篩選的資料建立版本化時間投影，分開製程、量測、結果可得時間與逐目標 availability；無可靠宣告時局部降級，不猜正式時間。
- 所有監控、預覽、SPC、AI、Heatmap／SHAP 共用同一可見性快照；品質尚未可得不得提前顯示。固定 What-if 與回放獨立，重新開始使已選情境明確失效。
- 保留固定歷史 SPC 基準、既有規則、四 Tabs、Mock／正式模型分離及 C9 整合邊界，不建七表 JOIN、不做正式模型訓練或 SHAP 計算。
- 不依賴未批准的三模式導航；記錄與其 WS-01／WS-02 Delta 的文字重疊，第二個 Change 實作／同步前須重新對齊，不能互相覆蓋情境。

## Capabilities

### New Capabilities

- `csv-replay`：歷史回放時間投影、單一游標、控制、可得性、防未來洩漏及生命週期。

### Modified Capabilities

- `dashboard-workspace`：啟用回放入口並保留跨 Tab 狀態及快照／回放邊界。
- `csv-ingestion`：載入成功與歷史可得性適用性分開，保留來源、欄位與時間映射證據。
- `quality-scenarios`：回放時固定已可見區段，重啟失效且不得自動復活。
- `spc-monitoring`：相同已可得實測切片使用既有固定基準及規則。
- `quality-visualization`：圖表來源識別納入游標／可得截止與版本，過期結果不得回寫。

## Impact

預計新增 `c_dashboard/replay/` 純服務及 C7 fixtures／測試，擴充既有 ReplayState、資料切片接點與 UI 控制；本次不修改 Python。正式事件／製程完成／量測／發布時間映射、模型歷史適用性及檢驗修訂歷史仍待 A／B／C9 確認。TCP-003／004／007 維持待討論。原始 Roadmap 24／39 不變；不撤銷 C1～C6 或 C8～C9，三模式 B／C 模擬不在範圍內。
