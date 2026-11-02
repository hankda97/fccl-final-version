# Tasks

> 2026-11-02 文件同步：實際已存在前輪 6／12 勾選及 C6 局部程式（C-local::DEV-20261102-004），本次暫停 Apply，不清除勾選、不將 C6 計為原 6.1～6.4 完成。以下 1.1～2.3 的完成僅對應原規格；D9／新版資料與 manifest 差異尚未驗收，集中於未完成的 4.2／4.3。整案仍須全數新版情境通過才可完成。未改任何 Python。

## 1. 實測 Heatmap（原 6.1）

- [x] 1.1 建立 visualization 請求／結果／來源型別、版本化 Pearson 顯示設定與 C6 小型手算 fixtures；以單元測試確認欄位 allowlist、五目標／單位、無效識別與重複列排除，原 C2 fixtures 及 A 程式不需修改（VIS-01）。
- [x] 1.2 實作有界切片的 pairwise Pearson 純服務；以手算正／負／零相關、逐格 n／排除數、缺值／非有限值、常數、單類別外觀、缺目標與不足三筆等測試驗證，不讀預測／What-if／隱藏真值，不改輸入 DataFrame（VIS-01、VIS-04）。
- [x] 1.3 將 Heatmap 多選與 native chart renderer 接入 AI 圖表 Tab，呈現標籤／單位、固定色階、N/A 原因、有效列與截止；以 chart payload／AppTest 覆蓋正常、空篩選／空選取及部分量測，並更新指南 Heatmap 操作與非因果／樣本數限制（VIS-01、WS-01／04）。

## 2. 可選解釋接點與 SHAP 互動（原 6.2，部分原 6.3）

- [x] 2.1 新增 C 內部可選 Explanation Provider／不可用 Provider 與請求 envelope，沿用既有模型能力資訊且不修改 ModelAdapter 的必備預測方法；以原 Adapter／公式 Mock／測試 Provider 驗證相容、能力不足不呼叫 explain、模型預測保持可用（VIS-02、WS-04）。
- [x] 2.2 實作 Summary／Dependence 切換、五目標／特徵選擇、無資料及待 B／C9 整合提示；以 AppTest 驗證兩種原定名稱可尋得、公式 Mock 不產生假 SHAP、Heatmap 不受影響，並更新指南能力／來源及圖型選取說明（VIS-02、WS-01）。
- [x] 2.3 實作結構化解釋及 Figure envelope 的來源／目標／單位／維度／尺度驗證；以測試覆蓋 N×F、base values、非有限／重複／錯序 IDs、feature domain、模型／前處理版本不符、NG 類別順序 [1,0] 與缺標籤拒絕，記錄 C 內部欄位及 C9 正式映射待確認清單（VIS-02；原 VIS-03 僅接點）。

## 3. 測試解釋圖形呈現（原 6.3）

- [x] 3.1 建立固定且明確標示 render-test 的 payload／Provider fixtures，實作 Summary 多特徵貢獻分布與 Dependence 特徵值－貢獻圖；以純 renderer／AppTest 核對資料、軸、單位、目標／特徵切換與整區測試標示，一般 Mock 不得自動顯示替身結果（VIS-02）。
- [x] 3.2 加入受信任記憶體 Matplotlib Figure renderer，於 Apply 鎖定相容依賴並更新 requirements；以真實測試 Figure 覆蓋正常／不支援型別／例外、無阻塞 show、反覆渲染清理及不快取活 Figure，更新指南與呈現接點文件，明示不是正式 SHAP 計算驗收（VIS-02）。
- [x] 3.3 將驗證／Provider／繪圖錯誤限制於相依 SHAP 區；以整合測試確認缺能力、單目標不可用、錯誤回應及重試不清除 Heatmap、CSV、SPC／AI Alarm、目前預測或固定 What-if，並補錯誤判讀文件（VIS-02、WS-04）。

## 4. 圖表狀態與結案整合（原 6.4）

- [x] 4.1 新增獨立 VisualizationState、完整來源 key／快取與局部失效，接入成功來源／篩選切換及 UI；以狀態測試／AppTest 覆蓋 running／ready／stale／unavailable／error、變更內容但同名同筆數、目標／圖型／模型版本切換、舊結果拒收、同源重載／失敗上傳／跨 Tab 保留，更新狀態與限制文件（VIS-04、WS-02）。
- [x] 4.2 依 D9 補齊內部 source profile／投影、逐目標 label availability／來源與粒度、結構化不可用原因及 manifest 相容性驗證，更新 key 與相依 UI；正式 A／B 轉接留 C9。加入非空但 unavailable、缺旗標、roll scope、抽檢／合成真值隔離、對齊／重測／外觀衝突原因、僅 metadata 改變失效、model manifest／class 1／尺度不符、缺標籤但可解釋、單目標不可用等單元及 AppTest；重新核對原 1.1～2.3。執行圖表跨功能整合與 C1～C5 完整回歸；驗證手算係數、圖形與測試來源、What-if 不改 Heatmap／SPC、固定基準／兩類 Alarm 仍正常及切片外擾動不影響有界結果；執行 pytest、Streamlit AppTest、compileall、imports、本機啟動及 OpenSpec strict，保留實際命令與結果（VIS-01／02／04、WS-01／02／04）。
- [x] 4.3 建立 C6 驗收矩陣，逐項將本 Change 全部 28 Scenario 與原任務 6.1～6.4 對應到實際測試／文件，包括 D9 新版差異檢查及原已勾選任務的重驗證證據；核對指南、Roadmap、DEVELOPMENT_LOG、正式 SHAP／C7 未完成清單、組長來源版本與 TCP 狀態，只有已驗收任務才勾選，不將 renderer 成功計為 B 真正 SHAP 交付，不自行確認 coverage／錨點／重測／NG 門檻（全案追溯、原 VIS-03／VIS-04 後續邊界）。

## Workflow follow-up

- 四組分別交付局部測試及文件；本案 12 個細分任務對應原 C6 四項，不增加原 39 項任務的分母。
- 本案完成後須另經授權 Archive；C7 動態回放、C8 全流程驗收、C9 A／B 與真正 SHAP 整合保持後續計畫，不阻擋 C6 獨立審查。


本輪 Apply 結案註記（2026-11-02）：前文 6／12／暫停是文件同步當輪狀態；續作授權後已依 D9 完成局部功能及新版差異驗收，最終 204 passed，原 C1～C5 回歸 126。詳見 [28 情境證據](../../../docs/C6_VISUALIZATION_ACCEPTANCE.md) 及 tasks；未 Archive／同步主 specs，不表示真正 SHAP／正式 A／B 整合完成。
