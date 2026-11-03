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

## DEV-20261102-006

- 時間：2026-11-02 02:29:55 +08:00 (Asia/Taipei)
- 標題：完成 SKILL 自動驗證並推送 v2 契約與資料至 GitHub main
- 階段：Verify、Maintenance
- 分類：C-TEST、C-INTEGRATION（技能驗證、版本控制與交付）
- Change／task／需求及驗證對應：延續 `define-seven-table-integration`、`define-model-selection-governance`、`regenerate-training-data-v2`；對應 DEV-20261102-005 的驗證限制及使用者本次 Push 授權。
- 目標：使用專案 `.venv` 中的 PyYAML 完成 `SKILL.md` 自動驗證，排除本機環境與快取，並將已驗證內容推送至指定 GitHub repository。
- 已完成：確認遠端 `main` 與本機基準無 ahead／behind；新增 `.gitignore` 排除 `.venv/`、`__pycache__/`、工具快取與本機重複備份；新增 `.gitattributes` 固定 CSV／JSON／Python／Markdown 為 LF，避免跨平台換行破壞 metadata SHA-256；建立內容提交並推送至 `origin/main`。
- 未完成：未建立 `requirements.txt`／`requirements-dev.txt`，未推送 `.venv` 或 `raw data/backups/`；未進行模型與 UI 實作。
- 待驗證：其他成員首次 clone 後仍應依專案後續依賴檔建立自己的虛擬環境；目前 PyYAML 版本尚未納入正式 dependency lock。
- 待整合：團隊後續決定依賴管理方式時，將 PyYAML 與測試工具加入開發依賴並鎖版。
- 檔案操作：新增 `.gitignore`、`.gitattributes`；本事件前一內容提交涵蓋 AGENTS、SKILL、OpenSpec、三份追蹤文件、七份舊 raw CSV、七份 v2 CSV、metadata 與三支腳本。
- 實作細節：`.venv` 與 Python bytecode 保留本機但由 Git 忽略；`raw data/backups/` 保留本機、不刪除且不推送，頂層七份歷史 raw CSV 已納管。
- 測試：通過。以 `$env:PYTHONUTF8='1'` 搭配 `.venv\Scripts\python.exe` 執行 skill-creator `quick_validate.py`，結果為 `Skill is valid!`；`git diff --cached --check` 通過；`git fetch` 顯示提交前本機與遠端為 0／0；`git push origin main` 成功。
- 錯誤修復：PyYAML 缺少問題已由使用者安裝至 `.venv`；初次驗證因 Windows CP950 無法解碼 UTF-8 中文而失敗，改用 Python UTF-8 mode 後通過。這取代 DEV-20261102-005 中「只能人工檢查」的暫時限制。
- 限制：本次未建立完整 Python 依賴清單；GitHub 接受推送只證明版本交付成功，不等於跨組契約已正式批准。
- 資料來源：Mock／合成七表 v2；歷史 raw 七表。
- 模型來源：未接入。
- 真實製程驗證：未執行。
- Git Hash：內容提交 `8d3483eb6232e194fa30c87f893637a2fef483d1`，已推送至 `origin/main`。
- 證據來源：skill-creator 驗證輸出、`git status`、`git fetch`、`git commit`、`git push` 與 GitHub remote `https://github.com/hankda97/fccl-final-version.git`。
- 待辦：提交並推送本筆追加式日誌；後續由團隊審查 TCP-003～TCP-006 及是否建立正式依賴檔。

## DEV-20261102-007

- 時間：2026-11-02 20:04:54 +08:00 (Asia/Taipei)
- 標題：同步 GitHub main 的 C 組儀表板完整交付
- 階段：Maintenance
- 分類：C-INTEGRATION（版本同步）
- Change／task／需求及驗證對應：使用者要求取得 `hankda97/fccl-final-version` 最新版本；同步遠端提交 `df510531471d680662899ab21b613d3b33de350a`。
- 目標：將指定 GitHub `main` 最新內容安全同步至目前工作目錄，不改寫既有歷史或本機忽略檔案。
- 已完成：執行 fetch 與 `git pull --ff-only origin main`，由 `058dfa35c9d773acfcf949a401fc018106bd296f` fast-forward 至 `df510531471d680662899ab21b613d3b33de350a`；新增 Streamlit app、`c_dashboard/` 模組、C 組測試、依賴檔、OpenSpec 正式 specs 與 archive 文件。
- 未完成：未執行新加入的完整 C 組測試；未 Commit 或 Push 本筆本機日誌。
- 待驗證：新儀表板與目前 v2 七表的正式介接仍需依各 Change 與測試驗證；本次只確認 Git 同步成功。
- 待整合：後續工作前需閱讀新加入的正式 OpenSpec、交付指南及相關測試，再判斷與本機七表契約的整合範圍。
- 檔案操作：Git fast-forward 新增 178 個遠端檔案、13,730 行；本機 `.venv/`、`raw data/backups/` 及其他忽略內容未受影響；另追加本開發紀錄。
- 實作細節：同步前 `main...origin/main` 為 0／1；同步後本機與 `origin/main` 指向相同提交，無 merge commit、無衝突、無強制覆蓋。
- 測試：Git 同步檢查通過；`git pull --ff-only` 成功，HEAD 為 `df510531471d680662899ab21b613d3b33de350a`，同步完成時 `main...origin/main` 無 ahead／behind。應用測試未執行。
- 錯誤修復：不適用，未發生衝突或同步錯誤。
- 限制：只驗證版本狀態，未宣稱新增的 178 個檔案已在目前環境通過功能測試。
- 資料來源：遠端 GitHub main；既有 Mock／合成資料保留。
- 模型來源：新遠端內容包含 Mock Adapter；正式模型接入狀態待依文件確認。
- 真實製程驗證：未執行。
- Git Hash：同步來源 `df510531471d680662899ab21b613d3b33de350a`；本筆追加日誌尚未提交。
- 證據來源：`git fetch origin main`、`git rev-list --left-right --count`、`git pull --ff-only origin main`、`git rev-parse HEAD` 與 `git status --short --branch`。
- 待辦：依後續授權決定是否執行 C 組測試，以及是否提交／推送本筆日誌。

## DEV-20261102-008

