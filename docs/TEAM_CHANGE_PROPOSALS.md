# FCCL 團隊變更建議追蹤

本文件依 [AGENTS.md](../AGENTS.md) 第 7 節維護，供成員 C 完成工作後與 A／B 共同討論。原始 Prompt 已經團隊討論；本文件中的建議不是已批准需求，也不直接改寫 [SKILL.md](../SKILL.md) 或 OpenSpec 正式規格。

## 紀錄與決議原則

- 登錄會影響原始功能、圖表、呈現方式、跨組資料／模型契約或交付範圍的建議；不影響這些項目的 C 內部實作細節，依一般 OpenSpec 流程處理。
- 不禁止合理優化或必要工程調整。遇到阻礙時記錄替代方案、影響及可繼續的工作；待討論提案不阻擋其他不受影響且已授權的 C 工作，也不等同可以先更改 A／B 契約。
- 新提案使用不重複的 `TCP-NNN`，先查最大編號；既有同主題提案更新原 ID，保留狀態歷程，不刪改先前討論證據。模板不算提案。
- 日期採 Asia/Taipei。來源使用 Codex／ChatGPT／組員，並保留實際可取得的對話或文件依據；使用者要求登錄的行為與原技術建議來源分開標示。ChatGPT 來源只記使用者實際提供的資料，不假設不可見對話內容。
- 建議優先級：高＝會影響正確性或近期跨組整合，應優先釐清；中＝有設計／呈現價值，可排入討論；低＝可延後。優先級不是批准或停止工作的指令。
- 決策狀態：待團隊討論／討論中／團隊同意／團隊否決／暫緩。只有明確團隊決議才能標記同意或否決；附決議日期、來源、適用範圍與條件，不將單一成員的局部選擇推定為全隊同意。
- 已有團隊討論、但內容尚未完整移交的事項，可標示「既有團隊討論待補齊／跨組整合待確認」作為交接狀態；此狀態不表示團隊未討論，也不代表登錄者已取得完整決議或可以制定正式數值。具體內容依實際提供資料補齊。
- 決議後更新原提案的結果與狀態歷程，連結實際存在的 OpenSpec Change／spec／design／task；尚無文件則寫「尚未建立，待後續授權」，不得虛構路徑或自動進入下一階段。實作與驗證是否完成另由開發日誌及 OpenSpec 任務追蹤。
- 文件分工：本文件管理團隊變更；[DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) 管理實際活動／驗證；[DECISION_LOG.md](DECISION_LOG.md) 管理技術決策。使用 TCP／DEV／ADR ID 交叉引用，避免重複保存完整技術論述。

## 提案索引

| 提案 ID | 主題 | 建議優先級 | 決策狀態 |
|---|---|---|---|
| TCP-001 | X-bar Mock 的五試片子組與 A 正式資料契約 | 高 | 待團隊討論 |
| TCP-002 | 在原有 X-bar 之外增加 I-MR | 高 | 待團隊討論 |
| TCP-003 | 分開管理製程監測與品質抽檢資料 | 中 | 待團隊討論 |
| TCP-004 | 品質規格、NG 門檻、多目標推薦與模型介接交接 | 高（正式整合前） | 既有團隊討論待補齊／跨組整合待確認 |

## 統一格式（模板，非實際提案）

```markdown
## TCP-NNN｜提案主題

- 提案 ID：TCP-NNN
- 日期：YYYY-MM-DD (Asia/Taipei)
- 提案來源：Codex／ChatGPT／組員；實際來源及登錄依據
- 原始 Prompt 的對應需求：
- 建議修改或新增的內容：
- 提出原因與技術依據：
- 對 A、B、C 的影響：分別列出；不確定處標待確認
- 對 GitHub 整合及簡報呈現的影響：
- 不修改時可能存在的問題：
- 建議優先級：高／中／低；理由
- 決策狀態：待團隊討論
- 團隊討論結果：尚未提供，不推定同意
- 相關 OpenSpec Change：實際連結；尚無則註明
- 關聯紀錄：DEV／ADR／其他 TCP
- 狀態歷程：日期、狀態及證據
```

