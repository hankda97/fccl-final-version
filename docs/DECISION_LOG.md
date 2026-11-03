# 決策紀錄

本文件採追加式 ADR。決策變更時新增 ADR 並以 Superseded／Supersedes 連結，不改寫舊 ADR 原文。

## ADR 模板

- 決策 ID／狀態／日期與決策時間：
- 背景：
- 決策：
- 理由：
- 影響與限制：
- 取代關係／證據：

## ADR-001：保留連續最高通過溫度作為耐熱度目標

- 狀態：Accepted
- 日期與決策時間：2026-11-02；2026-11-02 00:57:58 +08:00 (Asia/Taipei)
- 背景：既有 CSV 只有固定 150 °C、30 分鐘熱收縮，以及固定 288 °C、10 秒焊錫漂浮通過旗標；兩者都不等同 `SKILL.md` 定義的連續 `heat_resistance_c` 最高通過溫度。
- 決策：依使用者選定的第二方案，維持 `SKILL.md` 原契約，新增連續耐熱度模擬目標；保留既有熱收縮、焊錫漂浮及 UL94 欄位。
- 理由：避免將不同測試概念改名混用，並讓未來 Random Forest 可建立連續耐熱度迴歸模型。
- 影響：`quality_timeseries.csv` 新增 `heat_resistance_process_c`、`heat_resistance_measured_c`；`quality_inspection.csv` 新增 `heat_resistance_c`、`heat_resistance_process_c`、`heat_resistance_spec_pass_flag`；`quality_specifications.csv` 新增 `heat_resistance_c` 規格。
- 限制：中心值 305 °C、LSL 300 °C、USL 330 °C 與生成公式皆為模擬假設；正式產品使用前必須確認測試方法及驗收值。
- 取代關係：不適用，首筆 ADR。
- 證據：使用者於 2026-11-02 明確選定第二方案；對應 `DEV-20261102-001`。

## ADR-002：七表保留來源粒度並建立逐目標 canonical model table

- 狀態：Accepted（本機工作草案；跨組正式採用待確認）
- 日期與決策時間：2026-11-02；2026-11-02 02:10:59 +08:00 (Asia/Taipei)
- 背景：七份來源表具有卷、站別區段、追溯、完整合成真值、抽檢、規格與漂移事件等不同粒度，直接平面合併會複製標籤、造成洩漏或破壞追溯。
- 決策：保留七表；以最終壓合 MD 半開區間為 canonical 錨點，依重疊長度對齊三站；正式模型逐目標使用有效抽檢標籤；整卷檢驗不複製到區段；規格依產品、版本、特性及有效期 pivot；重測依有效性與明確 parent 關係選取；外觀以 `appearance_ng_flag` 為真值；availability 採總旗標加逐目標旗標。
- 理由：同時保留來源可追溯性、避免一對多 JOIN 擴增與標籤洩漏，並讓不同抽檢頻率的目標各自取得最大有效樣本。
- 影響與限制：已同步 AGENTS／SKILL 與 `define-seven-table-integration` Change；canonical builder 尚未實作，跨組欄位名稱與正式規格仍待 A／B／C 確認。
- 取代關係／證據：不取代 ADR-001；使用者於本次要求依建議修改需要變動的 MD。

## ADR-003：採用分層 Champion／Challenger 模型治理

- 狀態：Accepted（本機工作草案；跨組正式採用待確認）
- 日期與決策時間：2026-11-02；2026-11-02 02:10:59 +08:00 (Asia/Taipei)
- 背景：使用者希望現在先定義 XGBoost、LightGBM、LSTM／GRU、Autoencoder 等模型的加入規則，以免後續重構資料與介面。
- 決策：常數／線性模型作基準，Random Forest 為初版 Champion，HistGradientBoosting 為必要 Challenger；XGBoost／LightGBM 採共同 adapter 可插拔；LSTM／GRU 僅在 horizon、序列數量及樹模型不足等門檻成立時加入；SPC 保留，PCA／Isolation Forest 作異常基線，Autoencoder 為條件式 Challenger；所有模型共用資料快照、切分、指標、manifest、升版及回退規則。
- 理由：預留擴充點但不過早增加依賴與維護負擔，並確保模型比較公平、可重現、可回退。
- 影響與限制：已同步 AGENTS／SKILL 與 `define-model-selection-governance` Change；尚未訓練任何模型，異常分數不得視為 NG 機率。
- 取代關係／證據：不適用；來源為使用者模型規劃問題及本次修改授權。