- 時間：2026-11-02 20:27:44 +08:00 (Asia/Taipei)
- 標題：建立 canonical dataset、模型訓練與 Streamlit 接入的 OpenSpec 提案
- 階段：Propose
- 分類：C-DATA、C-MODEL、C-INTEGRATION（端到端模型管線規劃）
- Change／task／需求及驗證對應：新增 `implement-quality-model-pipeline`；建立 proposal、`quality-model-training` 新能力，以及對 `csv-ingestion`、`quality-scenarios`、`quality-visualization` 的 delta specs、design 與 tasks。延續 `define-seven-table-integration`、`define-model-selection-governance` 的既有契約，並關聯既有 TCP-006，未重複新增團隊提案。
- 目標：先建立可重現且防止資料洩漏的 canonical model dataset，再訓練五個目標專屬模型，最後以正式 adapter 與 SHAP 接入既有 Streamlit 儀表板。
- 已完成：建立完整 OpenSpec 規劃 artifacts；定義三道交付閘門（Dataset、Training、Integration）、兩種不可混用的標籤 profile、整卷時間隔離切分、基準模型／Random Forest Champion／HistGradientBoosting Challenger、可信 artifact manifest、rollback 與 Streamlit 降級行為。
- 未完成：未執行 canonical builder、模型訓練、模型序列化、SHAP 計算或 Streamlit 程式修改；未進入 Apply、Verify、Sync 或 Archive。
- 待驗證：Apply 後須以 v2 metadata、資料集 manifest、模型 metrics、adapter contract tests、SHAP 測試及 Streamlit smoke tests 逐項驗證；真實工廠資料的泛化能力仍未知。
- 待整合：Apply 時須同步處理 v2 metadata 的 `quality_inspection` coverage 0.98 與舊 `define-seven-table-integration/design.md` 所載 0.99 的契約差異；本提案以實際 v2 metadata 的 0.98 為該資料版本依據。
- 檔案操作：新增 `openspec/changes/implement-quality-model-pipeline/.openspec.yaml`、`proposal.md`、`design.md`、`tasks.md`，以及四份 delta spec；追加本開發紀錄。未修改 Python、CSV、正式 `openspec/specs/` 或既有模型／儀表板程式。
- 實作細節：canonical projection 由資料層唯一建立，C 組不得自行重做七表 JOIN；`synthetic-ground-truth-v2` 用於主要管線與 UI 驗證，`simulated-inspection-v2` 用於稀疏標籤與重測流程驗證；五個目標分開訓練與評估。XGBoost 僅保留可插拔擴充點，本次不納入 LightGBM、LSTM／GRU、Autoencoder、即時預測良率、PLC／MES 寫入或線上學習。
- 測試：通過。`openspec status --change implement-quality-model-pipeline` 顯示 4/4 artifacts complete；`openspec validate implement-quality-model-pipeline --strict` 回報 Change valid；`git diff --check` 通過。
- 錯誤修復：不適用；OpenSpec 嚴格驗證未發現格式或需求結構錯誤。
- 限制：此紀錄只表示提案文件已建立並通過結構驗證，不代表需求已由使用者批准，也不代表資料集、模型或 Streamlit 已完成。模擬資料不可推定為真實製程效能。
- 資料來源：Mock／`generated_data/v2`；規劃使用 `synthetic_ground_truth` 與 `simulated_inspection` 兩種 profile，尚未產生 canonical projection。
- 模型來源：未接入；目前仍為 Mock Adapter，正式模型尚未訓練。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次提案與日誌變更。
- 證據來源：`openspec context/list/status/instructions/validate` 輸出、既有 OpenSpec specs／changes、`generated_data/v2/metadata.json`、C dashboard adapter/schema/loader 程式碼與使用者本次 `$openspec-propose` 指示。
- 待辦：由使用者審查 `implement-quality-model-pipeline`；確認後以 `$openspec-apply-change implement-quality-model-pipeline` 進入實作。是否 Commit／Push 仍待使用者另行授權。

## DEV-20261102-009

- 時間：2026-11-02 21:46:01 +08:00 (Asia/Taipei)
- 標題：完成 canonical dataset、五目標模型、正式 Streamlit Adapter 與 Tree SHAP
- 階段：Apply、Verify
- 分類：C-DATA、C-MODEL、C-WHATIF、C-ALARM、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：`implement-quality-model-pipeline` tasks 1.1～6.3 已完成；6.4 於本事件與 ADR-005、TCP-003～006 補充同步後完成。對應四份 delta specs、ADR-002／003／005 及 TCP-003～006。
- 目標：依使用者授權，從唯讀 v2 七表建立兩種 canonical profile，訓練五個目標專屬模型，最後以可信 artifact、正式 Adapter 與 SHAP 接入既有 Streamlit，不影響 C Mock、SPC、回放及三工作模式。
- 已完成：建立七表驗證、MD 半開區間重疊對齊、逐目標 projection、lineage、排除摘要、120／40／40 完整卷時間切分及 leakage audit；分別產生 `synthetic-ground-truth-v2` 與 `simulated-inspection-v2` dataset；訓練 mean／linear 或 prevalence／Logistic 基準、Random Forest Champion、HistGradientBoosting Challenger；輸出 registry、bundle、metrics、manifest、背景資料及 hash；完成可信 loader、正式 Adapter、目前監控、What-if、Alarm、Tree SHAP Summary／Dependence 與 Streamlit 來源切換。
- 未完成：尚未以真實工廠資料重訓、驗證因果調參效果或建立 PLC／MES 寫入；XGBoost／LightGBM、LSTM／GRU、Autoencoder 仍依既有治理門檻保留為後續 Challenger，未在本 Change 實作；尚未 Sync／Archive 本 Change。
- 待驗證：真實產品規格、正式測試方法、機台安全範圍、資料漂移後的再訓練與 Champion 升版，均需製程／品質負責人及真實資料驗證。
- 待整合：團隊審查本次 Synthetic 模型報告與跨組契約後，再決定是否同步正式 specs、Archive、Commit 或 Push；本次未獲 Git 提交／推送授權。
- 檔案操作與實作細節：新增 `fccl_ml/`、`generated_data/model_dataset_v2/`、`artifacts/synthetic_v2/`、正式 Adapter／canonical loader／Tree SHAP Provider、ML 測試、`requirements-ml*.in/.txt`、`docs/ML_PIPELINE_GUIDE.md` 及本 Change；更新 Streamlit sidebar、layout、狀態、圖表、What-if、來源投影、OpenSpec task 與 0.98 coverage 契約。依賴使用 Python 3.12、NumPy 1.26.4、pandas 2.2.1、scikit-learn 1.5.2、joblib 1.4.2、SHAP 0.46.0、Streamlit 1.66.1、PyArrow 18.1.0；PyArrow 18.1.0 用於避免 NumPy 1.26 ABI 衝突。
- 端到端證據：`python -m fccl_ml.cli build --profile synthetic-ground-truth-v2` 耗時 25.919 秒，dataset version `67a0a2286db89c2d`，五個 projection 各 20,000 列；`python -m fccl_ml.cli train --profile synthetic-ground-truth-v2` 耗時 132.231 秒，model version `model-a94855f897dfbfae`。`generated_data/v2` 樹狀 SHA-256 前後同為 `791b96b83ea4c884a71c97a1ce442e9aa43c59b28fa5f457ebf89d1ee99f3554`；dataset manifest SHA-256 為 `e1c9032a18b3119218779b45b606d9e0c6acae81e1e2c1db6ca7257020a288f6`；registry SHA-256 為 `bd3eaa9dd5eee663a44126f07500327494d386ff8321016ccced269d70b8d79c`。
- 模型測試指標：Synthetic RF test——抗剝離 MAE 0.10059、R² 0.42742；MD MAE 0.06206、R² -0.00496；TD MAE 0.06194、R² -0.02849；耐熱 MAE 10.06101 °C、R² 0.39089；外觀 PR-AUC 0.26451、precision 0.24715、recall 0.53056、F1 0.33722、Brier 0.08620。這些數值只描述合成 test split；MD／TD 與分類效能不足以宣稱產線可用，且不觸發自動 Champion 升版。
- 測試、錯誤修復與限制：全套測試第一次為 343 passed／3 failed，修正 UI 相容文字與 Windows fixture LF；第二次為 345 passed／1 failed，唯一失敗是瀏覽器在資料載入 rerun 完成前展開設定造成的 race，加入明確可見性等待後兩個 Chrome 測試 2/2 通過。新增／受影響異常情境 12/12 通過，正式 Streamlit canonical → inference → What-if → SHAP 端到端 1/1 通過，正式 SHAP／既有 envelope 31/31 通過。OpenSpec strict validation 通過。Tree SHAP 200 筆深樹模型最大觀察浮點加總差約 0.00221，因此使用 0.005 輸出尺度容差，超過仍拒絕顯示。SHAP 0.46 會產生第三方 NumPy deprecation warnings，不影響結果。
- 資料來源：Mock、`synthetic_ground_truth`、`simulated_inspection`；`generated_data/v2` 唯讀核對未變。
- 模型來源：Synthetic 正式 artifact（非產線）；C 公式 Mock 保持隔離且不作自動 fallback。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次變更。
- 證據來源與待辦：上述 CLI／pytest／Playwright／OpenSpec 輸出、dataset／artifact manifests、`MODEL_REPORT.md`、`docs/evidence/`、ADR-005 與本 Change。待使用者審查後再決定 Sync／Archive 與 Git 操作。

