# Design

## Context

版本註記（2026-11-02）：以下 C1～C5 架構描述是本案 Propose 當時的基準；磁碟目前已含 6／12 的部分 C6 Apply 及 Matplotlib 依賴，未結案。本次只修改文件，不回退程式／任務／日誌，暫停 Apply。D9 補充組長 main `058dfa35` 新版差異，對來源語意／availability／manifest 的補充優先於 D1／D4／D6 的舊單表假設；D1 最低配對 3 仍僅 C 測試顯示預設。

動機與能力範圍見 [proposal.md](proposal.md)。已觀察到的 C1～C5 架構：`selected_rows(workspace)` 回傳批號／時間篩選後的正規化實測資料；loader 保留 `identity_valid`、`duplicate_record`、來源列與原始值，無效數值已標為缺值。`FEATURE_UNITS`／`TARGET_UNITS` 定義 C 內部欄位及單位。`ui/tabs.py` 的 AI 圖表只有三個占位容器。

`ModelAdapter` 目前只有 `describe`／`predict`，能力資訊含 `supports_shap`；公式 Mock 明確為 False。WorkspaceState 已保存 data／replay／what_if／model／spc，沒有圖表狀態。依賴目前是 Streamlit、pandas、numpy 與 pytest；尚無 Matplotlib 或 SHAP 計算套件。C3 純 SPC 結果供兩區共用，C5 的目前監控與固定情境分離，本案必須保留這些邊界。

## Goals / Non-Goals

**Goals:**

- 將圖表資料準備、驗證、渲染及 Session State 分層，使 C6 在沒有 A／B 交付時獨立測試。
- 以明確切片和可核對的來源識別管理圖表，不讓 What-if 候選或全域 CSV 成為隱藏輸入。
- 對缺值、常數、模型／解釋缺能力及錯誤提供局部降級；圖表測試可替換正式 Provider，預測介面保持相容。

**Non-Goals:**

- 不訓練 Random Forest、不呼叫 TreeExplainer、不計算真正 SHAP、不決定正式模型特徵或 NG 輸出尺度。
- 不提供回放游標、timer、背景訓練或非同步任務平台；C7 驗收真正回放，C9 驗收正式前處理／背景／模型／圖表結果。
- 不更改 A／B 程式、正式資料契約、品質政策、SPC 基準或四 Tabs 配置。VIS-03 正式解釋需求仍歸 C9；此案只在 VIS-02 驗證呈現接點。

## Decisions

### D1. Heatmap 只分析傳入的有效實測切片

新增 `c_dashboard/visualization/` 純服務，由 composition 層傳入 `selected_rows` 的副本及來源描述。純服務不取得 WorkspaceState、全域 CSV 或模型預測。候選欄位沿用 C schema allowlist；特徵為 11 項製程／環境數值欄，目標為五項品質欄，MD／TD 分開。預設顯示存在的特徵與五個目標；缺目標保留不可計算狀態，使用者可縮小選取。

先排除 `identity_valid=False`／重複列，保留排除數，再逐特徵－目標以有限且有效實測值作 pairwise Pearson；不作全表 complete-case、不填補、不擅自聚合或累加同子組試片。常數／無變異、外觀只有單類別與 n 不足回報不同原因。初版設定 `c-visualization-v1`、最低配對數 3，屬可配置 C 顯示測試預設，非正式取樣或統計顯著門檻。外觀 0／1 的 Pearson 僅作描述性關聯；不報 p-value，不將多試片資料列當成獨立製程條件數。

結果包含未四捨五入 r、每格 n／排除數／原因、分析母數、欄位／單位及完整來源。所有配對均從同一有界輸入取得。使用現有 normal Mock 時，多個製程欄為常數，因此正常顯示 N/A；環境欄可有變異。另以 C6 專用小型手算 fixtures 驗收，無須改 A 生成器或原 C2 fixtures。

考慮過只呼叫全 DataFrame 的 corr：容易把識別、預測及常數／缺值狀態混入且無逐格追溯，故採獨立結果資料結構。

### D2. Heatmap 與 SHAP 有各自可尋得的區域

