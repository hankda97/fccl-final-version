# FCCL 品質預測與 SPC：協作規範

狀態：使用者已驗收 `build-testline-simulation-control-room` Gate 0，並授權繼續完成 Gate 1–4；成果限 Synthetic 測試線，跨組契約與真實產線採用仍待團隊確認。

## 1. 目標與本階段範圍

正式使用者介面為單一 Mode B「測試線模擬控制台」，整合塗佈、熟化、壓合與環境資料，以可比較的 Champion／Challenger 模型預測抗剝離度、尺寸安定性 MD/TD 與耐熱度四個連續目標，使用 Streamlit 呈現製程 SPC、Alarm、What-if、Heatmap、Run 紀錄與調參候選。新控制台不顯示外觀模型、預測良率或 SHAP 一般入口；v2 五目標能力只保留作回退與測試。

本階段已授權依 `build-testline-simulation-control-room` 完成 Gate 1–4：版本化契約、Synthetic v3、四目標模型、連續模擬器、Run Store、製程 SPC 與正式控制台整合；仍未授權正式產線接入、PLC／MES／機台寫入或線上自動重訓。以下角色是工作責任分工，不代表需要同時啟動多個 AI 代理。

## 2. OpenSpec 工作流程

AGENTS.md 管理協作，SKILL.md 管理技術實作；兩者不取代 OpenSpec 的變更與需求文件。預定結構如下：

```text
openspec/
  config.yaml
  specs/<capability>/spec.md
  changes/<change-id>/
    proposal.md
    specs/<capability>/spec.md
    design.md
    tasks.md
```

- 使用內建 spec-driven 流程：proposal → specs → design → tasks → implementation → verification → archive。
- proposal 說明目的、範圍及影響；specs 定義可驗收行為；design 記錄技術決策；tasks 列出實作與驗證項目。
- 需求使用 SHALL／MUST；情境採 `#### Scenario:` 與 WHEN／THEN。新能力在 delta spec 使用 `## ADDED Requirements`；變更既有能力依語意使用 MODIFIED／REMOVED Requirements。
- 每個 task 應能追溯至需求及驗證結果；完成驗證後依 OpenSpec 歸檔流程同步正式 specs。
- 後續建議能力：data-generation、quality-prediction、spc-monitoring、parameter-advice、dashboard。
- 欄位、單位、模型輸出、SPC 規則或操作範圍改動時，先更新對應規格與介面契約。
- 導入 CLI 時記錄實際 OpenSpec 版本；尚未執行初始化、驗證或歸檔前，不得宣稱已完成。

## 3. 角色與交接

| 角色 | 職責與主要交付 | 交接驗收 |
|---|---|---|
| 製程／品質負責人 | 確認產品規格、測試條件、參數範圍、取樣及 SPC 基準 | 明確標示單位、配方適用範圍及實驗假設；模擬預設值不得當成工廠標準 |
| A：Data Engineer | v2 維護與 v3 生成器；輸出三站 setpoint／actual、五點厚度、材料區段、reference、metadata 與漂移真值 | 相同 seed 可重現；120／40／40 完整卷隔離；demo Run、reference、v2 與訓練資料不交叉；漂移真值不進模型或線上 SPC |
| B：ML Engineer | v3 canonical table 與四目標模型；交付 RF／HGB、registry、metrics、manifest、支援範圍及 Heatmap 服務 | 時間與完整卷無洩漏；四個連續目標可推論；外觀不進 v3 bundle；UI 範圍不得冒充模型支援範圍 |
| C：Full-Stack Developer | 單一 Mode B 控制台、連續模擬器、Run Store、製程 SPC、Alarm、What-if 與 Heatmap | setpoint／actual 分離；站別延遲正確；Run 與訓練隔離；預測、actual、規格及 SPC 界限清楚區分 |
| 整合驗證負責人 | 維護需求對照、驗證紀錄及已知限制 | 完成資料 → 訓練 → 儀表板流程，記錄版本與重現步驟 |

交接包應包含檔案路徑、schema_version、設定、執行方式、驗證結果及限制。下游若發現契約不符，回報具體欄位／情境，不自行猜測單位或靜默改名。

## 4. 分階段完成條件

1. 規範：使用者確認本草案與模擬假設。
2. 資料：輸出可重現的七表時序資料、metadata 與漂移真值；三站以材料 MD 半開區間對齊；合成真值與模擬抽檢分離；漂移真值不進模型。
3. 模型：以完整卷及時間隔離的測試集報告每個目標的指標、基準模型、Champion／Challenger 比較及漂移區間表現；產生可信模型檔、manifest 與圖表。
4. 儀表板：完成單一 Mode B、固定製程 SPC reference、七項主要／三項進階數字調參、四目標延遲預測、Alarm 事件群、What-if、Heatmap 與 Run 紀錄。
5. 整合：以穩定資料、漂移資料、缺欄、缺值、重複檢驗、衝突旗標及單一分類樣本等情境驗證；測試標準來自需求，不以任意高分作通過條件。