## DEV-20261102-010

- 時間：2026-11-02 22:26:40 +08:00 (Asia/Taipei)
- 標題：同步正式 specs 並歸檔品質模型管線 Change
- 階段：Archive
- 分類：C-INTEGRATION（OpenSpec 規格同步與歸檔）
- Change／task／需求及驗證對應：`implement-quality-model-pipeline` 36／36 tasks；同步 DATA-05、完整 `quality-model-training` capability、Q-06～Q-08、VIS-05～VIS-07，對應 DEV-20261102-009 與 ADR-005。
- 目標：依使用者選擇 `Sync now`，將已驗證 delta requirements 合併至正式 specs，確認內容一致後再歸檔 Change。
- 已完成：保留既有正式規格內容並新增四組需求；建立 `openspec/specs/quality-model-training/spec.md`；將 Change 從 active changes 移至 `openspec/changes/archive/2026-11-02-implement-quality-model-pipeline/`，`.openspec.yaml` 與所有 artifacts 一併保留。
- 未完成：未 Commit、未 Push；未歸檔其他三個 active changes；未將 Synthetic 驗證升格為真實產線批准。
- 待驗證：真實製程與跨組採用限制延續 DEV-20261102-009；本次只驗證規格結構、同步內容及 archive 路徑。
- 待整合：其他 active changes 依各自 tasks 與授權處理，不因本 Change 歸檔而自動完成。
- 檔案操作與實作細節：修改 `openspec/specs/csv-ingestion/spec.md`、`quality-scenarios/spec.md`、`quality-visualization/spec.md`；新增 `openspec/specs/quality-model-training/spec.md`；移動完整 Change 至日期前綴 archive 路徑；追加本開發紀錄。
- 測試：通過。同步前 artifacts 全部 done、tasks 36／36；`openspec validate --specs` 與 `openspec validate --specs --strict` 均為 8 passed／0 failed；逐 requirement block 比對回報 `DELTA_SYNC_COMPARISON=PASS`；歸檔後 active `openspec list --json` 不再包含本 Change，archive 目標與 `.openspec.yaml` 均存在，正式 specs strict validation 再次為 8 passed／0 failed。
- 錯誤修復：不適用；同步與移動皆一次完成，未發生內容衝突或已存在 archive 目標。
- 限制：Archive 代表本次規格／實作工作流完成，不代表模型已通過真實產線驗證，也不代表其他 active changes 已完成。
- 資料來源：Synthetic canonical dataset；本次未改動資料或 artifact。
- 模型來源：Synthetic 正式 artifact（非產線）；本次未重新訓練。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次同步、歸檔與日誌。
- 證據來源與待辦：OpenSpec list／status／instructions／validate 輸出、delta 與 main spec 逐區塊比對、archive 路徑存在性檢查及使用者 `Sync now` 指示。後續是否 Commit／Push 仍待使用者授權。

## DEV-20261102-011

- 時間：2026-11-02 23:22:40 +08:00 (Asia/Taipei)
- 標題：建立正式模型監控摘要與 Canonical Synthetic SPC 修正提案
- 階段：Propose
- 分類：C-UI、C-SPC、C-ALARM、C-MODEL、C-DATA、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：新增 `fix-formal-model-dashboard-and-canonical-spc`，包含 `dashboard-workspace` WS-05～WS-06、`quality-scenarios` Q-09～Q-10、`spc-monitoring` SPC-05～SPC-07，以及 4 組／16 項待 Apply tasks；關聯 ADR-005、ADR-006（Proposed）與 TCP-003／004／006。
- 目標：將五項模型預測與四項實測 SPC 摘要分離，移除正式模式的 Mock／尚未接入過時文字，提供 SPC reason code 的繁體中文呈現，並為 canonical synthetic ground-truth profile 規劃可驗證且不造假的取樣證據與固定穩定 baseline。
- 已完成：依 `openspec-propose` 建立 proposal、三份 delta specs、design 及 tasks；檢查現有正式 Adapter、canonical loader、overview、SPC profile／baseline／controller 與相關測試；設計 hash 驗證的 `spc_samples.csv` sidecar、最早 25 個 `train + stable` 合成子組 baseline、validation／test 監控隔離、集中式中文 reason catalog 及 UI 來源生命週期。
- 未完成：尚未修改 Python、canonical artifact、CSV、Streamlit UI 或測試；尚未執行 Apply、正式測試、Sync、Archive、Commit 或 Push。
- 待驗證：sidecar 正式產生後須驗證五 specimen 合理子組、四目標 baseline 穩定、歷史／監控零重疊、hash／版本失敗降級、正式／Mock／不可用 UI、What-if、Tree SHAP 與完整回歸。真實工廠取樣與管制界限仍未驗證。
- 待整合：使用者審查本 Change 後，須另行執行 `$openspec-apply-change fix-formal-model-dashboard-and-canonical-spc`；跨組 synthetic sampling 契約仍依 TEAM 提案追蹤，不推定為工廠標準。
- 檔案操作：新增 `openspec/changes/fix-formal-model-dashboard-and-canonical-spc/` 下 `.openspec.yaml`、`proposal.md`、`design.md`、`tasks.md` 及三份 delta spec；追加 `docs/DEVELOPMENT_LOG.md`、`docs/DECISION_LOG.md`、`docs/TEAM_CHANGE_PROPOSALS.md`。未修改實作程式或資料。
- 實作細節：現況確認 canonical display 以 `cumcount() // 5` 產生未受 profile 承認的 subgroup，且 `profile_for_dataset` 僅綁定 C Mock；設計改以 manifest hash 驗證 sidecar。`synthetic-ground-truth-v2` 可規劃 SPC evidence；`simulated-inspection-v2` 在沒有平行試片證據時維持不可判定，不借用 ground-truth baseline。
- 測試：OpenSpec 結構驗證通過；`openspec validate fix-formal-model-dashboard-and-canonical-spc --strict` 回報 valid，`openspec status` 顯示 4／4 artifacts complete。另以唯讀探索腳本將目前 v2 最早 25 個 `train + stable`、n=5 候選組套入既有 baseline 邏輯，四項目標均回報 valid；此結果只支持設計可行性，不等同正式 sidecar／整合測試通過。Python／Streamlit／完整 pytest 尚未執行。
- 錯誤修復：探索腳本第一次因 PowerShell 引號造成 Python SyntaxError，改用 stdin here-string 後成功；未修改專案程式。
- 限制：所有新行為仍為 Proposed；25 組 baseline 與 Synthetic 五件合理子組只供合成示範，不是實際工廠取樣或管制標準。validation／test 同時用於模型評估與 SPC 示範監控，UI 必須明確區分用途。不新增預測良率、I-MR 或模型重訓。
- 資料來源：`generated_data/v2` 與 `generated_data/model_dataset_v2/synthetic-ground-truth-v2` Synthetic 資料；本次未改動資料內容。
- 模型來源：Synthetic 正式 artifact（非產線）與既有 C 公式 Mock；本次未重新訓練或修改 artifact。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本 Change 與日誌追加。
- 證據來源：OpenSpec context／list／status／instructions／validate 輸出、現有 specs、`c_dashboard`／`fccl_ml` 程式與測試、canonical／v2 manifest 及使用者本次 `$openspec-propose` 指示。
- 待辦：等待使用者審查 artifacts；確認後另行 Apply 並依 tasks 執行正式模型、SPC、What-if、SHAP、Streamlit 與回歸驗證。