保留四個外層 Tabs。AI 圖表 Tab 包含獨立 Heatmap 區，以及同一 SHAP 容器的 Summary／Dependence 切換，兩種原始名稱始終可尋得。Heatmap 採特徵／目標多選；SHAP 採五目標選單與特徵選單，Summary 不依賴單一特徵，Dependence 使用目前特徵。不存在／不受支援的選項顯示原因，不讓模型不可用移除圖表入口。

Heatmap 選的是原始正規化製程欄；SHAP 特徵選單則以 Provider 宣告的解釋特徵域為準，無解釋能力時以 C 欄位作停留選項並標示待整合。C9 允許由 B 前處理產生不同名稱／順序的特徵，再由正式轉接層明確映射到標準請求，不把 C 的 11 個原始欄位硬編成 B 的模型特徵契約。

使用現有 native Vega-Lite 表達 Heatmap 與 payload 圖形；不增加外層頁面。Heatmap 固定色階 −1～1，格子顯示簡短數值或 N/A，tooltip／對照表顯示 n、排除數與原因；標籤帶單位，預測不混入實測圖。SHAP 軸標明 Provider 宣告的尺度，不能一律寫成機率。

將三張圖改成其他圖型或只交付特徵重要性 bar 會改原承諾，故不採用。Summary payload renderer 採每特徵的貢獻分布散點、以特徵值著色；Dependence 採原特徵值對該特徵貢獻的散點。這是對已給資料的繪製，不是計算 SHAP。

### D3. 加可選解釋 Port，保持既有預測介面不變

新增 `c_dashboard/adapters/explanations.py` 的 C 內部可選 Protocol 與不可用 Provider；不新增 ModelAdapter 的必備方法，不改公式 Mock 的 `supports_shap=False`。composition 層明確注入 Provider，先檢查目前模型能力及 Provider 來源是否匹配；無 Provider／能力時不呼叫解釋，保持 C5 預測運作。能力旗標為 True 仍需實際、有效的解釋回應，不能單憑旗標展示結果。

這是 C 的轉接邊界，不要求 B 採此結構。C9 會把 B 的實際 API、前處理及特徵輸出映射到它，或在另案依已核對契約演進。A／B 正式欄位、單位、特徵順序、NG 類別／尺度與 SHAP 背景仍按 TCP-004／C9 確認。本次未發現需改團隊需求的衝突，無新增 TCP。

將 explain 強加為現有 ModelAdapter 必備方法會破壞舊替身與預測路徑，故採獨立可選 Port。

### D4. C 內部解釋請求與回應的驗證

以新 types 保存下列 envelope；實際型別名稱可在 Apply 依模組慣例落實，語意須保留：

| 方向 | 必要內容與驗證 |
|---|---|
| 請求上下文 | 來源／映射版本、篩選／截止、實際樣本 IDs、feature names／units／values、目標、圖型、Dependence 特徵、模型及前處理版本、資料摘要雜湊 |
| 回應來源 | request key、model／explanation／schema version、目標／輸出單位、尺度、背景來源說明、測試或正式來源類型；必須與請求匹配 |
| 結構化 payload | sample IDs 長度 N 且順序與請求一致，唯一 feature names 長度 F，feature values 與貢獻值皆 N×F、有限數值；base values 為 N 或明確標記可廣播的 scalar，沒有靜默 reshape／截斷 |
| 分類輸出 | class labels 與每個輸出索引的明確對應；以標籤 1 選 NG，即使順序為 [1, 0] 也不可固定取第二項；缺標籤／未知尺度拒絕 |
| 圖形回應 | 受支援的記憶體 Figure 加相同來源／圖型／目標／尺度／樣本及特徵中繼資料；無包裝或不匹配圖形不得顯示為目前結果 |

原始模型張量 layout 由 Provider 正規化，renderer 只接受明確單目標／單類別的標準 payload。回歸貢獻輸出單位與目標對齊；分類保留宣告的 probability／raw margin 等尺度，不推測或自行做 sigmoid。特徵值與 SHAP 值單位分別標示。對非有限值、缺 base value、重複／錯序 ID、缺特徵、模型版本不符及 unsupported type 提供結構化原因。

