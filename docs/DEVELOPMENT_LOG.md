# 開發紀錄

本文件採追加式紀錄；更正時新增事件並引用原事件 ID，不覆寫歷史事件。

## 紀錄模板

- 事件 ID：`DEV-YYYYMMDD-NNN`
- 時間：`YYYY-MM-DD HH:mm:ss +08:00 (Asia/Taipei)`
- 標題／階段／分類：
- Change／task／需求及驗證對應：
- 目標：
- 已完成／未完成／待驗證／待整合：
- 檔案操作與實作細節：
- 測試、錯誤修復與限制：
- 資料來源／模型來源／真實製程驗證：
- Git Hash：
- 證據來源與待辦：

## DEV-20261102-001

- 時間：2026-11-02 00:57:58 +08:00 (Asia/Taipei)
- 標題：補齊連續耐熱度模擬目標
- 階段：Maintenance（資料契約補齊）
- 分類：C-DATA、C-INTEGRATION（資料與模型介面）
- Change／task／需求及驗證對應：未建立 OpenSpec Change 或 tasks；對應 `SKILL.md` 第 2 節 `heat_resistance_c` 目標與使用者選定的第二方案。
- 目標：保留 `SKILL.md` 原契約，在現有合成 CSV 增加最高通過溫度及規格，不取代既有熱收縮與固定 288 °C 焊錫漂浮測試。
- 已完成：新增可重跑腳本；為 13,074 筆品質時間序列生成製程真值與 0.5 °C 解析度量測代理值；為 87 筆五分鐘實驗室樣本與 25 筆每卷資格檢驗加入 `heat_resistance_c`；新增產品規格 1.0 的耐熱度規格；保存三份原始 CSV 備份。
- 未完成：尚未建立三製程對齊的單列訓練資料，也未訓練模型。
- 待驗證：正式產品的耐熱測試方法、中心值及 300–330 °C 模擬規格仍須製程／品質負責人確認。
- 待整合：後續模型訓練需把 `quality_timeseries.csv` 的 `heat_resistance_measured_c` 映射為資料契約目標，或以 `quality_inspection.csv` 的 `heat_resistance_c` 作檢驗標籤。
- 檔案操作：新增 `scripts/add_heat_resistance_target.py`、`docs/DEVELOPMENT_LOG.md`、`docs/DECISION_LOG.md`；修改 `raw data/quality_timeseries.csv`、`raw data/quality_inspection.csv`、`raw data/quality_specifications.csv`；新增 `raw data/backups/pre_heat_resistance_v1/` 備份。
- 實作細節：seed=42；潛在耐熱度由抗剝離、MD／TD 尺寸變化、MD／TD 熱收縮及外觀風險的明確公式產生，再加入依 `segment_id` 固定的量測噪音；每卷資格值採壓合區段第 10 百分位。
- 測試：通過。執行 `python scripts/add_heat_resistance_target.py`；確認 13,074 筆時間序列皆有值、量測範圍 292.5–312.0 °C、112 筆檢驗標籤有值、固定焊錫測試通過資料皆不低於 288 °C、腳本重跑 SHA-256 不變。
- 錯誤修復：不適用；本次未發生需修復的執行錯誤。
- 限制：公式及規格均為 `SYNTHETIC_DEMO_ONLY`；線上檢驗列不填入破壞性耐熱標籤；代理值不等同真實實驗室量測。
- 資料來源：Mock／合成示範資料。
- 模型來源：未接入。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前目錄不是 Git repository。
- 證據來源：`SKILL.md` 第 2 節、使用者於 2026-11-02 選定第二方案、上述腳本輸出與 CSV 驗證結果。
- 待辦：若進入模型階段，先建立 OpenSpec Change 與對齊資料集，並由製程／品質負責人確認耐熱測試定義及正式規格。

## DEV-20261102-002

