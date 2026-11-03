# Design

## Context

目前 `compute_spc` 對每個規則觸發產生唯一 `SpcEvent`，這些事件正確保留同組多規則與重跑去重；問題發生在呈現層把整個監控範圍的事件於 Overview 和 SPC Tab 各逐筆輸出。Canonical Synthetic 全範圍可包含 1,600 個監控子組與數千事件，因此渲染成本、視覺噪音及導覽距離都不可接受。

資料來源 radio 只代表候選來源，成功按下載入後才會寫入工作區 dataset；目前空狀態未區分兩者。What-if 使用可見列建立區段；Heatmap 使用觀測切片；真正 SHAP 另要求正式 Adapter、Explanation Provider 與 manifest 相容。三者的前置條件不同，但 UI 只以停用元件或泛用訊息呈現。

## Goals / Non-Goals

**Goals:**

- 在不改動 SPC 原始判定、event ID 與稽核資料的前提下，將 Alarm 呈現控制在可操作的規模。
- 建立可測試的事件群生命週期、Overview 摘要與 SPC 歷史明細界線。
- 讓資料載入、模型與各分析能力的狀態及下一步在同一畫面一致可讀。
- 從既有 Heatmap 結果產生可追溯的方向摘要，並維持規格方向與因果限制。
- 讓真正 SHAP、Mock 無 SHAP、資料缺失與相容性失敗有不同且可恢復的狀態。

**Non-Goals:**

- 不調整 SPC baseline、管制常數、規則門檻或 Synthetic 漂移資料以降低事件數。
- 不刪除、抽樣或合併底層 `SpcEvent`，也不把事件群當成新的 SPC 判定。
- 不重訓或更換模型、不為公式 Mock 製造 SHAP、不新增預測良率。
- 不接入真實產線、PLC／MES 或背景通知服務。

## Decisions

### D1：原始事件與呈現事件群採雙層模型

`SpcResult.events` 維持唯一稽核來源；新增純投影的事件群結果，包含穩定 group ID、來源／scope、批次、目標、開始與最近子組、目前／已結束狀態、規則集合、原始事件 ID、事件數與最嚴重偏差。group ID 由群內不可變來源身分與首個觸發點衍生，重跑與切 Tab 必須一致。

事件依實際 target groups 順序處理，而非只對事件時間排序。同批次／目標的異常點在合理子組連續時屬同群；一個子組的多規則留在同群規則集合。下一個有效子組若沒有任何規則訊號即結束群；無效組、break、換批與條件／時間邊界也結束群。這避免用固定分鐘數猜測連續性。

替代方案是只顯示最新 N 筆原始事件；雖能縮短畫面，仍會讓持續漂移產生大量重複通知，無法說明一次異常期間，因此不採用。

### D2：Overview、SPC Tab 與技術明細分層

主要功能 tabs 移到 Overview 的有界摘要之前或緊接摘要標頭，確保不受事件量影響。Overview 顯示目標狀態、目前群、歷史群數及每目標最近群，不呼叫完整事件 renderer。SPC Tab 顯示事件群表、篩選與預設最近 10 群；選定群後才展開原始事件技術表。完整 hash、ID、界限與序列不進一般紅色訊息。

只有「最新有效子組仍觸發」的目前群使用紅色；已結束歷史群使用警示／一般表格。此顏色規則描述操作注意力，不改變 SPC 嚴重度或產品合格判定。

替代方案是將所有事件放進單一 expander；它仍一次建立數千個 UI 元件且缺少事件期間語意，因此不採用。

### D3：以能力矩陣集中產生就緒狀態

由目前 workspace、候選來源、已載入 dataset、篩選切片、區段選項、AdapterInfo 與 ExplanationInfo 投影一份只讀能力矩陣。至少包含 Data、What-if、Heatmap、SHAP Summary、SHAP Dependence，每項具 `status`、`reason`、`next_action`、source/version。元件停用與文字狀態皆消費同一矩陣，避免畫面一處稱可用、另一處稱未載入。