Figure 的內容無法只憑 metadata 證明是真正 SHAP；C6 僅驗證包裝、呈現與錯誤，C9 必須與 B 的實際輸出／參考結果比對。C6 不測真正 SHAP 加法性或模型正確性，不宣稱正式整合完成。

### D5. 測試圖形與真正解釋明確隔離

新增小型、固定數值且明確標為 `render-test` 的 C6 test fixtures；以專用測試 Provider／AppTest 注入，匹配測試模型描述，不將公式 Mock 改成有解釋能力。一般 App 的預設 Provider 仍不可用，沒有自動顯示假 SHAP 或靜默回退測試圖的路徑。整個測試圖區標示「介面測試資料，非真正 SHAP」，來源／模型版本也保留測試標記。

結構化 payload renderer 使用 native chart spec；Figure 路徑先支援受信任記憶體 Matplotlib Figure，於 Apply 鎖定相容依賴及更新 requirements.in／lock。其他 Figure 類型先回報不支援，C9 可依 B 實際工具映射，不強制 B 更換繪圖工具。Figure 在成功或例外後皆釋放，不呼叫 show、不快取活 Figure；測試反覆渲染後無殘留 figure。CSV 上傳不增加任意圖形或模型反序列化入口。

可重現的 Renderer 替身比 C 訓練示範 RF 或產生隨機 SHAP 更符合 ADR-007；後兩者不採用。

### D6. 圖表狀態與來源 Key 獨立管理

WorkspaceState 新增獨立 VisualizationState，保存 Heatmap 欄位、SHAP 圖型／目標／特徵，以及每類結果的狀態、request key、結果／原因。UI widget key 只作互動入口，持久選項存業務狀態，避免切換條件式 widgets 清除特徵選取。

request key 包含實際切片的 IDs／特徵／實測值內容摘要、來源／映射／篩選、選項、算法／設定版本，以及 SHAP 的模型／前處理／Provider／輸出尺度與測試模式。不能只用檔名或 sample count。What-if 候選不進 Heatmap key。Heatmap 使用全篩選有效實測，不抽樣；解釋呈現的測試資料可有明確樣本上限，任何未來抽樣必須從傳入切片選取、固定設定並顯示方法／樣本 IDs，不能讀取完整 CSV。

計算採同步純服務與 Streamlit 計算中提示，無背景執行緒；開始新請求先標 stale／running，只有 key 匹配的結果可提交 ready。失敗標 error／unavailable 並可重試，不顯示過期圖冒充當前。資料來源／篩選成功變更時只使相依結果失效，仍有效的欄位選項可保留；失敗上傳與同源重載沿用 C2 語意。相同 key 可快取不可變資料結果，切 Tab 不做重複昂貴請求，暫時 Figure 不進 Session State。

新狀態只局部接入 `data/session.py` 的成功來源／篩選變更及 UI 組合；原 data／replay／what_if／model／spc 的重設規則不重寫。C7 再將游標及背景合法性納入 key，不在本案假裝交付回放。

### D7. 模組落點與依賴順序

| 預計新增／局部修改 | 責任 |
|---|---|
| `visualization/types.py`、`config.py` | 圖表請求／結果、來源、狀態與 C 版本化顯示設定 |
| `visualization/heatmap.py` | 實測有效配對與相關性純計算 |
| `adapters/explanations.py`、`visualization/explanations.py` | 可選 Port／不可用 Provider、payload／Figure envelope 驗證 |
| `visualization/charts.py`、`controller.py` | renderer 與來源 key／狀態組合，不回讀全域資料 |
| `ui/visualization_panel.py`、`ui/tabs.py` | AI 圖表互動、標示及局部錯誤；`layout.py` 必要的明確依賴注入 |
| `state.py`、`data/session.py` | 圖表業務狀態與局部失效；保留既有相依行為 |
| C6 tests／fixtures、指南、驗收矩陣 | 手算、renderer、AppTest、來源隔離與 C1～C5 回歸證據 |