- 時間：2026-11-02 01:02:44 +08:00 (Asia/Taipei)
- 標題：盤點合成資料良率、資料粒度與模型樣本充分性
- 階段：Explore
- 分類：C-DATA、C-MODEL、C-INTEGRATION（分析，未修改原始資料）
- Change／task／需求及驗證對應：未建立 OpenSpec Change 或 tasks；對應使用者對七表整併、合成良率及最低樣本數的問題；提出 `TCP-001`、`TCP-002` 待討論。
- 目標：確認目前各品質目標的實際通過率，辨識可否直接合併七表及是否足以訓練模型。
- 已完成：依檢驗口徑統計整卷、外觀、剝離、尺寸、熱收縮、耐熱、焊錫漂浮及阻燃通過率；確認外觀 NG 僅 2 筆且集中於同一卷；確認 13,074 筆區段來自 25 卷，不能當成獨立樣本。
- 未完成：尚未建立模型用衍生資料表，未調整模擬良率或增加卷數。
- 待驗證：正式產線預期良率、各缺陷機制比例及每項標籤的實際檢驗頻率。
- 待整合：需先決定模型資料列粒度、三站材料位置對齊方式、各目標訓練集與代表性驗證集的分布。
- 檔案操作：新增／更新本開發紀錄與 `docs/TEAM_CHANGE_PROPOSALS.md`；七份頂層 CSV 未修改。
- 實作細節：不適用；本次為資料盤點與設計建議。
- 測試：通過。以 Python `csv` 逐項統計非空標籤、通過／失敗數及失敗所屬卷號；結果包括整卷 21/25、外觀 9212/9214、耐熱 85/112、阻燃 22/25。
- 錯誤修復：不適用。
- 限制：目前「整體良率」沒有單一定義；不同檢驗粒度不可直接相乘或混為同一分母。
- 資料來源：Mock／合成示範資料。
- 模型來源：未接入。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前目錄不是 Git repository。
- 證據來源：七份頂層 CSV 的欄位與統計結果；scikit-learn GroupKFold、TimeSeriesSplit、Precision-Recall 與機率校準官方文件；ISA-95 官方資料模型說明。
- 待辦：待使用者決定是否建立模型用衍生表，以及是否依建議重新生成卷數與失敗比例。

## DEV-20261102-003

- 時間：2026-11-02 01:14:18 +08:00 (Asia/Taipei)
- 標題：比對 SKILL.md 與七表整合契約缺口
- 階段：Explore
- 分類：C-DATA、C-MODEL、C-INTEGRATION（規格分析）
- Change／task／需求及驗證對應：未建立 OpenSpec Change 或 tasks；細化 `TCP-001`，尚待使用者確認。
- 目標：逐項確認 MD 區間對齊、模型標籤、整卷檢驗、規格 pivot、重複檢驗、外觀旗標及標籤可用性是否已由 `SKILL.md` 完整定義。
- 已完成：確認 `SKILL.md` 已定義三站對齊後單列與五個目標，但缺少可直接實作的 join key、重疊演算法、標籤來源與優先序、卷級分配、規格關聯、重測衝突及逐目標缺值規則；提出逐項建議。
- 未完成：未修改 `SKILL.md`、未建立 OpenSpec、未修改 CSV 或實作整合程式。
- 待驗證：MD 覆蓋率門檻、各檢驗方法版本與外觀允收規則需由使用者／製程品質角色確認。
- 待整合：獲確認後建立 OpenSpec Change，更新技術契約，再建立衍生資料表。
- 檔案操作：更新 `docs/TEAM_CHANGE_PROPOSALS.md` 與本開發紀錄；其他檔案未修改。
- 實作細節：不適用；本次為契約差距分析。
- 測試：不適用；以 `rg -n` 人工核對 `SKILL.md` 第 2、4、8、9 節相關條文。
- 錯誤修復：不適用。
- 限制：所有解決方案仍為 Proposed，不代表已批准規格。
- 資料來源：Mock／合成示範資料結構。
- 模型來源：未接入。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前目錄不是 Git repository。
- 證據來源：`SKILL.md` 第 20、38–48、61–69、107–120 行及使用者本次問題。
- 待辦：等待使用者確認是否依建議修改 OpenSpec／`SKILL.md`。

## DEV-20261102-004