## DEV-20261103-001

- 時間：2026-11-03 00:10:52 +08:00 (Asia/Taipei)
- 標題：完成正式模型摘要與 Canonical Synthetic SPC 修正 Apply／Verify
- 階段：Apply、Verify
- 分類：C-UI、C-SPC、C-ALARM、C-MODEL、C-DATA、C-WHATIF、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：`fix-formal-model-dashboard-and-canonical-spc` tasks 1.1～4.4；對應 `dashboard-workspace` WS-05～WS-06、`quality-scenarios` Q-09～Q-10、`spc-monitoring` SPC-05～SPC-07；關聯 TCP-003／004／006、ADR-005／007。
- 目標：讓正式模型五目標預測與四目標實測 SPC 清楚分流，移除過時 Mock／尚未接入文字，將 SPC 狀態轉為可讀繁體中文，並以可稽核的 canonical sidecar 建立 Synthetic 示範 baseline。
- 已完成：產生並驗證版本化 `spc_samples.csv`；manifest／data dictionary 記錄 sidecar hash 與 profile；loader 驗證 hash、版本、單位、樣本及 cohort；移除依列序自動湊組；以最早 25 個 `train + stable` 合格子組建立固定 baseline，只監控 validation／test；快取身分涵蓋資料、sidecar、profile、history 及規則版本；overview 分為五項模型預測與四項實測 SPC；SPC Tab／Alarm 共用繁體中文 formatter 且保留 raw code；正式、Mock、不可用來源依 AdapterInfo 顯示且不互相降級。
- 未完成：尚未執行 OpenSpec Sync 或 Archive；尚未 Commit／Push；未建立真實工廠取樣 profile 或產線管制界限。
- 待驗證：真實產線資料泛化、實際平行試片與量測系統、正式 baseline 核准、因果調參效果及 A／B／C 跨組採用仍待製程／品質與團隊驗證。
- 待整合：使用者審查本次 Apply 結果後，另行決定 Sync／Archive 與 Git 操作；`simulated-inspection-v2` 在缺少平行試片證據時仍安全降級為 SPC 不可判定。
- 檔案操作：修改 `fccl_ml/dataset.py`、canonical loader、SPC source／controller／messages、overview／SPC UI 與相關測試；重建 `generated_data/model_dataset_v2` canonical profiles，Synthetic profile 新增 `spc_samples.csv`，inspection profile不宣告 SPC evidence；更新本 Change tasks 與三份追蹤文件。未刪除原七表、未重訓模型。
- 實作細節：合理子組固定 n=5、同卷、同 Synthetic phase、MD 連續、時間有序、條件一致且不重疊。baseline 固定選最早 25 個 eligible `train + stable` 子組；monitoring 僅用 validation／test eligible 子組。Synthetic phase／eligibility 僅存於 SPC metadata，不進正式模型特徵或 What-if allowlist。
- 測試：定向測試 `.\.venv-ml\Scripts\python.exe -m pytest -q tests/test_ml_dataset.py tests/test_ml_canonical_spc.py tests/test_c3_messages.py tests/test_c3_sources.py tests/test_c3_baseline.py tests/test_c3_controller.py tests/test_c2_ui.py tests/test_c3_ui.py tests/test_ml_formal_ui.py`，67 passed；正式／Mock／不可用端到端測試 24 passed；完整 `.\.venv-ml\Scripts\python.exe -m pytest -q` 最終 359 passed、915 warnings；`openspec validate fix-formal-model-dashboard-and-canonical-spc --strict` valid；`git diff --check` 無內容錯誤，僅既有 CRLF→LF 提示。
- 錯誤修復：完整回歸第一次在 collection 因 `.venv-ml` 缺少 `playwright` 而中止；確認 `requirements-c-test.txt` 鎖定 1.64.1 後安裝至 `.venv-ml`，再完整重跑並通過。另依新九格摘要布局將既有 UI 測試的 SPC metric index 由模型區改指向 SPC 區。
- 限制：測試仍有 SHAP／NumPy、pandas 未來行為及 CPU 核心偵測 warnings，但無測試失敗。25 組 baseline 與 n=5 子組只屬 Synthetic 示範，不是工廠 SPC 標準；模型仍為 Synthetic artifact，What-if 仍是關聯情境推論，不是因果保證；不提供預測良率。
- 資料來源：`generated_data/model_dataset_v2/synthetic-ground-truth-v2` Synthetic canonical artifact；`simulated-inspection-v2` 不借用 ground-truth SPC evidence；C Mock 測試資料維持隔離。
- 模型來源：既有 Random Forest Synthetic 正式 artifact（非產線）及明確選取的 C Mock；本 Change 未重新訓練或更換 Champion。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次 Apply、驗證及日誌。
- 證據來源與待辦：上述 pytest／OpenSpec／Git 檢查輸出、canonical manifest／sidecar、Change tasks、ADR-007 與 TCP 補充。下一步由使用者審查後決定 Sync／Archive；未獲授權前不 Commit／Push。

## DEV-20261103-002

- 時間：2026-11-03 00:51:27 +08:00 (Asia/Taipei)
- 標題：建立 Alarm 彙整與分析可用性改善提案
- 階段：Explore、Propose
- 分類：C-UI、C-SPC、C-ALARM、C-WHATIF、C-MODEL、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：新增 `improve-dashboard-alarm-and-analysis-usability`，包含 WS-07、SPC-08～09、Q-11、VIS-08～09 與 6 組／17 項待 Apply tasks；關聯 ADR-008（Proposed）及 TCP-003／004／006。
- 目標：解決 Canonical 全範圍數千 SPC 事件逐筆紅色展開造成的 alarm fatigue 與功能入口不可尋得，並改善資料載入、What-if、Heatmap、SHAP 的就緒狀態與下一步提示。
- 已完成：建立 proposal、四份 delta specs、design 與 tasks；設計保留全部原始 `SpcEvent`，另以連續異常事件群呈現；Overview 採有界摘要、SPC Tab 提供受控歷史明細；規劃共同能力矩陣、Heatmap 正／負相關摘要與 SHAP 能力導引。
- 未完成：尚未修改 Python、Streamlit、資料、模型或測試；尚未執行 Apply、Sync、Archive、Commit 或 Push。
- 待驗證：事件群邊界與 ID 穩定性、原始事件守恆、全 Canonical 極端事件量、tabs 可尋得、未載入／Mock／正式／不相容生命週期、Heatmap 摘要及正式 Tree SHAP 回歸均待 Apply。
- 待整合：使用者審查 artifacts 後另行執行 `$openspec-apply-change improve-dashboard-alarm-and-analysis-usability`；此提案不改變模型 Champion、SPC baseline／規則或 Synthetic 資料。
- 檔案操作：新增 `openspec/changes/improve-dashboard-alarm-and-analysis-usability/` 下 proposal、四份 delta specs、design、tasks；追加三份追蹤日誌。未修改實作程式。
- 實作細節：Proposed 事件群依 target groups 的合理子組連續性建立，正常有效組、無效／break、換批與條件邊界結束群；完整 hash、event ID 與界限移至可展開技術明細。Heatmap 摘要只消費既有有效 cell result，不另算或宣稱因果。
- 測試：`openspec validate improve-dashboard-alarm-and-analysis-usability --strict` 通過，`openspec status` 顯示 4／4 artifacts complete；Python／Streamlit 測試未執行，因本輪僅 Propose。
- 錯誤修復：不適用；本輪未修改程式。
- 限制：全部行為仍為 Proposed。事件群只改呈現，不降低 SPC 靈敏度；Heatmap 相關不是因果；Mock 不提供真正 SHAP；專案仍為 Synthetic／Mock 模擬。
- 資料來源：唯讀檢查 `synthetic-ground-truth-v2`；未改動資料。
- 模型來源：既有 Synthetic 正式 artifact 與 C 公式 Mock；未重新訓練。
- 真實製程驗證：不適用於目前純模擬專案；未執行。
- Git Hash：尚未提交；目前 HEAD 不包含本 Change 與日誌追加。
- 證據來源與待辦：使用者畫面、唯讀程式檢查、OpenSpec specs／CLI 輸出及前次全範圍事件統計。下一步等待使用者審查並另行 Apply。