## TCP-001｜X-bar Mock 的五試片子組與 A 正式資料契約

- 提案 ID：TCP-001
- 日期：2026-11-01 (Asia/Taipei)
- 提案來源：Codex／組員。Codex 前次 Explore 比較合理子組與單筆量測；使用者本輪明確要求登錄此議題。未取得額外 ChatGPT 或其他組員對話。
- 原始 Prompt 的對應需求：A 生成時序 Mock CSV，包含各製程與品質目標；C 顯示 X-bar 品質管制圖。原始 Prompt 未指定每次五個獨立試片、子組 ID 或正式取樣契約。
- 建議修改或新增的內容：討論是否為 X-bar 建立「同次取樣、短時間及相近條件下每組五個獨立試片」的 Mock 測試情境；五筆只是候選測試設計，不是 X-bar 的唯一組數要求。另分開決定這僅供 C 的測試，或需要 A 正式輸出子組／試片識別與取樣資訊；未決議前不要求 A 改契約。不將同一試片重測或五個不同時間點直接當成合理子組。
- 提出原因與技術依據：X-bar 需有合理子組才能估計組內變異；現有 SKILL.md 第 6 節的 n=5 為待確認草案，不是原始團隊已批准取樣方式。[Minitab 合理子組說明](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/control-charts/how-to/variables-charts-for-subgroups/xbar-r-chart/before-you-start/data-considerations/)及 ADR-003 已記錄此限制；尚無現場取樣證據。
- 對 A、B、C 的影響：A——若僅 C 測試，無正式契約變動；若採正式子組輸出，需共同確認新增欄位與資料粒度。B——若同一製程區段展開為多試片，需避免重複特徵造成評估洩漏或樣本權重改變，確認預測粒度。C——需子組驗證、未完成子組顯示及明確標示 Mock 假設；回放只能使用已可見樣本。
- 對 GitHub 整合及簡報呈現的影響：若正式契約改動，需同步 schema／fixture／介面文件與各成員分支；簡報需說明五試片是模擬假設或正式採樣決議，不把測試資料當現場證據。尚未建立 Git repository，不涉及本次提交。
- 不修改時可能存在的問題：若仍只按連續五列硬分組，可能混入時間變化、掩蓋偏移或錯估界限；若實際已有適當子組，則未必需要修改，需先確認。
- 建議優先級：高；影響 X-bar 正確性與 A／B／C 資料粒度，應在正式介接前釐清。
- 決策狀態：待團隊討論。
- 團隊討論結果：尚未提供；未批准五試片設計或任何 A 正式資料契約變更。
- 相關 OpenSpec Change：尚未建立；目前 changes／specs 均為空，不建立提案 artifacts。
- 關聯紀錄：ADR-003、DEV-20261101-003；本次登錄見 DEV-20261101-004。與 TCP-002、TCP-003 有關，但不互為批准前提。
- 狀態歷程：2026-11-01——依本輪登錄要求建立，待團隊討論；登錄不代表採用。
- 局部確認補充（2026-11-01 20:20:27 +08:00）：使用者允許 C 為 X-bar 使用同次多個獨立試片的專用 Mock，可設定固定子組大小，但未指定為五筆；僅批准 C 的測試路徑，不要求 A 採用。正式格式、實際子組大小與頻率、B 模型輸入仍待跨組協調。本提案維持待團隊討論，無團隊決議；見 ADR-005、DEV-20261101-005。
- 規劃關聯補充（2026-11-01 21:08:26 +08:00）：登錄當時尚未有 Change；目前已建立 [fccl-streamlit-dashboard](../openspec/changes/fccl-streamlit-dashboard/proposal.md)，[design.md](../openspec/changes/fccl-streamlit-dashboard/design.md) D4／D5 使用配置化 C Mock，正式粒度／子組驗證在 [tasks.md](../openspec/changes/fccl-streamlit-dashboard/tasks.md) 9.1。此為規劃連結，不是團隊批准；本提案仍待團隊討論。