先交付 Heatmap 純資料與圖，再加入 Port／選項／能力提示及測試 renderer，最後接入狀態失效及完整回歸。原 app.py 維持入口組合，不集中分析邏輯。

### D8. 驗收與原始來源追蹤

每個實作任務包含局部測試；結案以本 Delta 的全部情境建立 `docs/C6_VISUALIZATION_ACCEPTANCE.md`（Apply 時才產生實際結果）。不以規格 strict 成功當圖表功能完成。

| 原來源與保留的後續部分 | 本 Change 對應 |
|---|---|
| 原 6.1、VIS-01/S01 | VIS-01 全部快照 Heatmap；手算 ±1／0、常數、缺值、無效識別、缺目標、單類別外觀及逐格 n |
| 原 6.2、VIS-02/S01 | VIS-02 的入口／切換與不可用提示；預設 Mock 無 SHAP，Heatmap 保持可用 |
| 原 6.3、VIS-02/S02、VIS-03 接點部分 | VIS-02 payload／Figure 渲染、形狀／類別／尺度驗證；VIS-03/S01～02 真正 B 結果仍全部由 C9 驗收 |
| 原 6.4、VIS-04/S02 快照部分 | VIS-04 來源 key、running／stale／error 及狀態保留；C7 補游標／背景與 VIS-04/S01 未來資料擾動 |
| WS-01～02／04 | 本案 dashboard-workspace 完整 MODIFIED；WS-03、CSV、SPC、品質情境主規格不改 |

純單元測試使用明確資料與替身；圖表測試檢查 native spec 的軸／色階／資料／狀態及 Figure 清理；AppTest 操作欄位、目標、特徵、圖型、來源／篩選及跨 Tab。回歸要確認原 CSV／資料問題、SPC 基準與事件、目前模型預測及固定 What-if 都不變，原 C1～C5 pytest 126 項納入完整套件。Apply 結案另跑 compileall、imports、Streamlit startup 與 OpenSpec strict；真正瀏覽器／全流程驗收仍留 C8。

### D9. 組長 v2 來源與解釋契約同步

基底為已與 ZIP 核對的 main `058dfa35c9d773acfcf949a401fc018106bd296f`；完整差異與逐項責任見 [同步報告](../../../docs/C_LEADER_ALIGNMENT.md)，組長原文見 [來源快照](../../../docs/leader-reference/main-058dfa35/README.md)。本輪沒有正式資料／模型接入。

**來源與粒度**：C 消費 A／B 提供的 canonical 投影與版本化 source profile，不在 Streamlit 實作七表 JOIN、MD 加權、重測或 pivot。新 profile 攜帶 root_roll_id／aligned_sample_id／MD 半開區間、source IDs、dataset／alignment／mapping version、label_source／label_scope／方法、五個 label_available／原因、label 可得時間及 spec version／source。C Mock 依原 profile 明確標示；缺新版旗標不使舊 fixture 自動失效。正式來源缺少必要投影／可用性宣告則只降級相依分析，不假設全可用。

**Heatmap**：仍五目標 pairwise Pearson，只在可相容的來源／scope／方法／版本群內分析。正式區段標籤須該目標 availability 通過；availability=0 即使非空也排除。roll qualification 不擴展到區段；旗標衝突、未決重測／對齊問題依 A／B 輸出的逐目標原因呈現。`synthetic_ground_truth` 可作獨立、明示合成真值的示範分析，不與 `simulated_inspection` 或真實量測混算；前者無 inspection availability 旗標時須有其明確 source profile／有效性宣告，不自動套抽檢規則。保留逐格 n／排除原因與其他可用目標，不把標籤可用旗標當模型輸入。既有 loader 尚未保留新 metadata，後續 C6 以新增內部投影型別與明確測試 fixture 驗證，正式 loader／A／B 映射整合留 C9，不讓現存 raw 值繞過驗證。