## DEV-20261103-003

- 時間：2026-11-03 01:41:00 +08:00 (Asia/Taipei)
- 標題：完成 Alarm 事件群、分析就緒狀態與 Heatmap／SHAP 可用性改善
- 階段：Apply、Verify
- 分類：C-UI、C-SPC、C-ALARM、C-WHATIF、C-MODEL、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：`improve-dashboard-alarm-and-analysis-usability` tasks 1.1～6.3；對應 SPC-08、WS-07、C-11、VIS-08、VIS-09、ADR-008 及 TCP-003／004／006。
- 目標：保留完整 SPC 稽核事件與既有管制規則，同時消除數千筆重複紅色卡片造成的 alarm fatigue，並讓 What-if、Heatmap、SHAP 清楚顯示就緒條件、阻塞原因與下一步。
- 已完成：新增純事件群投影與穩定 incident ID；Overview 改為進行中／各目標最新歷史的有界摘要；SPC Tab 提供目標、批號、規則、狀態篩選、每頁最多 10 群及原始 event 技術明細。新增 Data／What-if／Heatmap／SHAP Summary／Dependence 就緒矩陣，區分來源已選與 dataset 已載入；What-if 提供精確阻塞指引。Heatmap 新增最強正／負相關、r、n、版本化品質方向與雙側規格限制；SHAP 只在相容 Adapter、Provider 與 manifest ready 時請求，並補充 Summary／Dependence 用途。
- 未完成：未 Sync／Archive 本 Change；未 Commit 或 Push；未進行真實產線資料、因果調參或工廠 Alarm 門檻驗證。
- 待驗證：使用者仍需以實際操作驗收事件群篩選、資訊密度與畫面易讀性；真實資料接入及跨組採用另開規格與驗證。
- 待整合：待使用者驗收後再決定 OpenSpec Sync／Archive。TCP-003／004／006 的跨組狀態不因本機 Apply 自動升格。
- 檔案操作：新增 `c_dashboard/spc/incidents.py`、`c_dashboard/ui/readiness.py`、`c_dashboard/visualization/heatmap_summary.py` 與三組專屬測試；更新 Overview、SPC、layout、sidebar、tabs、What-if、visualization UI、既有 UI 測試、Change tasks、ADR-008 及團隊提案補充。未修改 Synthetic CSV、SPC baseline／規則或模型 artifact。
- 實作細節：Canonical 全量 2,913 筆原始規則事件投影為 309 個事件群且事件守恆；ROLL-0121 為 57 筆／3 群。事件群依目標、批號、連續有效子組與 break 邊界切分；原始事件保留為唯一稽核來源。品質方向 metadata 版本為 `quality-direction-v1`，MD／TD 定義為 bounded，外觀明示 1=NG。
- 測試：通過。專屬事件群 3 passed、Canonical 極端案例 1 passed、SPC／What-if UI 15 passed、就緒矩陣 3 passed、Heatmap 摘要與計算 7 passed、C1／C6 UI 及正式端到端皆通過；最終完整回歸 `370 passed, 915 warnings in 588.06s`。`git diff --check` exit 0（僅 `TEAM_CHANGE_PROPOSALS.md` CRLF→LF 警告）；`openspec validate improve-dashboard-alarm-and-analysis-usability --strict` valid。
- 錯誤修復：第一次完整回歸為 368 passed／2 failed，兩個舊測試仍要求逐筆 SPC 紅卡；依新規格改驗證有界摘要及事件資料保留後，定向 2／2 與第二次完整回歸 370／370 通過。另修正 incident detail widget 在資料內容變更時沿用失效 ID 的 key 問題。
- 限制：資料來源仍為 Synthetic／C Mock；模型為 Synthetic 正式 artifact 或公式 Mock，非真實產線。事件群不降低 SPC 靈敏度、不代表事件已處置；Pearson 相關與 SHAP 不證明因果；What-if 不控制機台。
- 資料來源：`synthetic-ground-truth-v2` canonical projection、C 專用 Mock、既有 CSV fixtures；未改動生成資料。
- 模型來源：Synthetic 正式 Random Forest artifact 與 C 公式 Mock；未重訓、未更換 Champion，Mock 不產生真正 SHAP。
- 真實製程驗證：未執行；本專案目前為模擬／決策輔助。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次及先前未提交變更。
- 證據來源：pytest 輸出、OpenSpec instructions／strict validation、`git diff --check`、Canonical 事件群統計、Streamlit AppTest 與使用者 `$openspec-apply-change` 指示。
- 待辦：由使用者啟動 Streamlit 驗收；確認後另行決定 Sync／Archive、Commit／Push。第三方 SHAP／NumPy deprecation warnings 與 pandas 測試 warning 不影響本次通過結果，但可於依賴升級 Change 處理。

## DEV-20261103-004

- 時間：2026-11-03 06:28:04 +08:00 (Asia/Taipei)
- 標題：同步 v2 合成資料生成正式規格
- 階段：Maintenance（OpenSpec Sync）
- 分類：C-DATA、C-INTEGRATION（規格同步）
- Change／task／需求及驗證對應：`regenerate-training-data-v2` 7／7 tasks；同步其唯一 delta `specs/data-generation/spec.md`。
- 目標：在不歸檔 Change 的前提下，將已完成的 v2 資料規模、良率、失敗機制、穩定／漂移、標籤來源與可重現輸出契約納入正式 specs。
- 已完成：依 status 的 `artifactPaths.specs.existingOutputPaths` 同步唯一 delta；新建 `openspec/specs/data-generation/spec.md`，加入六項 ADDED requirements 及其情境；未修改其他正式 capability。
- 未完成：未 Archive；未補寫 delta 原先缺少的正式 Purpose；未 Commit／Push；未開始 v3 或測試線控制台 Change。
- 待驗證：Archive 前應直接將 `data-generation` 的 TBD Purpose 改為正式說明，之後執行 strict specs validation。
- 待整合：後續依使用者既定順序歸檔本 Change，再處理 `fix-formal-model-dashboard-and-canonical-spc` 與 `improve-dashboard-alarm-and-analysis-usability`。
- 檔案操作：新增 `openspec/specs/data-generation/spec.md`；追加本紀錄。未修改 CSV、metadata、生成器、模型或 UI。
- 實作細節：主 spec 採 canonical `## Requirements` 格式，將 delta 的 WHEN／THEN 正規化為 OpenSpec scenario 格式；因 delta 無 `## Purpose`，依 sync 規則保留明確 TBD，而未自行虛構正式 Purpose。
- 測試：通過。`openspec validate --specs` 為 9 passed／0 failed；`data-generation` 回報 Purpose placeholder warning，狀態屬待修而非失敗。
- 錯誤修復：不適用；同步未發生需求衝突。
- 限制：本次只同步 v2 正式行為契約，不代表 v3 設計、真實資料或工廠規格已批准。
- 資料來源：規格來源為既有 `regenerate-training-data-v2` delta；未讀寫新的生產資料。
- 模型來源：不適用；未訓練或載入模型。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次同步與日誌。
- 證據來源：`openspec list/status/instructions specs/validate --specs` 輸出、delta 與新正式 spec。
- 待辦：執行 `$openspec-archive-change regenerate-training-data-v2` 前補正式 Purpose，或由 archive workflow 明確處理該 warning；後續是否 Commit／Push 仍待使用者授權。