## ADR-004：v2 合成資料獨立輸出並以區段聯合良率約 80% 為目標

- 狀態：Accepted
- 日期與決策時間：2026-11-02；2026-11-02 02:10:59 +08:00 (Asia/Taipei)
- 背景：舊資料僅 25 卷且良率過高，外觀 NG 樣本極少，無法支援完整卷時間分割、分類評估、SPC 漂移學習及五目標聯合風險。
- 決策：v2 預設生成 200 卷、每卷約 100 個 canonical 區段、共約 20,000 區段，依時間分成 120／40／40 卷；五項品質的區段聯合良率須為 78%～82%，以穩定、輕度及強度漂移的合理製程機制產生；完整合成真值與模擬抽檢分離。輸出至 `generated_data/v2/`，保留舊 `raw data/` 作歷史比較且不作 v2 預設輸入。
- 理由：提供足量、跨卷且含多種失敗機制的 NG，同時避免刪除歷史資料或讓兩代資料混用。
- 影響與限制：80% 是合成區段聯合良率，不是整卷良率或真實產線承諾；模擬參數與規格仍需製程／品質負責人確認。
- 取代關係／證據：延伸 ADR-001 的連續耐熱目標；v2 將 300 °C 保留為最低允收值，因「最高通過溫度」是越高越佳的特性，330 °C 不再作拒收上限，僅可作生成／顯示範圍參考。此點取代 ADR-001 中把 330 °C 記為 USL 的模擬假設。對應 `regenerate-training-data-v2` Change 與使用者本次資料生成授權。

## ADR-005：正式 Synthetic artifact 與 C Mock 明確隔離且不自動降級

- 狀態：Accepted（本機實作；真實產線適用性未批准）
- 日期與決策時間：2026-11-02；2026-11-02 21:46:01 +08:00 (Asia/Taipei)
- 背景：`implement-quality-model-pipeline` 需把五目標模型與 SHAP 接入既有 Streamlit，同時避免 artifact 缺失、hash 不符或資料契約不相容時，以 Mock、舊結果或零值冒充正式推論。
- 決策：正式來源只載入專案可信根目錄中通過 registry、manifest、hash、套件版本及 source profile 相容性驗證的 Synthetic artifact；失敗按目標標示不可用，絕不自動 fallback 至 C 公式 Mock。Mock、正式 artifact、未接入是使用者明確選擇的三種來源，切換時清除推論、What-if 與 SHAP 快取。Tree SHAP 只使用 artifact 固定 train background，每請求最多 200 筆；外觀依 `classes_` 與 manifest 選標籤 1。
- 理由：確保模型來源、版本、資料契約及解釋輸出可追溯，避免安全降級被誤認為正式預測，並保留 C 既有 Mock／SPC／回放驗收行為。
- 影響與限制：已實作正式 Adapter、canonical loader、可信 loader、Streamlit 選擇、逐目標降級、What-if／Alarm 及 Tree SHAP。所有模型與規格仍是 Synthetic；What-if 是關聯推論，不是因果保證；不提供預測良率。Tree SHAP 加總採 0.005 輸出尺度數值容差。
- 取代關係／證據：不取代 ADR-002～004；落實 ADR-003 的共同 adapter／manifest／回退治理。證據為 `implement-quality-model-pipeline`、DEV-20261102-009、正式 Adapter／SHAP 測試及 Streamlit 端到端測試。