**模型與解釋**：label availability、prediction availability、explanation availability 分開。沒有某實測標籤仍可能可預測／解釋；目標模型不可用／缺能力／尺度不明則只該目標 SHAP 不可用。C6 測試 Provider 用 render-test manifest，包含 manifest ID 或 hash、model source/type/version、schema／feature／preprocessing／label／spec／dataset versions、目標單位／支援狀態、classes／輸出尺度及背景來源。與 envelope、目前選定模型及來源相容性宣告交叉核對；缺失或不符不顯示舊圖，不自行猜特徵／尺度。資料版本不同本身不代表模型不可用，應依 manifest 宣告的相容範圍判定，不能強求監控資料 hash 等於訓練 hash。正式 manifest 字段與序列化 layout 由 C9 adapter 明確映射，不新增 B 必備 C API。

外觀依標籤 1 的實際 class mapping 選輸出，不固定第 2 類；真實 NG 機率來自正式分類模型，C5 未校準 risk 分數不是替代品。SHAP 若宣告 raw margin／log odds，保留該尺度而非轉機率；regression 使用相符目標單位。缺規格僅使允收判定不可用，不應阻止其餘有效相關性或模型解釋。spec pass／overall pass／漂移真值不進 feature allowlist。

**失效與測試**：來源 key 再包含實際切片中 availability／source／scope／method／label/spec/alignment versions 與原因，及解釋 manifest 身分／相容性設定，避免只改旗標或換 manifest 仍顯示舊圖。D6 有界資料與選區隔離不變。原 28 Scenario 內增加「非空但 unavailable」、「roll／segment」、「真值／抽檢」、「同樣數值但 metadata 改變」、「manifest 不符」、「缺一目標解釋但其他功能可用」測試；新增差異驗證在 tasks 4.2／4.3 統一追蹤，前六勾選不代表這些新增條件已通過。

**未決及界線**：SKILL／metadata coverage=0.98 與 design=0.99、壓合錨點與 inspection 錨點、最新重測取代與不覆蓋原測互相不一致；舊 design 的欄名／方法也與實際 v2 不同。C 顯示「跨組待確認」，不在 UI 選定數值／聚合／標籤。維持三圖、固定 What-if、產品規格／SPC／預測分離及不新增預測良率；C7 回放、C9 真正 SHAP 及正式資料轉接仍未交付。

## Risks / Trade-offs

- [重複製程設定或時間漂移造成表面高相關] → 保留來源／篩選／逐格 n、不作顯著性或因果推論；不改原始採樣或強制 A 聚合。
- [常數欄讓 Mock Heatmap 看似空白] → 逐格顯示 N/A 原因，使用獨立手算 fixture 驗證算法，不偽造變異。
- [測試圖被誤認正式 SHAP] → 預設 Provider 無解釋，測試注入獨立且整區標示；C9 結果參考核對仍必要。
- [模型能預測但不能解釋] → 可選 Port／逐目標能力降級，原 Prediction API 保持不變。
- [舊圖／Figure 長駐造成誤判或資源累積] → 完整來源 key、局部狀態、只快取資料、Figure finally 清理及反覆渲染測試。

## Migration Plan

本階段只有規劃。Apply 新增預設未載入的圖表狀態，對同工作階段原有狀態使用缺省初始化；只接入 AI 圖表 Tab 及成功載入／篩選的結果失效。若回退，移除新增 UI／Provider 組合並恢復原占位；不需遷移 CSV、模型 artifact 或固定 SPC 基準。

## Deferred integration

C9 依 B 實際交付確認模型／前處理版本、特徵順序與單位、各目標／NG 類別、SHAP 輸出 layout／尺度、背景來源及參考圖形；C7 確認回放可見前綴與合法背景。這些是已保留的跨組／後續驗收，不阻礙 C6 的 Mock／renderer 獨立交付，也不是本輪新批准的正式契約。


本輪 Apply 結案註記（2026-11-02）：前文 6／12／暫停是文件同步當輪狀態；續作授權後已依 D9 完成局部功能及新版差異驗收，最終 204 passed，原 C1～C5 回歸 126。詳見 [28 情境證據](../../../docs/C6_VISUALIZATION_ACCEPTANCE.md) 及 tasks；未 Archive／同步主 specs，不表示真正 SHAP／正式 A／B 整合完成。
