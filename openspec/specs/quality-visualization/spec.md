# quality-visualization Specification

## Purpose

以可追溯的實測相關性與模型解釋呈現接點支援成員 C 的品質分析畫面，讓正式模型尚未交付時仍可驗收 Heatmap、圖表互動及資料驗證，並清楚區分測試圖形、真正模型解釋與後續整合能力。

## Requirements

### Requirement: VIS-01 可追溯 Heatmap

系統 SHALL 使用目前載入且符合批號／時間篩選的有效實測資料，提供製程／環境數值特徵對五個品質目標的 Pearson Heatmap，允許欄位選取並保留 MD／TD 各自標籤。圖表 MUST 標示欄名／單位、方法、資料範圍、觀測截止與每格有效配對數；缺值、無變異或有效配對不足須說明不可計算，不能偽造零相關、補造量測或將相關性解讀為因果。

系統 SHALL 消費版本化來源投影而非在 C 端重建七表。正式區段標籤依逐目標 availability、label source／scope、方法與版本選擇相容群；`quality_label_available` MUST NOT 代表五項皆可用。卷級結果不得展開成區段；完整 `synthetic_ground_truth` 僅可在獨立且明示合成示範的來源 profile 分析，不與抽檢／真實觀測混算。C 專用 Mock 保留明確舊 profile 相容性，不將其假設套用正式來源；所有合成資料 MUST NOT 宣稱產線實測結論。

#### Scenario: 可手算的相關係數
- **WHEN** 已載入測試 CSV，選定的製程特徵與品質目標有足夠且具變異的有效配對
- **THEN** Heatmap 顯示可與手算對照的 Pearson 值、固定 −1～1 色階、目標與特徵單位及有效配對數，MD／TD 與外觀 0／1 各自可辨識，相關性明示非因果

#### Scenario: 部分缺值或品質目標缺欄
- **WHEN** 某些列有缺值／非有限值／載入驗證判定的無效值，或某品質目標整欄缺失
- **THEN** 僅以該格有效配對計算並回報排除數；非空但該目標 availability=0、旗標衝突、重測歧義或 A／B 宣告不可用者亦排除並顯示原因；正式來源缺必要可用性宣告時不假設全可用。缺目標的格子顯示不可計算原因，其他有效格子仍可顯示，不用全表刪列或模型預測填補實測

#### Scenario: 常數與樣本不足
- **WHEN** 選定欄為常數、外觀只有一種類別，或有效配對低於已顯示的版本化測試最低數量
- **THEN** 對應格子顯示不可計算及原因，不以 0、極端相關或品質正常代替；樣本數僅描述有效資料列，不宣稱具有獨立樣本的推論效力

#### Scenario: 篩選與情境資料隔離
- **WHEN** 改變批號／時間篩選，或在相同實測範圍調整 What-if 候選
- **THEN** Heatmap 只分析目前傳入的實測切片，資料範圍改變才改變其結果；What-if／預測值與未傳入列不影響圖表，原始 CSV、SPC 與候選設定不被改寫

#### Scenario: 欄位選擇與無效識別
- **WHEN** 使用者選取存在的製程／環境欄及品質目標，或資料含無效識別與重複紀錄
- **THEN** 排除無效識別／已標記重複列並回報數量；依來源投影分開 roll／segment 與 synthetic_ground_truth／simulated_inspection，來源／方法／版本不相容時提示而不混算。顯示卷／材料 MD 範圍與來源版本；批號、時間索引、規格 pass、availability、隱藏漂移真值及預測欄不能作分析特徵；空選取／空篩選顯示可理解的提示，不產生空白假圖

### Requirement: VIS-02 SHAP 原定功能與能力提示

系統 MUST 保留 SHAP Summary Plot、SHAP Dependence Plot 的容器、圖型切換、五目標選擇及 Dependence 特徵選擇。解釋呈現接點 SHALL 驗證來源、版本、樣本／特徵對齊、目標／單位、分類標籤與輸出尺度。無真正解釋能力時明示待 B／C9 整合；只有明確標示的測試資料／圖形可用於介面驗收，不能由公式 Mock 輸出、係數或隨機值冒充真正 SHAP。

