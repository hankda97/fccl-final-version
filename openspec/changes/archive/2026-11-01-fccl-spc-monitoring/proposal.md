# Proposal

## Why

C1＋C2 已完成資料載入，但 SPC Tab 與 Alarm 仍為占位。成員 C 需要以獨立歷史 Mock 與合理子組完成可測的快照 X-bar 監控，將實測異常同步到主畫面，並保持後續回放與正式整合的獨立交付邊界。

## What Changes

- 依同次獨立試片、子組識別及條件設定驗證四個連續目標：抗剝離、尺寸 MD／TD、耐熱；外觀 NG 保留實測資訊與不適用說明，不套 X-bar，也不新增 I-MR。
- 使用獨立、時間早於監控起點的歷史 Mock，逐目標檢查完整性／穩定性／產品與條件，建立固定 CL／UCL／LCL；不由篩選或新觀測重新校準。
- 偵測一點超界、六點嚴格上升／下降、九點同側，明確定義中斷、觸發及去重；同一實測事件同時顯示於 SPC Tab 與上方紅色 Alarm。
- SPC 圖呈現子組均值、原始量測趨勢及三條固定界限，區分產品規格；不足／無效資料顯示無法判定並保留 CSV 檢查。
- 保留側欄篩選及 Session State，以明確輸入切片與固定基準設計純計算接點；本案只測可見前綴契約，不實作 C7 播放控制。
- 以 MODIFIED delta 更新基礎規格中「尚未實作 SPC」的限制；不修改既有主 specs 或歸檔歷史。本次只 Propose。

## Capabilities

### New Capabilities

- `spc-monitoring`: 合理子組、固定歷史基準、四連續目標 X-bar、實測異常規則與可追溯結果。

### Modified Capabilities

- `dashboard-workspace`: WS-01～04 保留既有情境並擴充快照 SPC／同步 Alarm，其他未實作功能繼續占位。
- `csv-ingestion`: DATA-02／03 保留既有驗證與 Mock 隔離，允許具有效基準的目標進行 SPC，其他目標局部降級。

## Impact

- 預計新增 c_dashboard/spc/ 的純計算模組及 ui/spc_panel.py／spc_alarm.py；局部修改 layout／tabs／overview／state 與 C 資料組合接點。不改 A／B 程式，不訓練 RF，不實作模型 Alarm、What-if、Heatmap、SHAP 或回放。
- 沿用 pandas／numpy、Streamlit，優先用既有原生圖表能力；本案不為繪圖另建資料庫／API。預計新增 C 專用 SPC 設定與小型手算測試資料，既有 C2 fixtures bytes 保留。
- 來源為 ADR-005／006、C3 計畫與原 C1～C9 快照；原任務 3.1～3.4 分解為本案可驗收任務，逐項追溯在 design／tasks。回放一致性留 C7、真滑桿整合留 C4＋C5、正式來源／基準語意留 C9。
- TCP-001～003 仍待團隊討論，TCP-004 仍為既有團隊討論待補齊／跨組整合待確認；沒有新增跨組契約或圖種。C 的穩定性檢查與設定僅為 Mock 測試，不代表已驗證產線界限。