- 時間：2026-11-02 01:22:01 +08:00 (Asia/Taipei)
- 標題：同步 GitHub main 最新進度並保留本機工作
- 階段：Maintenance
- 分類：C-INTEGRATION（版本與文件同步）
- Change／task／需求及驗證對應：使用者要求從 `hankda97/fccl-final-version` 取得最新進度；未執行 OpenSpec task。
- 目標：將遠端 main 最新提交帶入目前工作區，不覆蓋本機 CSV、腳本、日誌及未提交提案。
- 已完成：初始化本機 Git repository、設定 `origin`、取得並追蹤 `origin/main`；同步三份遠端 C 組文件；以遠端 `TEAM_CHANGE_PROPOSALS.md` 為基底整合本機提案，沿用 TCP-003 並將衝突的本機 TCP-002 重編為 TCP-005；保留全部本機資料。
- 未完成：未 Commit、未 Push；遠端儲存庫未包含本機 raw data、scripts、DEVELOPMENT_LOG 或 DECISION_LOG。
- 待驗證：遠端文件引用的部分 OpenSpec／日誌路徑未包含在目前遠端提交中，後續需由團隊確認完整來源。
- 待整合：本機未提交內容需另行審查後再決定是否納入版本控制。
- 檔案操作：新增遠端追蹤與 `.git`；同步 `docs/C_BASE_ACCEPTANCE.md`、`docs/C_DASHBOARD_GUIDE.md`、`docs/C3_SPC_ACCEPTANCE.md`；整合 `docs/TEAM_CHANGE_PROPOSALS.md`；本機衝突文件備份於 `C:\Users\User\Desktop\fccl-final-version.local-before-f7f9d091`。
- 實作細節：遠端 main／HEAD 為 `f7f9d091d34f098e5f0f60f5a02db4fa359ebc82`；AGENTS.md 與 SKILL.md 內容相同，未覆寫其語意。
- 測試：通過。執行 `git fetch origin main`、設定 upstream，並以 `git status`、`git log` 及檔案 SHA 比對確認同步來源與本機保留狀態。
- 錯誤修復：處理 `TEAM_CHANGE_PROPOSALS.md` 的 TCP-001／002 ID 與遠端 TCP-001～004 衝突，避免覆蓋遠端歷史。
- 限制：工作目錄仍有未追蹤與未提交內容；同步完成不等於本機變更已推送。
- 資料來源：Mock／本機原始資料保留；遠端文件來自 GitHub main。
- 模型來源：未接入。
- 真實製程驗證：未執行。
- Git Hash：同步來源 `f7f9d091d34f098e5f0f60f5a02db4fa359ebc82`；本次本機整合尚未提交。
- 證據來源：`origin/main`、`git log -1`、`git status --short --branch` 與同步前後檔案比對。
- 待辦：審查本機未提交內容，決定納管與提交範圍。

## DEV-20261102-005