## TCP-002｜在原有 X-bar 之外增加 I-MR

- 提案 ID：TCP-002
- 日期：2026-11-01 (Asia/Taipei)
- 提案來源：Codex／組員。前次 Explore 由 Codex 提出 I-MR 比較；使用者要求評估單筆量測替代方案，並於本輪要求列為待討論提案。未取得額外 ChatGPT 對話。
- 原始 Prompt 的對應需求：C 的 SPC 面板明確要求 X-bar，另有趨勢警報；原始 Prompt 未列 I-MR。
- 建議修改或新增的內容：討論是否在原有 X-bar 之外增加 I-MR 選項，用於每時間點一筆有效量測、無合理子組的情境；採用條件、顯示方式及警報規則另議。不默默以 I-MR 取代原定 X-bar，也不在缺乏子組時製造 X-bar 結果。
- 提出原因與技術依據：I-MR 以個別量測與相鄰 moving range 監控水準與變動，可避免為畫圖人工湊組；需評估自相關、分布、有效相鄰點及穩定基準。[NIST Individuals Control Charts](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm)與[Minitab I-MR 資料條件](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/control-charts/how-to/variables-charts-for-individuals/i-mr-chart/before-you-start/data-considerations/)為前輪查核來源，非現場驗證。此方案在 ADR-003 仍為 Proposed。
- 對 A、B、C 的影響：A——需確認單值是獨立試片還是平均值、時間順序與停機／配方資訊，是否新增欄位待議。B——通常無須因繪圖新增模型，但需對齊輸出粒度，不能把預測值當實測 I 圖。C——新增 I／MR 圖、適用性檢查、基準設定與規則驗證；工作量與展示範圍增加。
- 對 GitHub 整合及簡報呈現的影響：新增 SPC 功能與測試需介面及版本協調；簡報需交代原定 X-bar 與新增 I-MR 的適用條件，避免讓組員以為既有需求被替換。本次不新增分支或提交。
- 不修改時可能存在的問題：只有單筆量測時，可能無法提供適當的正式管制圖；若強行分組可能誤判。可以保留歷史趨勢並提示無適用子組，不能把新增 I-MR 視為唯一已批准解法。
- 建議優先級：高；涉及圖表交付與 SPC 適用性，需共同確認。
- 決策狀態：待團隊討論。
- 團隊討論結果：尚未提供；比較 I-MR 的要求不等於批准新增圖表或修改交付範圍。
- 相關 OpenSpec Change：尚未建立；未修改現有 SPC 契約，待團隊決議及後續授權再連結正式文件。
- 關聯紀錄：ADR-003、DEV-20261101-003、DEV-20261101-004；TCP-001。
- 狀態歷程：2026-11-01——待團隊討論；保留原定 X-bar 需求及取樣結構未決狀態。
- 局部確認補充（2026-11-01 20:20:27 +08:00）：C 的 X-bar 專用 Mock 路徑已確認，但全專案取樣結構仍未定；使用者要求保留原始 X-bar，正式資料不適用時記錄限制與替代建議，不直接改成 I-MR。本提案仍待團隊討論，未批准新增／替換圖種；見 ADR-005。
- 規劃關聯補充（2026-11-01 21:08:26 +08:00）：目前 [SPC delta spec](../openspec/changes/fccl-streamlit-dashboard/specs/spc-monitoring/spec.md) 保留 X-bar 及不適用提示，[design.md](../openspec/changes/fccl-streamlit-dashboard/design.md) 不新增 I-MR。此連結補充登錄時尚無 Change 的現況，未批准本提案，仍待團隊討論。

## TCP-003｜分開管理製程監測與品質抽檢資料