## DEV-20261103-005

- 時間：2026-11-03 06:39:34 +08:00 (Asia/Taipei)
- 標題：完成三項規格同步／歸檔並建立測試線控制台提案
- 階段：Maintenance（OpenSpec Sync／Archive）、Propose
- 分類：C-UI、C-DATA、C-SPC、C-ALARM、C-WHATIF、C-MODEL、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：同步並歸檔 `regenerate-training-data-v2`、`fix-formal-model-dashboard-and-canonical-spc`、`improve-dashboard-alarm-and-analysis-usability`；新增 `build-testline-simulation-control-room` 的 proposal、10 份 delta specs、design、tasks，涵蓋 Gate 0～4；關聯 ADR-009、TCP-007。
- 目標：先收斂已完成 Change 的正式規格，再把使用者確認的單一 Mode B 測試線、Synthetic v3、四目標模型、製程 SPC、Run 管理與控制台分階段規劃成可 Apply 的完整契約。
- 已完成：補齊 `data-generation` Purpose；三個舊 Change 已依序同步並移至 `openspec/changes/archive/2026-11-03-*`；正式 specs 納入資料生成、模型／SPC 分區、事件群及分析就緒契約。新 Change 已完成 4／4 planning artifacts，包含 3 個新 capability、7 個既有 capability delta，以及 Gate 0 靜態原型先驗收、Gate 1 契約、Gate 2 v3／模型、Gate 3 模擬器／SPC、Gate 4 整合的 tasks。
- 未完成：未 Apply 新 Change；未修改測試線 Python／Streamlit 實作、Synthetic v3、模型 artifact、AGENTS.md 或 SKILL.md；未 Commit／Push。
- 待驗證：Gate 0 版面需於後續 Apply 完成後由使用者人工驗收；Gate 1～4 的資料、模型、模擬器、SPC、效能及端到端測試尚未執行。
- 待整合：`define-seven-table-integration` 與 `define-model-selection-governance` 仍為進行中 Change，未因本次歸檔或新提案自動完成；跨組採用仍依 TCP-003～007 討論。
- 檔案操作：更新 7 份正式 specs 並新增 `openspec/specs/data-generation/spec.md`；移動三個完成 Change 至 archive；新增 `openspec/changes/build-testline-simulation-control-room/` 下 proposal、design、tasks 與 10 份 delta specs；追加三份追蹤文件。未改動 CSV、模型、runtime data 或應用程式碼。
- 實作細節：新提案採單一產品 `FCCL-DEMO-001`／`SIM-RECIPE-3.0`，5 模擬秒 tick、30 模擬秒品質節奏、60 秒 checkpoint、厚度五點 X-bar／R、其他連續訊號 I-MR／EWMA、四目標 v3 模型及本機隔離 Run。Gate 0 明定只用 fixture 且完成後停止等待驗收。
- 測試：通過。三次正式 specs strict validation 均為 9 passed／0 failed；`openspec validate build-testline-simulation-control-room --strict` valid；`openspec status` 顯示新 Change 4／4 artifacts complete。Python／Streamlit 測試未執行，因本輪僅 Sync／Archive／Propose。
- 錯誤修復：更正 DEV-20261103-004 的暫時狀態：`data-generation` Purpose 已補為正式說明，`regenerate-training-data-v2` 已完成 strict validation 並歸檔，不再是 TBD／未 Archive。
- 限制：全部新控制台行為仍是規劃，Synthetic 配方數值不是工廠標準；不接真實設備／PLC／MES，不提供預測良率、外觀 v3、因果改善保證或一般導覽 SHAP。
- 資料來源：本輪僅規格與 planning artifacts；未生成或改寫資料。
- 模型來源：本輪未訓練或載入新模型；v2 artifact 保留，v3 四目標模型屬待 Apply。
- 真實製程驗證：未執行；不適用於本輪規劃工作。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次同步、歸檔、提案及日誌。
- 證據來源：OpenSpec context／status／instructions／validate、正式與 delta specs、三個 archive 目錄、使用者本次 `$openspec-propose` 指示及已確認 Explore 決策。
- 待辦：由使用者審查新 Change；若批准，另行執行 Apply，且必須先只完成 Gate 0 並停止供面板驗收。Git Commit／Push 仍需另行授權。

## DEV-20261103-006

- 時間：2026-11-03 06:45:19 +08:00 (Asia/Taipei)
- 標題：完成測試線控制台 Gate 0 靜態 UI 原型
- 階段：Apply、Verify（Gate 0；等待人工驗收）
- 分類：C-UI、C-SPC、C-ALARM、C-WHATIF、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：`build-testline-simulation-control-room` tasks 0.1～0.8；對應 WS-08～WS-11、MW-06、PSM-01～05、Q-12～14、VIS-10～12、TRM-03～04 的 Gate 0 fixture 呈現；關聯 ADR-009、TCP-007。
- 目標：在不接後端、模型或設備的前提下，先提供可啟動、可互動且資訊密度可驗收的單一 Mode B Streamlit 控制台原型。
- 已完成：新增獨立 `testline_prototype.py` 及 UI module；完成四頁導航、產線與材料位置、產品規格／配方、七項主要與三項進階數字輸入、候選確認、三張 60 點 SPC fixture、四項品質 fixture、有界 Alarm、詳細 SPC、What-if／Heatmap readiness 與 completed／interrupted Run 紀錄。所有區域明示 Gate 0 靜態 fixture。
- 未完成：Gate 1～4 共 31 項尚未開始；未更新 AGENTS.md／SKILL.md；未建立正式 schema、Synthetic v3、四模型、模擬時鐘、Run Store 或正式控制台接線；未 Commit／Push。
- 待驗證：等待使用者人工檢視字級、排版、資訊密度、導覽與互動。未取得明確 Gate 0 驗收前不得開始 Gate 1。
- 待整合：正式 `app.py` 保留原入口，Gate 4 才會切換一般入口；Gate 0 原型不得被當成正式模型／SPC 或執行中模擬結果。
- 檔案操作：新增 `testline_prototype.py`、`c_dashboard/testline_prototype.py`、`tests/test_testline_prototype_ui.py`、`docs/evidence/gate0/README.md` 與 PNG 截圖；更新本 Change tasks 與本日誌。未修改 `app.py`、v2 CSV、模型 artifact 或 runtime_data。
- 實作細節：原型 session 只保存 fixture 候選；表單未確認不改 setpoint，What-if 帶回後仍需再確認。技術事件預設收合，首頁最多三圖；Heatmap current-run fixture 明示 18／30 樣本不足；Run 不寫檔、不續跑、不進訓練。
- 測試：通過。專屬 AppTest `6 passed`；專屬＋既有 C1／mode workspace 回歸 `14 passed`；Streamlit health HTTP 200；Playwright 1600×1000 browser smoke 與截圖通過；OpenSpec strict validation valid；`git diff --check` 無內容錯誤。
- 錯誤修復：首次專屬測試 4 passed／2 failed，原因為驗收測試讀取 metric 與 form 提交方式錯誤，修正測試後 6／6 通過。首次瀏覽器驗收因缺少 Playwright Chromium executable 失敗，安裝相符測試瀏覽器後重測通過。另移除原型內已排定淘汰的 `use_container_width` 用法。
- 限制：所有圖、品質值、Alarm、Heatmap、What-if 與 Run 都是固定 UI fixture；未驗證模擬機理、模型效能、SPC 統計正確性或真實製程。
- 資料來源：Gate 0 內建靜態 fixture；未讀寫 raw data、generated_data 或 runtime_data。
- 模型來源：不適用；未載入 Mock、v2 或正式模型。
- 真實製程驗證：未執行；Gate 0 不控制設備。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本次 Gate 0。
- 證據來源：`docs/evidence/gate0/`、pytest／OpenSpec／HTTP health／Playwright 輸出、使用者 `$openspec-apply-change` 指示。
- 待辦：使用者以 `.\.venv-ml\Scripts\python.exe -m streamlit run testline_prototype.py` 驗收；確認後另行繼續 Apply Gate 1。未獲確認前停止。

