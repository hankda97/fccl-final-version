# Proposal

## Why

C1 的 Streamlit 基礎主畫面與 C2 的 CSV 資料載入已完成並通過 40 項測試。原 Change 同時包含 C3～C9，將功能階段與正式跨組整合綁在一起，無法分別驗收歸檔。本輪依使用者要求將本 Change 收斂為 C1＋C2，讓基礎交付可獨立審查；全部原需求由後續獨立 Changes 承接，未取消第一版快照／回放與原始團隊功能。

## What Changes

- 交付可啟動的單一主畫面、側欄、監控摘要與 Alarm 顯示區、四個功能 Tabs；未實作的分析／調參／回放保留明確占位或停用控制，不造假數值。
- 交付 C 專用可重現 fixtures（含獨立事前歷史資料）、CSV UTF-8／BOM 解析、顯式欄位／單位／時區映射、可追溯識別、穩定排序、用途輸入檢查及局部降級。
- 交付 Mock／上傳載入、批次／時間篩選、產品／環境顯示、資料預覽與問題結果；失敗匯入保留舊有效資料，成功更換才清除相依狀態。
- C1＋C2 八項已驗收任務保留；C3～C9 移至 [後續開發計畫](../../../../docs/CHANGE_ROADMAP.md)，並在修改前保存 [原完整規劃](../../../../docs/change-baselines/fccl-streamlit-dashboard-c1-c9/README.md)。
- 本次只調整管理文件，不修改 Python、不重做功能、不 Archive／同步主規格、不進入 C3 Apply。

## Capabilities

### New Capabilities

- `dashboard-workspace`: 基礎頁面、四 Tabs、業務狀態保留、來源／成熟度提示及未實作功能占位。
- `csv-ingestion`: C Mock 與 CSV 載入、來源映射、輸入驗證、識別／篩選、資料檢查及原子資料切換。

### Modified Capabilities

無。目前正式 specs 為空；本案將來 Archive 時只新增上述兩項的基礎能力。

## Impact

- 已有實作為 app.py、c_dashboard/state.py、ui/、data/、adapters 的不可用接點、tests／fixtures 與鎖定依賴；本輪不改動。
- 排除本 Change 交付：X-bar 計算、SPC Alarm、確定性預測、可操作 What-if／解鎖／建議、Heatmap、SHAP、動態回放與正式 A／B 整合。占位不代表這些功能已完成。
- [Roadmap](../../../../docs/CHANGE_ROADMAP.md) 保存 28 需求／47 情境／39 任務的完整追蹤；全案仍為 8／39，本案是 8／8。六個後續 Change 尚未建立，不將 C 內部格式強加 A／B。
- ADR-015 調整管理粒度；原 ADR 的功能決策與 TCP-001～004 狀態保留。Mock 成功不代表正式模型、真正 SHAP 或產線驗證完成。