- 提案 ID：TCP-003
- 日期：2026-11-01 (Asia/Taipei)
- 提案來源：組員（使用者本輪要求登錄此議題）；下列資料流影響分析由 Codex 補充，非已存在的其他對話或團隊決議。未取得額外 ChatGPT 對話。
- 原始 Prompt 的對應需求：A 的時序資料同時包含製程、環境與品質目標；B 讀取模擬資料訓練；C 透過 CSV 呈現監控與預測。原始 Prompt 未要求將資料拆成不同表／檔案。
- 建議修改或新增的內容：討論製程監測與品質抽檢是否採不同邏輯資料集，必要時才拆檔；以批次／材料區段／試片等明確關聯鍵連接，區分製程觀測時間、抽樣時間與品質結果可得時間。實際欄位名稱、檔案數、join 規則與保留單一 CSV 相容方式均待協議。本項不等同已確認的「實測與 What-if 分離」。
- 提出原因與技術依據：工程上製程監測與品質抽檢可能頻率不同，抽檢結果也可能延後取得；若確有此情境，單列同步資料可能無法準確表達資料可得性，回放也可能提前看見品質結果。這是待確認的情境假設，沒有實際採樣頻率或檢驗延遲證據；目前 SKILL.md 第 2 節仍以完成後對齊的一列紀錄為草案契約。
- 對 A、B、C 的影響：A——可能需分開生成資料與關聯鍵，定義一對多關係、時間與缺測；B——需明確特徵／標籤對齊與訓練粒度，避免 join 擴增及未來標籤洩漏；C——可能增加多來源載入、關聯驗證、延遲結果及回放可見性處理。三者皆未被要求在本次修改程式。
- 對 GitHub 整合及簡報呈現的影響：若採用，需共同版本化 schema、資料字典與相容層，避免各分支使用不同欄位；簡報新增製程流／抽檢流與預測資料流說明。若只在 C 內部分視圖且維持既有契約，跨組影響較小，但仍需說明展示語意。本次不執行 Git 操作。
- 不修改時可能存在的問題：若確有不同頻率或延遲，可能重複品質標籤、誤認每時點都有實測、提早取得未來檢驗資訊；若原始單表已能明確表達且符合實際取樣，則可能不需拆分，避免額外整合成本。
- 建議優先級：中；先釐清實際資料粒度與可得時間；若確認影響回放正確性，再依證據調整優先級。
- 決策狀態：待團隊討論。
- 團隊討論結果：尚未提供；未批准拆表／拆檔、新關聯鍵或變更 A／B 的輸入輸出契約。
- 相關 OpenSpec Change：尚未建立；待決議後，在獲授權的規格流程中連結資料生成、模型對齊與儀表板相關文件。
- 關聯紀錄：DEV-20261101-004；ADR-002 的禁止未來觀測要求僅是需要考量的既有約束，不代表批准資料拆分；TCP-001、TCP-002。
- 狀態歷程：2026-11-01——依本輪指定建立，待團隊討論。
- 局部確認補充（2026-11-01 20:20:27 +08:00）：使用者要求 C 的載入架構保留正式介接彈性，不把 Mock 條件施加所有來源；這不等於批准製程／品質資料拆表或拆檔。本提案維持待團隊討論，未改 A／B 契約；見 ADR-005。
- 規劃關聯補充（2026-11-01 21:08:26 +08:00）：目前 [CSV delta spec](../openspec/changes/fccl-streamlit-dashboard/specs/csv-ingestion/spec.md) 與 [design.md](../openspec/changes/fccl-streamlit-dashboard/design.md) D4 定義 C 來源轉接及可得時間隔離，正式資料結構在 tasks 9.1 核對；不批准 A 拆表／拆檔。此為新增 Change 後的連結補充，狀態仍待團隊討論。

## TCP-004｜品質規格、NG 門檻、多目標推薦與模型介接交接

