# Tasks

本案第一階段導航／隔離已由本輪使用者確認團隊同意並授權 Apply；實際進度以以下 20 項 checklist 為唯一來源。5 新增＋2 修改需求、28 個情境保持；原始進度維持 **29／39**，新增工作另計。完整 B／C 模擬器與 SQLite／CSV 持久化不在本案。前輪 Proposed／Update 限制保留於原 DEV／ADR 歷史，本輪未授權 Archive／Sync Specs。

## 1. 模式狀態與既有 Session 相容

- [x] 1.1 建立 D2 的 mode registry／RunContext／版本型別與三份獨立 WorkspaceState；用狀態單元測試證明可變子物件不共用、未知 registry 版本保留原資料，並記錄模式 ID／型別責任（MW-02）。
- [x] 1.2 實作單一工作區升級及 A 相容 alias；以現有載入／篩選／固定 What-if／模型／SPC／圖表及 C7 游標／時間 profile 驗證原 instance 與 key 不被重設，重複初始化不複製資料（MW-02 舊工作階段；WS-02）。
- [x] 1.3 將來源成功切換、失敗上傳、篩選及明確 run 重設限制於指定子工作區；以三模式相同檔名／批號／卷／區段與跨 Session 測試驗證其他模式完全不變（MW-02 資料重設／同名識別）。
- [x] 1.4 建立 widget context／UiPreferences 持久化與恢復接點，A 預設 keys 保持相容；測 inactive widget 消失後仍能恢復來源選擇／Tab／篩選及候選，不複製上傳物件，補狀態邊界文件（MW-02 切換保留；WS-02）。

## 2. 外層導航與模式 A 相容畫面

- [x] 2.1 加入側欄 A／B／C 選擇與頁首模式標示，預設 A，僅組合 active 頁面；AppTest 驗證真實切換、未知模式輸入處理，spy 確認不執行隱藏模式的載入／模型工作（MW-01）。
- [x] 2.2 將原 C1～C7 畫面完整接為 A，保留四 Tabs、CSV／環境／產品資訊、五目標／SPC／兩類 Alarm／What-if／三圖與 C7 全部控制及不可用提示；以 focused AppTest 驗證最新 WS-01／02 的 C7 兩情境與三模式情境，切換往返仍可操作，正式七表／模型未交付仍按 C9 提示（WS-01／02；MW-01 返回模式 A）。
- [x] 2.3 建立 B／C 待交付頁、定位及後續 Change 連結，未提供 Provider 時投入／補償動作停用；AppTest 驗證無 A 結果混入、無模擬或機台呼叫，更新導航／成熟度指南（MW-01 未交付入口；MW-04 未提供後端）。

## 3. 共用服務、SPC／Alarm 與結果隔離

- [x] 3.1 建立 mode-aware 共用服務組合接點，沿用既有 ModelAdapter 與固定 What-if／控制呈現；以兩個獨立 child workspace 的測試 harness 驗證五目標輸出／逐目標不可用、候選不改歷史，不複製模型公式／不開 B／C 完整操作頁（MW-03 模擬與候選；MW-04 接點替身）。
- [x] 3.2 為 SPC baseline／結果、歷史事件與 Alarm 去重／顯示加模式、run 及事件類型邊界；測同事件 ID／規則／不同基準不互吞，SPC／AI／未來訊號事件不混用；無獨立有效基準只回報無法判定，A 固定界限及其他 run 歷史不被切換／候選／reset 影響（MW-02／03）。
- [x] 3.3 將模式／run／資料與 simulator 來源／availability／模型／manifest／設定版本納入預測及圖表快取與顯示；測 Synthetic 輸入、模擬量測、正式模型輸出／公式 Mock 分別標示、同 key 不混用、局部錯誤不清其他結果，更新共用接點與快取文件（MW-03 模型與圖表；WS-02）。

## 4. 模擬 Port 與驗證替身