## 5. 共通約定

- 技術契約以 SKILL.md 為準；正式需求納入 openspec/specs 後，兩者必須保持一致。
- 使用繁體中文說明與 UI，欄位及 Python 識別字使用英文 snake_case。
- 變更附上原因、受影響契約與驗證證據；不提交真實機密資料、憑證或未受信任的序列化模型。
- 系統提供模擬與決策輔助。UI 解鎖只控制本機模擬參數編輯，不代表產線權限；本專案初版不寫入 PLC、MES 或機台。
- 新控制台的參數調整只顯示目前／候選參數、四項連續品質預測、規格狀態、差值及限制；不顯示外觀 NG 或「當下預測良率」。
- 初版固定產品／配方為 `FCCL-DEMO-001`／`SIM-RECIPE-3.0`。產品規格、配方範圍、UI 操作範圍、模型支援範圍及 SPC 管制界限是五種不同契約，不得互相代替。
- 每次模擬 Run 只寫入 `runtime_data/testline_runs/<run_id>/`，不得自動寫入 `raw data/`、`generated_data/` 或 `artifacts/`，也不得自動觸發訓練、baseline 重估或模型升版。
- 改善資料只透過版本化、人工審核的離線週期加入下一輪訓練；不得讓模型以線上自我更新方式直接改動生產參數。

## 6. Development Logging and Traceability

### 6.1 適用範圍與執行責任

- 本節補充原第 1、2 節初次規範交付的範圍：使用者已授權建立 `docs/DEVELOPMENT_LOG.md`、`docs/DECISION_LOG.md`，並於 2026-11-02 先授權更新契約與重新生成 v2 合成資料，後續再以 `$openspec-apply-change implement-quality-model-pipeline` 明確授權本機模型 pipeline 與 Streamlit 整合。跨組正式採用及真實產線接入仍須另行確認。
- Codex 讀取本規範後，須在有實質變更、重要確認結論、測試／修復結果或階段狀態改變時，於該次工作結束前主動同步日誌。純閱讀、無新結論或無變更的操作不重複新增事件。
- 此為由 Codex 遵循指令執行的紀錄機制，沒有背景程序、CLI hook 或 Git hook；不保證捕捉其他工具或人工修改，也不代表新增 Verify 技能。
- 紀錄不取代 OpenSpec 的 proposal、specs、design、tasks；重要架構或契約改動先檢查對應規格是否需要同步，依當次授權處理，未授權的同步列為待辦。不得為記錄而自動啟動下一階段。
- 日誌寫入權限仍以當次使用者範圍為準；若範圍不含日誌或無法寫入，回報未同步項目，不宣稱已完成。已有明確日誌授權時，不重複要求批准。

### 6.2 統一紀錄與證據

- 依兩份日誌內的模板，以繁體中文、UTF-8 追加紀錄；時間採 `YYYY-MM-DD HH:mm:ss +08:00 (Asia/Taipei)`，ADR 日期採台灣日期並附決策時間。事件 ID 使用 `DEV-YYYYMMDD-NNN`，決策 ID 使用 `ADR-NNN`；先查現有最大編號，避免重複或覆用。
- 每筆開發紀錄包含時間、標題、階段、分類、Change／task／需求及驗證對應、目標、完成項目、檔案操作、實作細節、測試、錯誤修復、限制、待辦、Git Hash 及證據來源。無適用資料填「不適用」並說明；無法取得的歷史填「待補充」。
- 逐項區分「已完成」「未完成」「待驗證」「待整合」；已完成必須有相應驗證證據。測試狀態使用「通過／失敗／未執行／不適用」，記錄命令或人工檢查方式、結果及限制，不把未執行寫成通過。
- 事實、模型假設、技術建議、實際測試結果分開記載；保存來源路徑／章節、可取得的對話確認或工具結果。未確認的草案、建議與討論不得記為已批准設計。
- 歷史採追加式；更正須新增事件並引用原 ID。決策變更新增 ADR，連結前案與後繼案；舊 ADR 原文保留，其有效狀態由後續取代事件標為 Superseded。模板不算事件。
- 不抄錄密碼、API Key、Token、敏感製程資料或完整私人對話；證據僅保留必要且已去識別的摘要。

### 6.3 OpenSpec 階段觸發規則