## ADR-006：Canonical Synthetic SPC 採可驗證 Sidecar 與隔離歷史基準

- 狀態：Proposed（待使用者審查及 Apply 驗證）
- 日期與決策時間：2026-11-02；2026-11-02 23:22:40 +08:00 (Asia/Taipei)
- 背景：canonical projection 現有 display loader 依列序每五列建立 subgroup，但 SPC source 沒有相應取樣 profile 或獨立 baseline，因此畫面正確回報缺少取樣證據與基準；若只隱藏 code 或直接套用 C Mock 基準，會製造不可追溯的管制界限。
- 決策：提議由 canonical builder 對 `synthetic-ground-truth-v2` 產生 hash 驗證的 `spc_samples.csv`，明確記錄五件 Synthetic 合理子組、自然樣本、條件、時間與 cohort；固定使用時間最早 25 個 `train + stable` eligible 子組建立 baseline，validation／test 才作監控。每個目標仍須通過既有穩定性檢查，失敗不得刪點、換窗或從監控補值。Synthetic phase 只供 SPC metadata，不進模型特徵或 What-if。
- 理由：保留 X-bar 與既有安全降級政策，同時讓合成示範的取樣假設、歷史／監控隔離及版本身分可稽核；避免依目前排序湊組、借用 Mock history 或用監控值重估界限。
- 影響與限制：若 Apply，canonical artifact、manifest／data dictionary、loader、SPC source／controller、UI 與測試都需更新；`simulated-inspection-v2` 無平行試片證據時維持不可判定。此 baseline 只供 Synthetic 示範，不代表工廠 SPC 標準；目前尚未實作或通過正式整合測試。
- 取代關係／證據：不取代 ADR-002～005；延伸 ADR-002 的 canonical 可追溯性與 ADR-005 的來源隔離。證據為 `fix-formal-model-dashboard-and-canonical-spc` proposal／design／specs、DEV-20261102-011 及 OpenSpec strict validation。

## ADR-007：接受 Canonical Synthetic SPC Sidecar 與隔離歷史基準的本機實作

- 狀態：Accepted（本機 Synthetic 實作；真實產線適用性未批准）
- 日期與決策時間：2026-11-03；2026-11-03 00:10:52 +08:00 (Asia/Taipei)
- 背景：ADR-006 所提 sidecar、固定歷史窗口與 UI 來源分流已依使用者 `$openspec-apply-change fix-formal-model-dashboard-and-canonical-spc` 指示完成實作及驗證，需要將 Proposed 與已驗證的本機決策分開保留。
- 決策：`synthetic-ground-truth-v2` 使用 hash 驗證、版本化的 `spc_samples.csv`；合理子組為同卷、同 phase、MD 連續、時間有序且條件一致的五件非重疊 Synthetic specimen。baseline 固定採最早 25 個 `train + stable` eligible 子組，validation／test 才可作 monitoring；逐目標穩定性失敗時不刪點、不換窗、不由監控補值。`simulated-inspection-v2` 不借用此 evidence。五項模型預測與四項實測 SPC 分區且依來源生命週期顯示。
- 理由：讓 Synthetic SPC 的取樣假設、自然樣本、歷史／監控隔離與 cache identity 可稽核，同時維持正式模型、Mock、不可用及無證據來源之間的安全隔離。
- 影響與限制：本決策只接受本機 Synthetic 示範契約，不核准實際工廠 n=5 取樣、25 組 baseline 或管制界限。未重訓模型、不新增預測良率；What-if 不是因果建議。真實工廠 profile、量測系統及跨組採用仍需另行批准。
- 取代關係／證據：取代 ADR-006 的 Proposed 狀態，保留 ADR-006 原文作歷史；不取代 ADR-002～005。證據為 DEV-20261103-001、`fix-formal-model-dashboard-and-canonical-spc` tasks 1.1～4.4、67 項定向測試、24 項端到端測試、359 項完整回歸及 OpenSpec strict validation。