系統 MUST 將標籤可用性、模型逐目標預測能力及解釋能力分別呈現；缺實測標籤不直接使模型解釋失效。解釋來源 SHALL 與選定模型及版本化 manifest 的 model source/type/version、manifest ID 或 hash、schema／feature／preprocessing／label／spec／dataset versions、class mapping、輸出尺度及背景相容性一致。C6 可用明示 render-test manifest 驗證；B 的實際 manifest 欄名與真正計算仍留 C9，不要求 B 採 C 內部 API。

#### Scenario: 公式 Mock 模式
- **WHEN** 目前使用公式 Mock、未接入模型，或 Adapter 不提供解釋能力
- **THEN** 兩個原定 SHAP 圖表入口及目標／特徵選擇保持可辨識，顯示來源、能力與不可用原因及 C9 待整合狀態，不呼叫不支援的解釋方法，Heatmap／預測／SPC 仍可使用

#### Scenario: 圖型與目標特徵切換
- **WHEN** 使用者在 Summary／Dependence 間切換或變更品質目標／特徵
- **THEN** Summary 按目標呈現多特徵貢獻分布，Dependence 以所選特徵值為橫軸、該特徵貢獻為縱軸；只有與選項匹配且有效的資料可繪圖，不可用項目仍逐目標說明原因，不因該目標缺實測標籤直接阻止其他已驗證的模型解釋

#### Scenario: 測試解釋資料呈現
- **WHEN** 渲染測試注入有明確來源、目標／單位、樣本、特徵名稱／值、貢獻值、基準值、模型版本與尺度的測試回應
- **THEN** 可獨立驗證 Summary／Dependence 圖形、標籤及資料對齊，整個圖區明示「介面測試資料，非真正 SHAP」，不將測試回應設為一般公式 Mock 的解釋結果

#### Scenario: 測試圖形與資源生命週期
- **WHEN** 顯示接點收到附完整且匹配中繼資料的受支援記憶體圖形替身，或反覆切圖／遇到繪圖例外
- **THEN** 依圖型與目標嵌入並標明測試來源；過程不開啟阻塞視窗，暫時圖形於完成或失敗後釋放，未經核對的檔案／序列化物件不作解釋輸入

#### Scenario: 維度與分類尺度不符
- **WHEN** 解釋回應的樣本／特徵維度、識別順序、目標／單位、版本或尺度不符，或外觀 NG 類別標籤無法明確映射
- **THEN** 拒絕該圖並指出原因；manifest 身分／model source/type/version、特徵／前處理／標籤／規格版本及來源相容性亦須核對，缺必要宣告不得假定相容，不要求監控資料 hash 等於訓練 hash。不截斷、猜順序、固定取第二類別或自行轉成機率；NG 依標籤 1 選定輸出，probability／raw margin／log odds 明確區分，既有預測及其他有效圖表不被停用

#### Scenario: 解釋服務失敗
- **WHEN** 可選解釋接點回報不可用、部分目標不支援或拋出可處理錯誤
- **THEN** 相依 SHAP 區顯示逐目標錯誤／不可用原因、模型與 manifest 來源版本，不保留舊圖冒充新結果；缺產品規格僅使允收判定不可用，不直接禁止其餘有效解釋，並保留有效 CSV、SPC、What-if、模型預測與 Heatmap

### Requirement: VIS-04 快照圖表來源與計算狀態

系統 SHALL 區分圖表的未載入、計算中、可用、過期、不可用與錯誤狀態，以明確傳入的實測切片及匹配解釋來源產生結果。資料／映射、篩選、目標／特徵、圖型、模型／解釋／設定版本改變時 MUST 使相依結果失效；舊圖不得標為目前結果。回放 SHALL 使用同一截止的已可得欄位，結果識別納入回放範圍、世代、游標與時間 profile；正式 SHAP 計算及背景整合仍留 C9。

