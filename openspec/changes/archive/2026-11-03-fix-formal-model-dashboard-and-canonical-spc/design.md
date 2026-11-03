# Design

## Context

目前 `render_overview` 的五張卡片實際混合四項 SPC 最新子組均值與一項模型外觀風險，並硬編碼「Mock 未校準」及「正式 Random Forest 模型尚未接入」。正式 Adapter 已存在且可回傳五目標結果，所以問題在呈現資料流而非缺少模型。

canonical loader 目前以每卷列序每五列直接產生 `subgroup_id`，但 `profile_for_dataset` 僅承認 hash 登錄的 C Mock；canonical 資料因此沒有合格 profile 或 baseline。來源 v2 `quality_timeseries.csv` 已保存 `dataset_split` 與 Synthetic `process_phase`，且資料生成驗證曾以五筆為子組容量假設，但 canonical manifest 尚未保存正式 SPC 取樣 sidecar／hash；canonical 內現有 `process_phase` 來自製程站的 observed 值 `production`，不能直接用來選 stable 歷史。

本設計延續既有 X-bar、固定歷史基準、hash 驗證與「證據不足即不可判定」政策。詳見本 Change 的 delta specs。

## Goals / Non-Goals

**Goals:**

- 建立單一、可測試的 overview view model，讓模型預測與實測 SPC 從資料結構到 UI 都保持分離。
- 讓正式、Mock、不可用三種 Adapter 的來源、版本、能力與文字一致，不依 UI 硬編碼推測。
- 為 `synthetic-ground-truth-v2` 建立透明、可重現、hash 驗證的 Synthetic X-bar 取樣與 baseline sidecar。
- 保持 baseline 與監控 cohort 時間隔離、樣本不重疊，且逐目標沿用既有穩定性拒絕機制。

**Non-Goals:**

- 不重訓或更換 Champion／Challenger，不改模型特徵、指標、閾值或 artifact 格式。
- 不把 Synthetic baseline 升格為工廠 SPC 標準，也不替真實資料推測取樣設計。
- 不為 `simulated-inspection-v2` 虛構連續品質平行試片；其證據不足時仍可保持 SPC 不可判定。
- 不新增 I-MR、預測良率、線上學習、PLC／MES 寫入或因果調參宣稱。

## Decisions

### D1：Overview 使用兩個明確的展示模型

建立「目前區段模型預測」與「實測 SPC 最新子組」兩個 presentation model。模型區直接讀取同一次 `PredictionResult`：四項連續目標顯示預測值與單位，外觀顯示預測類別及風險；SPC 區只讀取 `SpcResult` 的四個連續目標，顯示最新有效子組均值、狀態與 baseline 來源。任何一側不可從另一側補值。

來源 banner、caption 與 Alarm 由 `AdapterInfo`、逐目標 availability、SPC profile／baseline 動態產生。保留使用者明確選擇 Adapter 的流程，不因載入 canonical 自動改選來源。

替代方案是只修改現有五張 metric 的 caption；這仍會混合兩種統計語意，無法可靠處理部分目標不可用，因此不採用。

### D2：Reason code 在呈現邊界集中翻譯

新增集中式 SPC reason catalog，輸入完整原始 code（包含 `PREFIX:detail`），輸出繁體中文標題、必要細節與原始 code。`SpcResult`、baseline 與事件仍保存原始 code，不在計算層改成中文，避免破壞測試、去重、API 與稽核。

已知 code 使用固定翻譯；未知 code 顯示「未識別原因（RAW_CODE）」而非隱藏。overview、SPC Tab 與 Alarm 共用相同 formatter，避免同一原因在不同區塊出現不同說法。

替代方案是在各 Streamlit renderer 直接建立字典；這會產生重複與遺漏，故不採用。

### D3：新增 hash 驗證的 `spc_samples.csv` sidecar

canonical builder 對 `synthetic-ground-truth-v2` 另外輸出 `spc_samples.csv`，manifest 保存 sidecar hash 與 `spc_profile` 描述。sidecar 至少包含 canonical／自然樣本 ID、`sampling_event_id`、`subgroup_id`、`specimen_id`、卷／MD 範圍、原觀測時間、取樣事件時間、可得時間、`dataset_split`、Synthetic phase、baseline／monitor eligibility、產品／配方與版本。

合理子組採來源生成規則已使用的五個 Synthetic specimens：只在同卷、同 Synthetic phase、MD 連續、時間有序且 profile 條件容許範圍內建立非重疊子組。每組五個 constituent 仍保留原始 `aligned_sample_id`；SPC 投影以共同 `sampling_event_id` 與事件完成時間表達同次合理子組，不覆寫 canonical 的原始時間或材料區段欄位。跨卷、跨 phase、缺列或條件不符的尾組明確排除並記錄原因。

loader 只在 manifest、canonical 與 sidecar hash／版本全部相符時建立 canonical `SpcProfile` 和 SPC 專用 frame；刪除目前 canonical display 內按列序 `cumcount() // 5` 所產生的偽證據。一般上傳與 inspection profile 不繼承此 profile。