狀態優先序固定為：未載入資料 → 篩選為空 → 識別／特徵不足 → Adapter／Provider 不可用或不相容 → ready／computing／error。radio 選擇不得提升為 loaded；Mock 只能讓 Mock What-if ready，不能讓 SHAP ready。

替代方案是在每個 panel 各自增加判斷文字；較快但容易再次產生不一致來源生命週期，因此不採用。

### D4：Heatmap 摘要只使用已驗證格子

摘要由現有 Heatmap result 的 cell records 產生，不重新讀取全域資料或另算相關。逐目標排除不可計算格子後，分別取 `r > 0` 與 `r < 0` 中絕對值最大的格子；平手以固定特徵順序處理，確保可重現。摘要攜帶與格子一致的 r、n、特徵／目標單位及來源身分。

規格方向另由版本化目標 metadata 描述為 higher-is-better、lower-is-better 或 bounded/target-centered。摘要先陳述統計方向，再提供受限解讀：bounded 目標不標示有利／不利；外觀明示 1=NG；任何目標都保留非因果提示。

替代方案是直接依 r 正負給「改善／惡化」文字；對 MD／TD 區間目標會產生錯誤結論，因此禁止。

### D5：SHAP 可用性先於控制項與計算

SHAP 區先呈現能力狀態卡，再呈現選項與圖。未載入資料時指向資料載入；Canonical + Mock 時明示 Heatmap 可用但 Mock 無真正 SHAP，並指向模型來源；正式 Adapter／Provider 不相容時列出具體原因。只有 ready 才允許請求解釋，計算中及錯誤沿用既有結果失效規則。

Summary 與 Dependence 各自附用途、輸出尺度及單位說明。停用控制項仍可保留作能力預覽，但其容器不可降低整區文字對比。

### D6：驗收以極端事件量與來源生命週期為主

單元測試使用連續超界、重疊規則、正常恢復、換批及無效邊界驗證群組。Streamlit 測試以全 Canonical 2,913 類型事件量驗證 Overview 不產生等量 `st.error`、tabs 可直接尋得、SPC 明細有界且原始事件數守恆。另覆蓋未載入、Canonical+Mock、Canonical+正式、空篩選、正式模型失效、Heatmap 部分不可計算及 SHAP 錯誤隔離。

## Risks / Trade-offs

- [事件群規則可能掩蓋同一期間內多條規則] → 群摘要顯示規則集合與各規則計數，原始事件可完整展開及匯出。
- [只將目前群標紅可能被誤讀為歷史事件不重要] → 顯示歷史群總數、狀態與最近時間，SPC Tab 保留警示層級及篩選。
- [建立群組需遍歷目標子組與事件] → 使用一次線性投影並以 result/source identity 快取；不得為每個 UI 元件重算。
- [能力矩陣與現有 panel 判斷短期重疊] → Apply 時逐一將 panel 改為消費共同狀態，測試禁止相互矛盾文字。
- [Heatmap 文字摘要被當成調參建議] → 統一標示觀測相關、非因果，且不輸出參數調整量；調參仍只在 What-if。
- [tabs 移位可能改變既有 AppTest 元件順序] → 測試改用 key／label 與語意斷言，不依賴全域 metric 或 error 索引。

## Migration Plan

1. 先加入事件群純函式與守恆／穩定身分測試，不改現有渲染。
2. 加入能力矩陣與 Heatmap 摘要純投影，驗證現有計算結果不變。
3. 將 tabs、Overview、SPC、What-if 與 AI 圖表逐區切換到新投影；保留原始事件技術表作比對。
4. 執行定向 AppTest、正式模型／Mock／不可用端到端、極端事件量效能檢查及完整回歸。
5. 若 UI 驗收失敗，可回退呈現層變更；底層 SPC 事件、baseline、資料與模型 artifact 未遷移，無資料回復需求。