#### Scenario: 匹配來源的可用結果
- **WHEN** 圖表計算完成，結果來源與目前資料／選項／模型版本一致
- **THEN** 才標示為可用，圖旁可查資料來源／label source／scope、卷／材料 MD 範圍、截止、有效列／抽樣數、mapping／alignment／dataset／spec 版本、方法／模型／manifest／解釋版本與尺度；Heatmap 不會被誤稱模型解釋，C Mock 及合成真值不被誤稱真實量測

#### Scenario: 選項或版本改變
- **WHEN** 更換 CSV／映射／篩選、目標／特徵／圖型、逐目標 availability／原因／來源粒度或 alignment／label／spec／dataset／模型／manifest／解釋版本，即使數值與筆數未變，之後收到舊請求的結果
- **THEN** 舊結果維持過期或被隱藏，不能以新選項標籤展示，只有匹配目前來源的結果能成為最新；失敗載入不取代原有效資料及匹配結果

#### Scenario: 計算中與失敗恢復
- **WHEN** 使用者啟動圖表計算，或計算失敗後重新嘗試
- **THEN** 顯示計算中／具體錯誤與可重試狀態，不產生假完成圖，不清除其他業務狀態；重試成功後僅更新該圖區的匹配結果

#### Scenario: 同一切片重跑與有界輸入
- **WHEN** 同一來源與選項重跑／切 Tab，或切片以外未提供的資料被改動
- **THEN** 相同輸入的圖表內容及來源識別可重現，選項及匹配結果可保留，計算不回讀全域 CSV 或 What-if 數值；這項接點測試不代替 C7 播放控制及 C9 正式解釋驗收

#### Scenario: 回放品質配對與解釋可得性
- **GIVEN** 部分製程與品質已釋出，其他目標尚未可得
- **WHEN** 更新 Heatmap 或請求 SHAP
- **THEN** Pearson 僅用已可得有效配對；解釋使用已可得特徵及匹配且具歷史適用性的來源，不以缺標籤直接否決解釋，也不放行未來樣本或背景

#### Scenario: 重啟與過期圖表拒收
- **GIVEN** 圖表請求屬於重啟前或較舊游標
- **WHEN** 新範圍／截止已生效而舊結果抵達
- **THEN** 不冒充目前圖表，顯示過期／重新計算狀態；相同來源範圍與截止可重現，不使用完整 CSV 或情境候選補值

### Requirement: VIS-05 正式樹模型 SHAP 解釋

系統 SHALL 由已載入的正式 Champion 與其 manifest 提供真正的 SHAP Summary／Dependence 解釋；解釋 MUST 使用與推論相同的前處理、特徵順序與模型版本，背景資料只可來自對應 train split，並以固定 seed 及有界樣本量建立。

#### Scenario: 迴歸目標解釋

- **WHEN** 使用者選擇任一可用連續品質 Champion 及相容資料切片
- **THEN** 系統回傳與樣本及特徵對齊的回歸輸出貢獻值、基準值、背景來源、模型／manifest／解釋版本與單位

#### Scenario: 外觀 NG 解釋

- **WHEN** 使用者選擇外觀 NG Champion
- **THEN** 系統依 manifest 的 class labels 明確選擇標籤 1，並標示 SHAP 的 probability、raw margin 或 log-odds 尺度，不固定取陣列第二個輸出

### Requirement: VIS-06 解釋相容性與失效

正式解釋 SHALL 驗證 dataset source、schema、feature、preprocessing、label、spec、model、manifest、background 與 class mapping；任何相依版本、資料範圍、模型或選項改變時，舊 SHAP 結果 MUST 失效且不得以新標籤繼續顯示。

#### Scenario: Manifest 不匹配

- **WHEN** Explanation Provider 與目前選定模型的 manifest、特徵順序、輸出尺度或背景版本不一致
- **THEN** 系統拒絕解釋並顯示不一致欄位，不影響有效預測、Heatmap、SPC 或資料檢查

#### Scenario: 模型切換後舊結果抵達

- **WHEN** 使用者切換 Champion／資料來源後收到舊模型的延遲 SHAP 回應
- **THEN** 該回應保持過期或被丟棄，不得取代目前模型的圖表狀態

### Requirement: VIS-07 SHAP 資源與失敗隔離

