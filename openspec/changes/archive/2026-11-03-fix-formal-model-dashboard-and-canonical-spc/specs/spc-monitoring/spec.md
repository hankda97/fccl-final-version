# Spec Delta

## ADDED Requirements

### Requirement: SPC-05 Canonical Synthetic 取樣證據

canonical synthetic profile MUST 以版本化且可驗證 hash 的 metadata 明確聲明產品、配方、自然樣本、合理子組、樣本順序、條件容許範圍、時間與資料 cohort。系統不得只按目前列順序或固定每五列推測子組；此證據只代表合成示範取樣設計，不得標示為工廠實際取樣。

#### Scenario: Canonical profile 證據完整
- **WHEN** canonical manifest、資料內容與 SPC metadata 的 hash、版本、欄位及單位均相符，且每個子組的樣本識別唯一、同卷、MD 相鄰、時間有序並符合聲明條件
- **THEN** 系統使用 metadata 聲明的 subgroup 與 specimen 身分建立合成示範子組，並顯示 profile、取樣設計與 Synthetic 限制

#### Scenario: 只有 canonical 欄位而無 SPC metadata
- **WHEN** canonical projection 缺少 SPC metadata、自然樣本或合理子組證據
- **THEN** 資料與正式模型功能仍可使用，SPC 顯示「缺少可驗證的取樣證據」並保留 `MISSING_SAMPLING_EVIDENCE`，不得以列序自動湊組

#### Scenario: Metadata 與資料不一致
- **WHEN** metadata hash、版本、樣本識別、單位、時間順序或條件與 canonical 內容不一致
- **THEN** 系統拒絕套用該 SPC profile，顯示具體中文原因及原始 reason code，不沿用快取或其他資料來源的 profile

### Requirement: SPC-06 Canonical Synthetic 獨立穩定基準

canonical SPC 基準 SHALL 僅使用 profile 明確指定且位於監控起點之前的 `train + stable` 合成歷史 cohort；監控 cohort MUST 與歷史自然樣本不重疊，且不得包含 train 歷史列。每個目標仍須通過既有組數、變異、穩定性與適用性檢查，否則不得提供有效界限。

#### Scenario: 合成歷史基準通過檢查
- **WHEN** `train + stable` 歷史 cohort 在監控起點之前、樣本不重疊、子組完整且逐目標通過既有穩定性檢查
- **THEN** 系統建立固定 CL／UCL／LCL，顯示「合成資料示範基準」、歷史時間窗、組數、profile／baseline 版本及監控 cohort，不宣稱為正式產線界限

#### Scenario: 監控只使用保留 cohort
- **WHEN** canonical SPC 進入監控分析
- **THEN** 系統只分析 profile 聲明的 validation／test 或其他明確保留監控 cohort，不將建立基準的 train 樣本重複當成監控點

#### Scenario: 歷史不穩定或不足
- **WHEN** 任一目標的歷史子組不足、零變異、違反穩定性規則、晚於監控起點或與監控樣本重疊
- **THEN** 該目標顯示「無可用的穩定歷史基準」與具體原因，不刪除異常組、不從監控資料補點，也不影響其他通過檢查的目標

#### Scenario: Drift truth 與模型特徵隔離
- **WHEN** Synthetic phase／baseline eligibility 用於建立或驗證 SPC 歷史 cohort
- **THEN** 該欄位只作 SPC profile 與驗證 metadata，不進入正式模型特徵、What-if 可調參數或目前區段預測輸入

### Requirement: SPC-07 可讀狀態與可追溯 reason code

系統 SHALL 將已知 SPC 狀態及 reason code 轉成清楚的繁體中文使用者訊息，至少涵蓋 `MISSING_SAMPLING_EVIDENCE` 與 `BASELINE_UNAVAILABLE`；原始 code、目標、來源及版本 MUST 保留供除錯與稽核，未知 code 不得被隱藏或誤譯為正常。

#### Scenario: 缺少取樣證據與基準
- **WHEN** 目標同時包含 `MISSING_SAMPLING_EVIDENCE` 與 `BASELINE_UNAVAILABLE`
- **THEN** 畫面顯示「缺少可驗證的取樣證據」及「無可用的穩定歷史基準」等繁體中文狀態，並可查看兩個原始 code

#### Scenario: 已知與未知 reason code 混合
- **WHEN** 同一目標同時出現已知 code 與尚未建立翻譯的 code
- **THEN** 已知 code 顯示標準中文，未知 code 以安全的「未識別原因」加原始 code 呈現，不省略該異常或將目標標示正常

#### Scenario: 基準與 SPC 均有效
- **WHEN** 取樣證據、歷史基準及目前子組均通過檢查
- **THEN** 畫面顯示可判定狀態、最新子組及基準來源，不再顯示與該目標不相符的缺證據或缺基準訊息