## ADR-008：SPC 原始事件與事件群呈現採雙層模型

- 狀態：Accepted（本機 Synthetic／Mock 範圍；跨組與真實製程仍待確認）
- 日期與決策時間：2026-11-03；2026-11-03 00:51:27 +08:00 (Asia/Taipei)
- 背景：Canonical Synthetic 全範圍可產生數千筆有效 SPC 規則事件；逐筆於 Overview 與 SPC Tab 展開會造成 alarm fatigue、重複呈現並阻礙 What-if／AI 圖表操作，但直接刪除事件或放寬規則會破壞稽核與 SPC 語意。
- 決策：保留 `SpcResult.events` 為完整稽核來源，另依批次、目標與合理子組連續性建立穩定事件群投影。Overview 只呈現有界目前／歷史摘要；完整群與原始事件只在 SPC Tab 以篩選、有限預設筆數及展開技術資料呈現。正常有效組、無效／break、換批與條件邊界結束事件群。
- 理由：同時維持 SPC 判定完整性、重跑可追溯性與可操作 UI，避免以隱藏、抽樣或修改資料假裝事件減少。
- 影響與限制：已新增事件群投影、共同分析就緒狀態及 UI／測試調整；不改 baseline、規則、原始事件、模型或 Synthetic 資料。事件群屬呈現層，不是新的品質判定或合格結論。Heatmap 方向是觀測相關，What-if 不是因果控制，SHAP 僅解釋相容模型。
- 取代關係／證據：不取代 ADR-007 或既有 SPC 決策；延伸其可追溯性。Accepted 時間為 2026-11-03 01:41:00 +08:00。證據為 DEV-20261103-003、`improve-dashboard-alarm-and-analysis-usability` tasks 1.1～6.3、Canonical 2,913 原始事件／309 事件群守恆驗證、370 項完整回歸與 OpenSpec strict validation。

## ADR-009：以單一 Mode B 測試線控制台及 Gate 0 原型先行

- 狀態：Accepted（架構與規劃方向；實作仍待 Apply／驗收）
- 日期與決策時間：2026-11-03；2026-11-03 06:39:34 +08:00 (Asia/Taipei)
- 背景：既有 A／B／C 模式、快照分析與回放無法直接滿足連續測試線調參、材料延遲、製程 SPC 及簡潔控制台需求；使用者在 Explore 中逐項確認只保留 Mode B 產品面，並要求先看到可操作面板。
- 決策：一般導覽改為單一 Mode B 測試線控制台，舊 A 能力只作內部重用、C 隱藏；以 Gate 0 靜態 Streamlit fixture 原型先驗收，取得明確確認後才依 Gate 1 契約、Gate 2 Synthetic v3／四目標模型、Gate 3 模擬器／製程 SPC、Gate 4 正式整合推進。初版只支援 `FCCL-DEMO-001`／`SIM-RECIPE-3.0`，不新增外觀模型、預測良率或一般 SHAP 入口。
- 理由：先鎖定資訊架構可降低後端完成後重做版面的成本；單一入口可避免來源、session state 與成熟度混淆；Gate 分離讓資料、模型、模擬與 UI 各自具驗收證據。
- 影響與限制：此決策接受規劃方向，不代表 Gate 0 或任何後端已完成。Synthetic 配方、X-bar／R、I-MR／EWMA、Run 儲存及模型結果只供本機模擬，不是工廠標準或真實設備控制。AGENTS.md／SKILL.md 僅在 Gate 1 Apply 時依正式 specs 更新。
- 取代關係／證據：取代 MW-01 三模式使用者導航與 WS-01 模式 A 主畫面作為未來正式產品面的方向，但保留舊程式／artifact 供內部重用與回退；不取代 ADR-005、ADR-007、ADR-008 的來源、SPC 及事件群安全決策。證據為 DEV-20261103-005、`build-testline-simulation-control-room` proposal／design／specs／tasks 及 strict validation。