## DEV-20261103-007

- 時間：2026-11-03 06:55:00 +08:00 (Asia/Taipei)
- 標題：修正 Gate 0 原型深色主題殘留
- 階段：Apply、Verify（Gate 0 人工驗收修正）
- 分類：C-UI、C-TEST
- Change／task／需求及驗證對應：`build-testline-simulation-control-room` Gate 0 tasks 0.1～0.7 的驗收修正；對應 WS-08～WS-10 的可讀性與淺色控制台要求。
- 目標：消除 host dark theme 導致的導航白字、配方黑底及參數區黑底，統一為淺色系背景與深色字。
- 已完成：原型內限定 `color-scheme: light` 與 Streamlit radio、container、number input、selectbox、expander、form、metric／caption 的淺色 CSS；固定配方、事件、What-if 與 Run 表格改用淺色 HTML table。未修改全域 `.streamlit` theme，避免影響既有 `app.py`。
- 未完成：Gate 1～4 未開始；仍待使用者再次人工驗收。
- 待驗證：使用者本機瀏覽器實際主題與縮放下的主觀版面確認。
- 待整合：不適用；本次僅 Gate 0 原型視覺修正。
- 檔案操作：修改 `c_dashboard/testline_prototype.py`；新增兩張淺色驗收截圖；更新 Gate 0 evidence 與本日誌。未修改 AGENTS.md、SKILL.md、app.py、CSV 或模型。
- 實作細節：Playwright 刻意使用 `color_scheme='dark'` 驗證覆寫；導航與 input 的 computed color／background 均為深色字 `rgb(21, 34, 56)`／白底 `rgb(255, 255, 255)`。
- 測試：通過。`tests/test_testline_prototype_ui.py` 為 6 passed；兩次瀏覽器 computed-style assertion 與截圖通過。
- 錯誤修復：修正 CSS 只改 `.stApp` 背景、未覆寫 Streamlit theme token 造成的混色問題。
- 限制：Streamlit 最上方工具列仍由框架管理；業務控制台內容已固定為淺色。所有數值仍是 Gate 0 fixture。
- 資料來源：靜態 fixture；未讀寫資料檔。
- 模型來源：不適用。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本修正。
- 證據來源：使用者截圖、`docs/evidence/gate0/testline-control-room-light-theme.png`、`testline-parameter-panel-light-theme.png`、pytest 與 Playwright computed style。
- 待辦：由使用者重啟原型驗收；確認前仍停止於 Gate 0。

## DEV-20261103-008

- 時間：2026-11-03 07:03:52 +08:00 (Asia/Taipei)
- 標題：統一 Gate 0 全頁淺色系並展開全部 SPC 訊號
- 階段：Apply、Verify（Gate 0 人工驗收修正）
- 分類：C-UI、C-SPC、C-TEST
- Change／task／需求及驗證對應：`build-testline-simulation-control-room` Gate 0 tasks 0.5～0.7；對應 WS-08～09、PSM-01～03、PSM-05。
- 目標：移除圖表及其他沿用元件的黑底／白字，並讓 SPC 詳細頁可同時監看所有製程訊號。
- 已完成：三張首頁圖與五張詳細 SPC 圖改為明確淺色 Altair theme，加入 actual、中心／目標及上下限／警戒線；移除 SPC 訊號 selectbox，詳細頁一次呈現厚度、熟化溫度、排風量、線速、壓合壓力。補強 Tabs、alert、button、code／JSON 與 Heatmap／Run table 的淺色樣式。
- 未完成：Gate 1～4 未開始；仍待使用者再次人工驗收。
- 待驗證：使用者本機長頁面捲動、五圖資訊量與主觀閱讀舒適度。
- 待整合：正式 R 圖與 I-MR 的完整雙圖只在 Gate 3／4 實作；Gate 0 仍是版面 fixture，不將單張示意冒充已完成統計引擎。
- 檔案操作：修改原型 UI 與專屬測試；新增 SPC、What-if、Run 淺色驗收截圖；更新 evidence 與本日誌。未修改正式 app、資料或模型。
- 實作細節：首頁保留 3 張摘要以控制密度；SPC 詳細頁採兩欄排列 5 張圖並加入全訊號狀態卡。瀏覽器檢查以 dark color scheme 執行，確認 5 張圖皆可見及 Run table 白底。
- 測試：通過。專屬＋C1／mode workspace 回歸 `14 passed`；Playwright 詳細 SPC 可見圖數 5，What-if／Run 淺色檢查通過。
- 錯誤修復：第一次 Playwright 以所有已建立 Vega DOM 計數得到 8，改以可見元素驗證後確認目前頁面恰為 5 張；這是 Streamlit 前頁 DOM 保留，不是重複渲染。
- 限制：Gate 0 圖表資料與界限是固定 fixture；R 圖正式版位與統計計算待 Gate 3／4。
- 資料來源：靜態 fixture。
- 模型來源：不適用。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本修正。
- 證據來源：使用者指示、`docs/evidence/gate0/` 截圖、pytest 及 Playwright。
- 待辦：使用者再次驗收；確認前仍停止於 Gate 0。

## DEV-20261103-009