| 階段 | 必須更新的內容 |
|---|---|
| Explore | 摘要已確認需求、重要架構結論與未解問題；一般腦力激盪不必全寫。提案或假設明確標示未批准；達重要決策門檻時記 ADR，尚待批准為 Proposed。無法讀取既有探索時標「待補充」，保留進度，不重跑 Explore。 |
| Propose | 記實際建立／修改的 Change 名稱，以及 proposal、design、specs、tasks 各實際路徑、主要需求與設計選擇、已產生／尚缺的 artifact、是否待使用者審查。尚未產生的路徑不得描述為已存在。 |
| Apply | 每完成一組任務，先依需求與證據更新對應 `tasks.md`，再追加開發紀錄，必要時追加 ADR；逐項核對規格及測試結果。未完成或未驗證的 task 不得勾選；待 A／B 整合另標待整合，不推定整合已完成。 |
| Verify | 記測試項目、執行方式、環境、資料／模型來源、通過／失敗／未執行、問題、修復與重測結果及剩餘風險。先確認 Verify 技能是否存在；缺少時仍記一般測試，不虛構技能或命令執行。 |
| Archive | 只有實際歸檔後，記歸檔時間、Change、最終範圍、限制、原路徑／歸檔路徑、正式 specs 同步結果及 DEV／ADR 對應。未歸檔或未同步須明記，不刪除歷史紀錄。 |
| Maintenance | 規範、日誌、修復與流程維護同樣記錄變更、原因及驗證；不藉此跳過 OpenSpec 需求與實作流程。 |

### 6.4 成員 C 分類與整合成熟度

| 分類 | 範圍 |
|---|---|
| C-UI | Streamlit 介面 |
| C-DATA | CSV 載入、資料驗證 |
| C-SPC | 管制圖、SPC 規則 |
| C-ALARM | 異常警報 |
| C-WHATIF | 動態調參及情境模擬 |
| C-MODEL | Random Forest API、SHAP 整合 |
| C-TEST | 測試與驗收 |
| C-INTEGRATION | 與成員 A、B 的整合及交接 |

- 每事件可選多個分類，流程維護可使用 C-INTEGRATION 並註明「流程文件」。
- 分別記錄資料來源（Mock／正式資料／未接入／不適用）、模型來源（Mock Adapter／正式模型／未接入／不適用）、真實製程驗證（未執行／已執行及證據／不適用）。混合來源依功能或測試逐項標示。
- 使用 Mock 測試成功僅代表模擬情境；正式資料接入、正式模型接入與真實產線驗證是不同里程碑，各需來源版本、介面驗證及證據，不可互相推定。

### 6.5 Git 追蹤與工作結束檢查

- Git 版本管理規劃應包含 `AGENTS.md`、`SKILL.md`、`openspec/config.yaml`、`openspec/specs/`、`openspec/changes/`（含 archive 與必要 metadata）及兩份日誌；實際納管前檢查忽略規則及敏感資料。本規則不授權 Git 初始化、Commit 或 Push。
- 無 Git repository 時只提出初始化建議；不得自動初始化、Commit、Push，或修改／刪除既有 Git 歷史。
- 尚無涵蓋本次變更的 Commit 時填「尚未提交」，不可把目前 HEAD 當成本次 Hash。後續已獲授權且實際提交後，可追加事件 ID → Commit Hash 對照；不需 amend 歷史或為取得日誌自身 Hash 反覆提交。
- 結束前核對：實際檔案變更與日誌一致、task／需求／測試證據可追溯、ADR 狀態與取代連結一致、未完成／待驗證／待整合清楚、資料與模型來源明確、Git 狀態正確且未洩漏敏感資訊。最終回報已同步的日誌及仍未能同步的原因。
- 恢復工作時先讀兩份日誌與相關 Change artifacts，核對目前檔案狀態；歷史資料不足保留「待補充」，不自行重建先前探索或自動進入 Propose／Apply。

## 7. 團隊變更建議追蹤

- 在 Explore、Propose、Apply 或其他技術討論中，Codex 發現可能改變原始 Prompt 的功能、圖表、呈現方式、跨組資料／模型介接或交付範圍的建議時，須於任務結束前新增或更新 [docs/TEAM_CHANGE_PROPOSALS.md](docs/TEAM_CHANGE_PROPOSALS.md)，沿用既有提案 ID，避免重複登錄。
- 成員 C 內部且不影響上述項目的實作細節，仍依一般 OpenSpec 流程處理；合理優化與必要工程調整不因本機制被禁止。實際阻礙可提出替代方案，註明原規格與 A／B／C 影響；只隔離受影響項目，繼續不受影響且已授權的 C 工作。
- 團隊提案預設為待討論，不等於正式規格或實作授權；C 的局部測試假設或個人技術確認，不推定為團隊決議。已有明確團隊決議才依實際證據更新狀態、討論結果及相關 OpenSpec 文件；不得自動啟動 Propose／Apply。
- 提案按文件模板記錄來源與影響；ChatGPT 建議僅依使用者實際提供的內容登錄，不推測其他對話。既有同名文件先讀取整合，不覆蓋歷史；狀態變動保留日期、依據與結果。
- 三份文件分工：TEAM_CHANGE_PROPOSALS.md 保存待團隊討論的變更及其決議；DEVELOPMENT_LOG.md 保存實際活動與驗證；DECISION_LOG.md 保存技術決策及批准範圍，使用 ID 互相引用而不複製整份內容。未確認提案不得在 ADR 中標為 Accepted；提案追蹤機制本身的批准不批准個別提案。
- 恢復工作及結束檢查時一併核對團隊提案；未來 Git 納管規劃納入此文件，本條不授權 Git 初始化、Commit 或 Push。
