# Tasks

## 1. Canonical SPC 證據與 artifact

- [x] 1.1 在 canonical dataset builder 定義並產生版本化 `spc_samples.csv`，只將同卷、同 Synthetic phase、MD 連續、時間有序且符合條件的五個非重疊 specimen 建為合理子組；以 builder 單元測試驗證 subgroup／specimen 唯一性、跨界排除與相同 seed 可重現（SPC-05，D3）。
- [x] 1.2 將 SPC profile、baseline／monitor cohort policy、sidecar hash 與欄位說明加入 manifest／data dictionary，重建 canonical profiles；以輸出 hash、manifest schema 與重建結果測試確認只有 `synthetic-ground-truth-v2` 宣告 SPC evidence，`simulated-inspection-v2` 不借用 ground-truth 證據（SPC-05，D3）。
- [x] 1.3 更新 canonical loader，使其驗證 canonical 與 sidecar 的 hash、版本、單位、樣本關係及 cohort，移除 display frame 的 `cumcount() // 5` 自動分組；以有效、缺檔、竄改、錯版及一般上傳測試確認模型／預覽可繼續且 SPC 安全降級（SPC-05，D3）。
- [x] 1.4 加入防洩漏測試，確認 Synthetic phase／baseline eligibility 只存在 SPC metadata／frame，不在 `FEATURES`、正式推論輸入或 What-if allowlist，並執行既有 dataset audit 測試（SPC-06，D4）。

## 2. Canonical SPC profile、baseline 與監控

- [x] 2.1 擴充 SPC source/context 以攜帶 loader 驗證過的 canonical profile、history frame 與 monitoring frame，同時維持 C Mock fixture 路徑及未知上傳隔離；以 source/controller 測試驗證三者不共用 profile 或 baseline（SPC-05～06，D5）。
- [x] 2.2 實作固定選取最早 25 個 `train + stable` eligible 子組、以第一個 validation 事件作 monitoring origin，且只將 validation／test eligible 子組送入監控；以測試驗證歷史早於監控、自然樣本零重疊、四目標通過時有固定界限及篩選不重估（SPC-06，D4～D5）。
- [x] 2.3 將 dataset／canonical／sidecar／profile／history／規則版本納入 SPC 與 baseline cache identity；以資料或 profile 變更測試驗證舊結果失效，同源重跑與切換 Tab 則維持相同 baseline／事件身分（SPC-06，D5）。
- [x] 2.4 增加歷史不足、零變異、不穩定、晚到、樣本重疊與 inspection profile 無證據測試，確認逐目標拒絕 baseline、不移除異常點、不改選窗口，且其他目標與資料／模型功能保持可用（SPC-06，D4）。

## 3. 狀態翻譯與監控摘要

- [x] 3.1 建立共用 SPC reason catalog／formatter，覆蓋目前已知 reason code 並保留 raw code／detail；以單元測試驗證 `MISSING_SAMPLING_EVIDENCE`、`BASELINE_UNAVAILABLE` 的繁體中文及未知 code 的安全 fallback（SPC-07，D2）。
- [x] 3.2 讓 overview、SPC Tab 與 Alarm 共用 formatter，顯示 profile／baseline 來源與「合成資料示範」限制；以 Streamlit 測試驗證有效狀態不殘留缺證據訊息、無效狀態同時可讀中文與原始 code（SPC-07，D2）。
- [x] 3.3 將 overview 拆成「目前區段模型預測」五目標區與「實測 SPC 最新子組」四目標區，直接分別使用 `PredictionResult` 與 `SpcResult`；以 UI 測試驗證任一來源不可替另一來源補值，部分目標失敗不阻擋其他目標（WS-05、Q-09，D1）。
- [x] 3.4 移除硬編碼 Mock／「正式模型尚未接入」文字，讓摘要、Alarm、What-if 與 SHAP 依同一 AdapterInfo／來源生命週期更新；以正式、Mock、不可用及切換來源測試驗證無殘留文字、無靜默降級與相依結果原子失效（WS-06、Q-10，D1）。

## 4. 整合驗證與追蹤

- [x] 4.1 執行 canonical builder／loader、SPC source／baseline／controller／UI 的 targeted pytest，記錄命令與逐套結果，並修正至全部通過。
- [x] 4.2 執行 Streamlit canonical 正式模型端到端測試，驗證五目標正式推論、獨立實測 SPC、What-if、正式 Tree SHAP、來源文字及無預測良率；另執行 Mock／不可用降級情境並保存結果。
- [x] 4.3 執行完整既有回歸測試與 `openspec validate fix-formal-model-dashboard-and-canonical-spc --strict`，確認 CSV、SPC、Alarm、What-if、SHAP、正式模型及其他模式無回歸，失敗項須記錄修復與重測證據。
- [x] 4.4 依 AGENTS.md 更新 `docs/DEVELOPMENT_LOG.md`、必要的 `docs/DECISION_LOG.md` 與既有 `docs/TEAM_CHANGE_PROPOSALS.md` 關聯，逐項標示 Synthetic 資料／模型來源、真實產線未驗證、測試結果、限制及尚未提交 Git；核對日誌與 tasks／specs／實際檔案一致。

## Workflow follow-up

- 使用者審查 Apply／驗證結果後，再另行執行 OpenSpec sync／archive；本 Change 不自動歸檔。