- 時間：2026-11-03 07:12:21 +08:00 (Asia/Taipei)
- 標題：修復 Gate 0 在系統 Streamlit 1.36 的整頁停止問題
- 階段：Apply、Verify（Gate 0 人工驗收修正）
- 分類：C-UI、C-TEST、C-INTEGRATION
- Change／task／需求及驗證對應：`build-testline-simulation-control-room` Gate 0 tasks 0.1、0.2、0.4～0.7；對應 WS-08～10 的可啟動與可操作驗收。
- 目標：排除使用者看到大量紅色 TypeError、無法切頁或操作的跨 Streamlit 版本問題，同時保留已接受的後四張圖淺色兩欄版面。
- 已完成：確認 `.venv` 未安裝 Streamlit，直接輸入 `streamlit`／系統 Python 會使用 1.36.0，而 `.venv-ml` 為 1.66.1；移除 1.36 不相容的 `width="stretch"` 參數與不必要寬度參數，改由 CSS／容器管理。完整停止舊 server 後，以 1.36 實機驗證四頁、圖表、表單及 What-if；1.66 回歸維持通過。
- 未完成：Gate 1～4 未開始；仍待使用者重新啟動與人工驗收。
- 待驗證：使用者本機依指定 `.venv-ml` 命令重開後的最終確認。
- 待整合：後續可將 Streamlit 執行依賴正式化於 Gate 1；本次未改 requirements 或虛擬環境契約。
- 檔案操作：修改 `c_dashboard/testline_prototype.py`；新增系統 1.36 修復前／後截圖；更新 evidence 與本日誌。未修改資料、模型、AGENTS.md、SKILL.md 或正式 app。
- 實作細節：舊 server 的 imported module 不會可靠熱載入，因此 traceback 曾顯示新檔案行號卻執行舊函式。驗證流程改為完整終止 listener、重啟 server，再以 Playwright 操作。
- 測試：通過。系統 Streamlit 1.36 四頁可見圖數為 3／5／0／0 且零 exception；表單提交與 What-if 計算通過；`.venv-ml` 專屬＋既有 UI 回歸 `14 passed`。
- 錯誤修復：修復 `FormMixin.form_submit_button() got an unexpected keyword argument 'width'`；使用者截圖中 radio 行的 `str object cannot be interpreted as an integer` 判定為舊 server／熱載入錯位的一部分，完整重啟後未再重現。
- 限制：推薦且唯一受專案驗證的啟動方式仍為 `.venv-ml` Python；系統 1.36 僅作防呆相容測試。
- 資料來源：靜態 fixture。
- 模型來源：不適用。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本修正。
- 證據來源：使用者 traceback、Streamlit signature／version 檢查、Playwright 1.36 四頁與互動驗證、pytest。
- 待辦：使用者先 `Ctrl+C` 完整停止舊 server，再用 `.\.venv-ml\Scripts\python.exe -m streamlit run testline_prototype.py` 重開；確認前仍停止於 Gate 0。

## DEV-20261103-010

- 時間：2026-11-03 07:18:46 +08:00 (Asia/Taipei)
- 標題：壓縮 Gate 0 參數面板並移除不穩定 radio 導航
- 階段：Apply、Verify（Gate 0 人工驗收修正）
- 分類：C-UI、C-SPC、C-TEST
- Change／task／需求及驗證對應：`build-testline-simulation-control-room` Gate 0 tasks 0.2、0.4、0.6～0.8；對應 WS-08～10。
- 目標：恢復使用者指定的緊湊三欄參數面板、保留後四張 SPC 圖版面，並徹底排除點進 SPC 後停在 radio TypeError 的問題。
- 已完成：頁面導航由 `st.radio` 改為四個固定按鈕及 session page state；入口每次 rerun 強制 reload Gate 0 UI module。參數由按欄分配改成逐列三欄，並在窄視窗強制保持水平三欄；順序與既定主要參數一致。後四張 SPC 圖的兩欄淺色布局保留。
- 未完成：Gate 1～4 未開始；等待使用者重新啟動後驗收。
- 待驗證：使用者實際瀏覽器縮放與螢幕寬度下的最終閱讀感受。
- 待整合：正式應用入口與響應式設計仍留 Gate 4；本次只修 Gate 0。
- 檔案操作：修改原型入口、UI module 與專屬測試；新增 800px 參數網格及 SPC 導航修復截圖；更新 evidence 與日誌。未改資料、模型、AGENTS.md、SKILL.md 或正式 app。
- 實作細節：800px Playwright 驗證前 3 個 number inputs y 座標一致、次 3 個亦一致；四頁按鈕依序往返後零 `stException`，SPC 可見圖數為 5。
- 測試：通過。系統 Streamlit 1.36 窄視窗／四頁瀏覽器操作通過；`.venv-ml` 專屬＋既有 UI 回歸 `14 passed`；OpenSpec strict validation valid。
- 錯誤修復：刪除產生 `str object cannot be interpreted as an integer` 截圖的 radio 路徑；修正三個長欄在 responsive stack 後造成參數順序錯亂與超長頁面。
- 限制：800px 下三欄文字會較緊湊；推薦以桌面寬度或 90%～100% 瀏覽器縮放驗收。Gate 0 仍是 fixture。
- 資料來源：靜態 fixture。
- 模型來源：不適用。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本修正。
- 證據來源：使用者截圖、`docs/evidence/gate0/testline-compact-parameter-grid-800px.png`、`testline-spc-navigation-fixed.png`、Playwright 與 pytest。
- 待辦：使用者必須完整停止所有舊 Streamlit process，再以 `.venv-ml` 指令重開；確認前仍停止於 Gate 0。

## DEV-20261103-011

- 時間：2026-11-03 07:36:33 +08:00 (Asia/Taipei)
- 標題：補強連續卷材位置、五圖總覽與警報調參流程
- 階段：Apply、Verify（Gate 0 人工驗收修正）
- 分類：C-UI、C-SPC、C-ALARM、C-TEST
- Change／task／需求及驗證對應：`build-testline-simulation-control-room` Gate 0 tasks 0.3、0.5～0.8；對應 WS-08～11、PSM-02、PSM-04～05。
- 目標：正確表達連續卷材同時位於多站、以語意色顯示品質狀態、在首頁呈現全部五項 SPC，並建立警報明細與參數調整的可操作動線。
- 已完成：產線圖為各站配置不同邏輯區段並將 SEG-018 明示為目前追蹤區段；品質卡改用綠／黃／紅／灰語意狀態。首頁 SPC 由 3 圖改為 5 圖 3＋2 排列。AI Alarm 改名異常警報摘要；SPC 詳細頁新增異常警報中心，分開 SPC 製程警報與品質預測警示，並提供返回生產控制台的按鈕與提示。
- 未完成：Gate 1～4 未開始；正式材料流、模型判定、警報規則與復歸仍待後續 Gate。
- 待驗證：使用者對五圖首頁資訊密度、語意色及警報動線的人工驗收。
- 待整合：正式版需以 Gate 3 的 segment movement、SPC event 與 Gate 4 路由取代 fixture。
- 檔案操作：修改原型 UI 與專屬測試；新增五圖／品質狀態與警報中心截圖；更新 evidence 與日誌。未改資料、模型或正式 app。
- 實作細節：目前 fixture 表示連續卷材被切成邏輯 MD 區段，各站同時工作；Highlight 是 UI 選取，不是機台開關或 Alarm。警報調參按鈕只導頁與帶提示，不會清除事件。
- 測試：通過。Playwright 確認首頁 5 張可見圖、品質狀態綠色 computed style、警報明細與返回參數調整流程零 exception；專屬＋既有 UI 回歸 `15 passed`；OpenSpec strict validation valid。
- 錯誤修復：消除單一熟化 Highlight 的歧義、`vs 下限` 英中混用、首頁只選三圖及 AI／SPC 警報來源混稱。
- 限制：所有 segment、品質與警報仍是 Gate 0 fixture；綠色只表示 fixture 規格判讀，不是真實檢驗合格。
- 資料來源：靜態 fixture。
- 模型來源：Prototype RF fixture（未載入模型，只作版位標示）。
- 真實製程驗證：未執行。
- Git Hash：尚未提交；目前 HEAD `df510531471d680662899ab21b613d3b33de350a` 不包含本修正。
- 證據來源：使用者確認方向、Playwright、pytest、`docs/evidence/gate0/testline-five-spc-quality-status.png` 與 `testline-spc-alarm-center.png`。
- 待辦：使用者於 http://localhost:8510 驗收；確認前仍停止於 Gate 0。