- 時間：2026-11-02 02:16:08 +08:00 (Asia/Taipei)
- 標題：完成七表整合與模型治理契約，重新生成並驗證合成資料 v2
- 階段：Propose、Apply、Verify
- 分類：C-DATA、C-MODEL、C-SPC、C-WHATIF、C-TEST、C-INTEGRATION（跨組契約與合成資料）
- Change／task／需求及驗證對應：`define-seven-table-integration` tasks 1.1～1.5 完成、2.1 待後續；`define-model-selection-governance` tasks 1.1～1.4 完成、2.1～2.2 待後續；`regenerate-training-data-v2` tasks 1.1～1.7 完成。對應 TCP-003～TCP-006、ADR-002～ADR-004。
- 目標：正式化七表整合的七項缺口、預先定義可擴充模型治理與離線改善循環，並建立約 80% 區段聯合良率、足量 NG 且與舊資料分離的 v2 合成七表。
- 已完成：更新 `AGENTS.md`、`SKILL.md`；建立三個 OpenSpec Change 的 proposal／delta spec／design／tasks；新增可重現生成與驗證腳本；在 `generated_data/v2/` 產生七份 CSV 與 metadata；更新 TEAM／DECISION／DEVELOPMENT 三類追蹤文件。
- 未完成：尚未實作 `build_model_dataset`、模型 adapter、模型訓練、SHAP、SPC UI 或 Streamlit 儀表板；尚未由 A／B／C 團隊確認正式跨組欄位與模擬規格。
- 待驗證：正式產品規格、測試方法、機台可操作範圍及真實製程因果效果仍需製程／品質負責人與真實資料驗證。
- 待整合：後續依 `define-seven-table-integration` 實作 canonical builder，再依 `define-model-selection-governance` 實作共同 adapter、基準、Random Forest Champion 及 HistGradientBoosting Challenger。
- 檔案操作：修改 `AGENTS.md`、`SKILL.md`、`docs/TEAM_CHANGE_PROPOSALS.md`、`docs/DECISION_LOG.md`；新增 `scripts/generate_fccl_v2.py`、`scripts/validate_fccl_v2.py`、三個 `openspec/changes/` 目錄及 `generated_data/v2/`。舊 `raw data/` 七份頂層 CSV 未刪除或覆寫。
- 實作細節：v2 使用 seed 42、200 卷、每卷 100 canonical 區段；三站各 20,000 列並採 MD 半開區間；完整合成真值 20,000 列，模擬檢驗 25,240 列（含 40 筆明確重測），分割為 train／validation／test 120／40／40 卷。五項品質以固定規格、製程特徵、卷效應、時間自相關及穩定／輕度／強度漂移產生，不隨機翻標籤或逐列修改規格；耐熱最高通過溫度只設 300 °C LSL，不把較高的通過溫度判成 NG。
- 測試：通過。`python scripts/validate_fccl_v2.py --check-reproducible` 驗證七表數量、唯一鍵／外鍵、三站 MD 完整無縫覆蓋、固定規格重算、availability、外觀旗標、重測 parent、spec 唯一鍵、metadata 列數及 hash；同 seed 暫存目錄重跑的七份 CSV hash 完全一致。`python -m py_compile scripts/generate_fccl_v2.py scripts/validate_fccl_v2.py` 通過；`git diff --check` 無內容錯誤，僅提示 Git 未來可能將 LF 轉 CRLF。
- 測試結果：區段聯合良率 79.45%；剝離／MD／TD／耐熱失敗率各 5.20%，外觀 NG 6.50%；穩定／輕度／強度漂移良率分別 96.95%／88.40%／52.31%；外觀 NG 1,300 筆、涵蓋 155 卷，test 有 409 筆；穩定資料可形成 1,300 個 n=5 子組。
- 錯誤修復：初版聯合良率 84.45% 且失敗過度集中於強漂移，調整共同與特定失敗機制後達成分層目標；驗證另發現 CSV 六位小數與記憶體浮點判定的界限風險，改為先量化寫入值再計算 pass flag。驗證器原以 pandas `Series.equals` 比較不同整數 dtype 造成假失敗，改用值陣列比較。
- 限制：`skill-creator` 的 `quick_validate.py` 因環境缺少 PyYAML 而未執行成功；已人工確認 YAML frontmatter 起訖、name、description，且完整讀取 Markdown。合成規格、範圍與約 80% 良率僅供測試，不是工廠標準或真實良率。OpenSpec 尚未 archive 或同步至正式 `openspec/specs/`。
- 資料來源：Mock／`synthetic_ground_truth` 與 `simulated_inspection`；舊 raw data 僅作歷史基準，七份原檔 SHA-256 逐一核對皆未變動。
- 模型來源：未接入；本次只定義模型治理契約。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD 僅為先前同步來源 `f7f9d091d34f098e5f0f60f5a02db4fa359ebc82`，不代表本次變更。
- 證據來源：上述兩支腳本輸出、`generated_data/v2/metadata.json`、三個 OpenSpec Change、原始資料 SHA-256 核對、使用者本次授權及 ADR-002～ADR-004。
- 待辦：由使用者與團隊審查本機 v0.2 草案及 TCP-003～TCP-006；確認後才進入 canonical builder 與模型實作，並另行決定 Commit／Push。