- 提案 ID：TCP-004
- 日期：2026-11-01 (Asia/Taipei)
- 提案來源：組員（使用者本輪說明既有團隊討論及要求登錄交接事項）；Codex 上輪「全部目標符合允收條件才推薦」僅為未批准建議，不當成團隊原共識。沒有取得額外 ChatGPT 或組員對話。
- 原始 Prompt 的對應需求：四大品質預測、AI Alarm、具體線速等調參建議、What-if 前後比較，以及模型／SHAP／Heatmap 與 C 儀表板整合；尺寸安定性包含 MD／TD，合計五個預測目標欄位。
- 建議修改或新增的內容：目前不改正式品質或推薦規則，先登錄下列交接清單。四大品質的正式允收規格與來源；外觀 NG 風險門檻；多目標互相衝突時的推薦原則；正式模型輸出與 C 的 What-if／Alarm 介接；模擬調參改善不代表真實製程因果。具體決議、數值、版本、條件與文件來源待依團隊提供內容補齊，不臆造。C 現階段以 Mock Adapter 與可配置測試設定繼續完成 Alarm、具體調參建議、What-if 比較與圖表；測試規則不升格為正式規格。
- 提出原因與技術依據：使用者明確說明品質規範先前已有團隊討論，只是尚未完整寫入原始 Prompt；本項是交接與整合紀錄，不代表團隊缺乏討論。將設定與呈現分離，可先驗證 C 的流程與畫面，再接入有來源的正式設定及模型。沒有真實資料或正式模型驗證證據，不把 Mock 改善解讀為製程因果。
- 對 A、B、C 的影響：A——後續依既有團隊內容確認正式欄位、單位及資料語意，本次不要求修改生成器。B——後續共同核對目標、輸出格式、風險語意及 SHAP 能力，不要求採用 C 的公式或重訓。C——保留配置與正式 Adapter 接點，完成原定功能並標示 Mock 來源；不等待正式規格才推進介面，也不把缺乏交接資料等同正式需求被取消。
- 對 GitHub 整合及簡報呈現的影響：正式整合時需以團隊提供的來源與版本對齊設定、模型輸出和測試證據；簡報區分 C Mock 功能展示、正式模型整合及真實製程驗證。未執行 Git 初始化、Commit 或 Push，不虛構現有分支／PR。
- 不修改時可能存在的問題：若不保存交接資訊，C 測試規則可能被誤認正式品質規範，或因等待完整規格而不必要地停止 UI 工作；不表示團隊既有規則本身有問題，也不主張一定需要更改團隊決議。
- 建議優先級：高（正式整合前）；先列交接清單，不阻擋當前 C 介面與 Mock 測試工作。
- 決策狀態：既有團隊討論待補齊／跨組整合待確認。
- 團隊討論結果：使用者確認先前已討論；具體允收規格、NG 門檻、取捨原則及來源尚未提供至本輪可見內容，待交接補齊。不記為「團隊尚未討論」，也不推定 Codex 上輪的推薦條件已獲同意。
- 相關 OpenSpec Change：尚未建立；changes／specs 目前為空。後續依實際授權連結文件，不為此記錄直接進入 Propose／Apply。
- 關聯紀錄：ADR-009、DEV-20261101-009；既有 Mock 能力見 ADR-007，固定區段見 ADR-008。與 TCP-001／002／003 範圍不同，不合併或改變它們的待團隊討論狀態。
- 狀態歷程：2026-11-01 20:43:18 +08:00——查無 TCP-004 或同題提案，依使用者要求首次登錄；狀態為既有團隊討論待補齊／跨組整合待確認，並非新增正式品質決議。
- 規劃關聯補充（2026-11-01 21:08:26 +08:00）：目前 [品質情境 delta spec](../openspec/changes/fccl-streamlit-dashboard/specs/quality-scenarios/spec.md)、[AI 圖表 delta spec](../openspec/changes/fccl-streamlit-dashboard/specs/quality-visualization/spec.md) 與 [tasks.md](../openspec/changes/fccl-streamlit-dashboard/tasks.md) C9 已列正式交接驗收；C1～C8 以 Mock／測試配置推進。此為登錄後新建規劃的關聯，不表示正式規格或模型已交付，維持既有團隊討論待補齊／跨組整合待確認。

