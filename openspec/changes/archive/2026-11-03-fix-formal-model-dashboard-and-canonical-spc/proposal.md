# Proposal

## Why

目前監控摘要把四項實測 SPC 子組均值與一項模型外觀風險放在同一列，且正式模型模式仍顯示 Mock／「尚未接入」文字，容易讓使用者誤判數值來源。canonical synthetic projection 也尚無可驗證的 SPC 取樣與獨立歷史基準契約，因此只能誠實回報 `MISSING_SAMPLING_EVIDENCE` 與 `BASELINE_UNAVAILABLE`；本變更要在不虛構產線證據的前提下補齊這個整合缺口。

## What Changes

- 將監控摘要拆成「目前區段正式／Mock 模型預測」與「實測 SPC 最新子組」兩個區塊：前者顯示五項模型輸出，後者僅顯示四項連續品質的實測 SPC 狀態與數值。
- 依實際選用 Adapter 動態顯示正式模型、C 公式 Mock 或不可用狀態；移除正式模型模式中的硬編碼 Mock 與「正式模型尚未接入」過時文字，且禁止靜默降級。
- 在呈現層將已知 SPC reason code 轉成可理解的繁體中文，同時保留原始 code、來源及版本供追溯；未知 code 仍須安全顯示，不得被隱藏。
- 為 canonical synthetic profile 增加版本化、hash 驗證的 SPC metadata／profile，明確聲明自然樣本、子組、條件、歷史 cohort、監控 cohort、監控起點及來源限制。
- canonical SPC 基準只可由監控起點之前、與監控樣本不重疊且通過既有穩定性檢查的合成歷史 cohort 建立；資料或證據不足時仍顯示不可判定，不可由目前監控資料補湊或只憑檔名宣稱穩定。
- 明確標示 canonical SPC 為「合成資料示範基準」，不宣稱為工廠／產品正式管制界限；不改變模型訓練內容、產品允收規格，也不新增預測良率。
- 實作階段須執行 Streamlit 正式模型端到端、SPC、What-if、SHAP 與既有回歸測試，並加入來源分離、中文狀態、baseline 不洩漏與失敗降級情境。

## Capabilities

### New Capabilities

無。

### Modified Capabilities

- `dashboard-workspace`: 監控摘要須以獨立區塊及動態來源文字呈現模型預測與實測 SPC，不得混用 Mock、正式模型或 SPC 語意。
- `quality-scenarios`: 正式模型、C 公式 Mock 與不可用 Adapter 的五目標監控輸出、來源、版本及降級行為須明確且一致。
- `spc-monitoring`: canonical synthetic profile 須具可驗證的取樣證據、獨立穩定歷史基準、監控 cohort 與繁體中文狀態呈現契約。

## Impact

- 受影響區域：`c_dashboard/ui/overview.py`、模型來源選擇與 Adapter 描述、SPC 狀態呈現、`c_dashboard/data/canonical.py`、`c_dashboard/spc/sources.py`、`c_dashboard/spc/controller.py`、canonical dataset builder／manifest 及相應測試。
- 既有正式模型 artifact 與五目標推論介面維持相容；canonical manifest／projection 將新增 SPC metadata 或 sidecar hash，舊資料缺少證據時必須安全降級，不可自動推測。
- 不新增外部服務或 PLC／MES 寫入；不把合成資料結果宣稱為真實產線效能、因果改善或正式品質標準。