- [x] 4.1 定義 D5 模擬能力描述及可選動作 Port，提供預設 unavailable 實作；單元測試確認 start／advance／confirmed event／reset 均不生成資料或機台請求，A 的預測 Port 不需新增必備方法（MW-04 未提供後端）。
- [x] 4.2 建立 context／event／observation／來源描述驗證與結構化錯誤；測模式／run／版本／單位／站別／時間缺失、MD 無效、未知 schema／未標示 Synthetic／Mock 或目的地指向七表皆拒收並保留有效狀態，寫入 spy 證明不修改七表／生成器／正式模型；文件記 D8 的獨立 CSV／SQLite 取捨，僅驗接點而不實作持久化、JOIN 或標籤選取（MW-03／04）。
- [x] 4.3 建立固定且明示介面測試的 B／C Provider，驗證事件／process／原始與處理後 signal／measurement／truth／prediction 分流及逐特徵／目標可得時間；spy ModelAdapter 確認只收到支援且已可得特徵，未來量測／噪音真因不進分析，五目標不足逐項提示，fixtures／記憶體測試不產生一般 UI 模擬器或儲存 I/O（MW-03／04）。
- [x] 4.4 驗證候選意圖、人工確認模擬事件與未支援動作的區別，測 What-if 不產生已執行紀錄、不保證線速改善；文件列出確認時間、參數差值、站別／受影響 MD、原始訊號與補償歷史保留、後續量測延後可得及 Synthetic／Mock／非因果／非機台控制語意；實際事件及量測生成仍後續兩案（MW-04 調參意圖）。

## 5. 模式生命週期與 C7 相容接點

- [x] 5.1 實作 activation_epoch／run generation 與目前 request token 比對；測切換 A→B→A 的晚到成功／失敗仍拒收，而已完成且內容匹配的快取可保留，不讓導航強迫重算（MW-03 舊請求；MW-02）。
- [x] 5.2 將 mode／workspace／epoch 綁定 C7 既有 lifecycle_token，建立離開模式暫停／返回不自動播放的接點；用已交付 C7 與可控時鐘測游標不歸零、倍率非線速、inactive 舊 tick 拒收，成功換源重建 ReplayState 後亦重新綁 context；來源時間不適用則僅降級相依回放，不退回全域占位（MW-05／WS-01）。
- [x] 5.3 用 C7 真實重啟／有界前綴與 reset hook 測 A 輪次、不可見 What-if 失效且不自動復活、來源／profile 變更及舊回應拒收，確認 B／C run／事件與 A 基準不變；更新 C7 先完成的導航相容文件，不重做 timer／回放引擎或實作 B／C 時鐘（MW-05；WS-02）。

## 6. 跨功能驗收與交付紀錄

- [x] 6.1 建立本 Change 全部 28 個 Scenario→實際測試證據矩陣，保留原 26 情境的追蹤及 C7 兩項新增對照，執行三模式整合與 A 的 C1～C7 全回歸（歷史參考 251 項／AppTest 38，不直接當新結果）；驗證三圖／SPC／兩類 Alarm／固定 What-if／可信回放、來源與儲存隔離及機台邊界（全案）。
- [x] 6.2 執行 pytest、真正導航 AppTest、導航前後 C7 播放／暫停／單步／重啟／倍率／終點的真瀏覽器回歸、Python 語法／匯入、Streamlit 啟動及 OpenSpec strict；記實際結果，不用 fake tick 代替 browser timer，也不將 Port 測試寫成完整 B／C 模擬驗收（全案）。
- [x] 6.3 完成操作／接點／遷移與退回指南，核對原進度 29／39、擴充 20 項另計、唯讀七表／C 獨立來源、B／C 模擬器與持久化後續範圍及 TCP／待批准事項，更新 DEVELOPMENT_LOG／必要 ADR，僅已驗收項目勾選（全案追溯）。

## Workflow follow-up

- 本輪僅執行已授權的第一階段 Apply／驗證；實際證據見 docs/THREE_MODE_ACCEPTANCE.md 及 docs/evidence/three-mode。完成後停止，不自動 Archive／Sync Specs。
- B／C 後續 Change 僅在 Roadmap 規劃，尚未建立 active artifact；其完整模擬、訊號處理與補償需獨立 Propose／Apply 及驗收。
- C7 原五項已完成 Archive，三模式外殼須保留並重驗；正式資料／模型契約變動另經跨組確認，不以 C 的來源 envelope、儲存格式或模型接點強制 A／B 採用。