## 管理拆分補充｜2026-11-01 22:23:19 +08:00

本節只更新規劃歸屬與歷史連結，不新增提案、不改既有討論結果或狀態。使用者已要求 C 各可驗收功能獨立 Change；原 C1～C9 規劃已完整凍結，見 [Roadmap 與舊路徑對照](CHANGE_ROADMAP.md)、[完整快照](change-baselines/fccl-streamlit-dashboard-c1-c9/README.md)，ADR-015／DEV-20261101-014。上文「規劃關聯補充」所指的是拆分前狀態；移出 active Change 的四份 spec 以快照回查。

| 提案 | 保留狀態 | 後續規劃歸屬（尚未建立 active Change） |
|---|---|---|
| TCP-001 | 待團隊討論 | [C3 Mock 子組／SPC](change-plans/fccl-spc-monitoring.md)、[C9 正式粒度／契約](change-plans/fccl-ab-integration.md) |
| TCP-002 | 待團隊討論 | [C3 保留原 X-bar 與限制](change-plans/fccl-spc-monitoring.md)、[C9 正式適用性](change-plans/fccl-ab-integration.md)；未批准新增 I-MR |
| TCP-003 | 待團隊討論 | [C7 可得時間／回放](change-plans/fccl-csv-replay.md)、[C9 正式來源確認](change-plans/fccl-ab-integration.md)；不批准 A 拆表／拆檔 |
| TCP-004 | 既有團隊討論待補齊／跨組整合待確認 | [C4＋C5 測試配置](change-plans/fccl-what-if-mock-ai.md)、[C6 圖形接點](change-plans/fccl-quality-visualization.md)、[C9 正式規格／模型／SHAP](change-plans/fccl-ab-integration.md) |

C1＋C2 僅交付基礎 UI／資料載入；本案可獨立審查歸檔，不代表本表任何跨組議題已批准、整合或取消。


## C3 規劃關聯補充｜2026-11-01 22:40:06 +08:00

目前已建立 [fccl-spc-monitoring Propose](../openspec/changes/fccl-spc-monitoring/proposal.md)，[design](../openspec/changes/fccl-spc-monitoring/design.md) D2／D3 與 [SPC delta](../openspec/changes/fccl-spc-monitoring/specs/spc-monitoring/spec.md) 對應 TCP-001 的 C Mock／正式契約隔離、TCP-002 的保留 X-bar／不新增 I-MR，以及 TCP-003 的來源相容性／未來可得時間。正式取樣與資料流仍留 C9；TCP-004 品質規格／模型交接不在 C3 制定。

此為關聯補充，沒有新跨組技術變更提案或團隊決議；TCP-001～003 仍待團隊討論，TCP-004 仍為既有團隊討論待補齊／跨組整合待確認。C3 只 Propose，D2～D6 具體內部方案在 ADR-016 為 Proposed，不視作全隊契約批准。


## TCP-004 C4＋C5 規劃關聯補充｜2026-11-01 23:36:21 +08:00

已建立 [fccl-what-if-mock-ai Propose](../openspec/changes/fccl-what-if-mock-ai/proposal.md) 與 [delta specs](../openspec/changes/fccl-what-if-mock-ai/specs/quality-scenarios/spec.md)。該 Change 僅以可配置 C 測試條件驗證展示、Alarm 與候選建議；不填正式允收數值／外觀門檻／多目標政策，不宣稱團隊未曾討論，也不改動 A／B 契約。正式交接待補齊及跨組整合待確認的 TCP-004 狀態與原正文均維持不變；Q-06／正式模型介接留 C9。