系統 MUST 限制正式 SHAP 的資料列與背景樣本量，提供計算中、可用、不可用及錯誤狀態；計算錯誤或不支援目標只可影響相依圖區，且暫時圖形與運算資源 SHALL 在完成或失敗後釋放。

#### Scenario: 解釋計算失敗

- **WHEN** SHAP 計算超出限制、模型不支援或 Provider 回報可處理錯誤
- **THEN** 相依圖區顯示具體原因及可重試狀態，不保留舊圖冒充完成結果，其他模型與儀表板功能保持可用
### Requirement: VIS-08 Heatmap 相關方向摘要

Heatmap 可用時，系統 SHALL 對每個選定品質目標摘要最強正相關與最強負相關的製程／環境特徵、Pearson r 及有效配對數；摘要 MUST 依品質目標規格方向避免把相關正負號直接宣稱為改善，並持續明示相關不代表因果。

#### Scenario: 同時存在正負相關
- **WHEN** 某品質目標有至少一個可計算的正相關及負相關特徵
- **THEN** 系統顯示兩個方向中絕對值最高的特徵、r、n、單位與目前資料範圍，且數值與 Heatmap 格子一致

#### Scenario: 只有單方向或不可計算
- **WHEN** 只有正或負方向可計算，或所有格子因樣本不足、無變異或標籤不可用而無法計算
- **THEN** 系統只顯示可支持的方向，並對缺少方向或整個目標顯示具體原因，不補零或挑選無效格子

#### Scenario: 品質規格方向解讀
- **WHEN** 摘要涉及越高越佳、越低越佳或需落在區間／接近中心的不同品質目標
- **THEN** 系統分別標示相關方向與品質規格方向；MD／TD 等區間型目標不得僅依 r 正負號稱為有利或不利，外觀 NG 亦須明示 1 代表 NG

#### Scenario: 篩選與選項更新
- **WHEN** 使用者改變批次、時間、特徵或品質目標選項
- **THEN** 相關摘要與 Heatmap 使用完全相同的有效配對、來源身分與版本重新計算，舊摘要不得留在新圖旁

### Requirement: VIS-09 Heatmap 與 SHAP 可用性導引

系統 MUST 對 Heatmap、SHAP Summary 與 SHAP Dependence 分別顯示未載入、可用、計算中、不可用或錯誤狀態，以及資料來源、模型來源、阻塞原因與下一步。選項控制可停用，但狀態說明 SHALL 保持正常可讀對比。

#### Scenario: 尚未載入資料
- **WHEN** 工作區沒有成功載入的 dataset
- **THEN** Heatmap 與 SHAP 明示尚未載入資料並指示載入動作，不將已選來源誤寫成已載入，也不只顯示 `No options to select`

#### Scenario: Canonical 已載入且選用 Mock
- **WHEN** Canonical 資料可供 Heatmap 使用，但目前 Adapter 為 C 公式 Mock
- **THEN** Heatmap 可獨立計算；SHAP 顯示 Mock 不具真正解釋能力，提示如需真正 SHAP 應選 Synthetic 正式 artifact，且不產生偽造圖形

#### Scenario: 正式 SHAP 已就緒
- **WHEN** Synthetic 正式 artifact、Explanation Provider、manifest 與目前 Canonical 切片相容
- **THEN** Summary／Dependence 顯示可用狀態、模型與解釋版本並產生匹配圖形；控制項與圖形使用正常可讀對比

#### Scenario: 正式模型或解釋不相容
- **WHEN** artifact、manifest、來源 profile、必要特徵、目標或 Explanation Provider 驗證失敗
- **THEN** SHAP 顯示具體不相容欄位或缺項及恢復方式，不保留舊圖、不自動切換 Mock，且 Heatmap、What-if、SPC 與資料檢查保持獨立

#### Scenario: Summary 與 Dependence 的用途說明
- **WHEN** 使用者查看 SHAP 分析入口
- **THEN** Summary 說明其呈現整體特徵貢獻分布，Dependence 說明橫軸特徵值與縱軸 SHAP 貢獻；兩者均標示輸出尺度、單位及非因果限制