替代方案是沿用 display frame 的每五列分組；它沒有來源契約且排序變更會改組，違反既有 SPC 規格，因此不採用。另一方案是改用 I-MR，但本專案已決定保留 X-bar 並在無合理子組時顯示不適用，故不採用。

### D4：Baseline 使用固定的最早 25 組 `train + stable` cohort

`synthetic-ground-truth-v2` baseline 候選限定為 sidecar 中時間最早、完整且符合條件的 25 個 `dataset_split=train`、Synthetic phase=`stable` 子組；選取規則在 profile 版本中固定，不得根據品質值或是否觸發規則挑組。監控起點固定為第一個 validation cohort 事件時間，監控 frame 只含 validation／test 的 eligible 子組。這使歷史必然早於監控且自然樣本不重疊。

25 組符合既有 `minimum_history_groups=25`，也避免以全部長期資料作 Phase I 基準而把已知漂移混入。每個目標仍由 `build_baseline` 驗證完整性、R-bar、X-bar／R 穩定性；任何失敗都拒絕該目標 baseline，不移除異常點或改選下一段。初步唯讀檢查顯示目前 v2 最早 25 組對四項目標皆能通過現有檢查，但實作後仍須以正式 sidecar 重跑測試作為唯一驗證證據。

Synthetic phase 僅進入 SPC sidecar／驗證，不加入 `FEATURES`、正式預測或 What-if。`simulated-inspection-v2` 若沒有相同等級的平行試片證據，不套用 ground-truth baseline。

替代方案是用所有 train 列或監控資料即時計算界限；前者混入 drift，後者會造成 baseline 漂移與資料洩漏，均不採用。

### D5：Canonical profile、baseline 與快取以內容身分隔離

canonical profile identity 包含 dataset version、canonical hash、sidecar hash、SPC profile version、取樣規則、單位與 cohort policy。baseline cache key 再加入實際歷史 frame hash與穩定性規則版本；模型 profile 切換、資料重建或 sidecar 變動都會使舊 SPC 結果失效。C Mock 繼續使用既有 fixture profile／history，不共用 canonical baseline。

controller 對 canonical 使用 loader 已驗證的 SPC context、history frame 與 monitoring frame；一般 `selected_rows` 仍服務資料檢視與模型，不能被 baseline builder 回讀。篩選只縮小監控 frame，不改固定 baseline。

### D6：測試以來源隔離和失敗降級為主軸

新增 builder／loader 測試驗證 sidecar 可重現、hash、五 specimen、同卷／相位／MD／時間條件、train/history 與 validation-test/monitor 零重疊，以及 phase 不在模型特徵。SPC 測試驗證四目標 baseline、固定界限、篩選不重估、tamper／缺 sidecar／不穩定歷史的安全降級。

Streamlit 端到端測試分別覆蓋正式、Mock、不可用來源；斷言正式模式五項模型結果不含 Mock／尚未接入文字，SPC 區獨立呈現，中文狀態仍可查原始 code。既有 What-if、正式 SHAP、SPC、CSV 與全套回歸測試全部保留。

## Risks / Trade-offs

- [Synthetic 五件子組是示範取樣設計，不代表工廠抽樣] → UI、manifest 與 baseline source 固定標示「合成資料示範」，真實上傳不自動套用。
- [Sidecar 讓 canonical artifact 多一個契約檔案] → 納入 manifest hash、data dictionary、版本與重建測試；缺檔時只停用 SPC，不破壞正式模型或資料預覽。
- [25 組可能在未來資料版本失去穩定性] → 選取規則不依品質值，逐目標拒絕失敗 baseline；資料版本更新須重新驗證，不自動換窗。
- [validation／test 同時作模型評估與 SPC 示範監控，使用者可能混淆] → 兩者共用資料但用途與結果分區標示；SPC 不回寫模型評估，也不宣稱獨立的真實產線驗證。
- [中文翻譯可能落後新增 code] → 未知 code 以原始值安全顯示，並以測試要求 catalog 覆蓋目前已知 code。

## Migration Plan

1. 先新增 sidecar schema、builder 與驗證測試，重建兩個 canonical profile；只有 ground-truth profile 宣告可用 SPC evidence，inspection profile 保持誠實限制。
2. 更新 canonical loader／SPC source 與 controller，使舊 manifest 或缺 sidecar 資料安全降級；確認 C Mock 路徑不受影響。
3. 加入 reason catalog 與 overview 分區，移除硬編碼過時文字，再更新 Streamlit 測試。
4. 執行 targeted 測試、正式模型／What-if／SHAP 端到端與完整回歸；測試通過後才將 OpenSpec tasks 標完成。
5. 回退時可還原 UI／controller 與 canonical artifact；舊 canonical 缺 sidecar 時本來就會回到不可判定狀態，不會產生假界限。
