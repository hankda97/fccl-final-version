# Design

## Context

動機見 proposal.md。C1～C6 已 Archive，原進度 24／39。現有 ReplayState 已有 mode、stream_id、generation、cursor、playing、speed、last_tick；overview 的控制仍停用。`data/session.py::selected_rows` 現在回傳完整篩選切片，sidebar／資料檢查也讀完整資料，不能只讓 SPC 受游標限制。

loader 缺 `available_at` 時以 timestamp 代入並回報 `AVAILABILITY_ASSUMED`；這是快照相容行為，不能作正式歷史發布證據。現有 C Mock 有明示 timestamp／available_at 及獨立歷史 fixture；組長七表另有 sampled_at、completed_at 等，但檢驗完成不必然等於發布。正式 JOIN、材料對齊、重測版本選取及 spec pivot 屬 A／B／C9。

SPC 純服務可接受有界切片與 analysis_scope_id；目前部分控制器仍自行取 selected_rows。What-if 選單目前可能因 options 變動自動重選；圖表已有來源／availability／manifest 驗證。本案擴充 orchestration，不替換已驗收的統計／公式 Mock／Pearson／SHAP renderer。

## Goals / Non-Goals

**Goals:** 一份可見性快照支援全部四 Tabs；純游標服務可注入時鐘及測試；保留快照體驗與固定基準，局部時間缺失可降級；提供未來模式接點但預設單一 workspace 即可使用。

**Non-Goals:** 七表 JOIN、跨站 MD 配對、正式重測選取、正式模型訓練／SHAP 計算、三模式導航、模式 B／C 模擬、真機控制。正式時間欄名與數值政策不在本案定案。

## Decisions

### D1：版本化時間投影，不直接拿 CSV 列順序回放

新增 `c_dashboard/replay/`，規劃 types、temporal、timeline、service／controller 等分層（實際檔名可依職責微調）。`TemporalProfile` 記錄來源／schema／mapping／時間設定版本、時區、識別與逐特徵／逐目標時間角色及證據。

內部 ReplayEvent 含 event_id、來源列／樣本／channel／revision ID、occurred_at、可信 available_at、批號／root_roll_id／MD 區段及有效性原因。保留原事件、製程完成、sampled_at、結果發布時間，不能僅保留一個 timestamp。available_at 不得早於相關發生／完成／量測，矛盾拒絕相依通道，不以 max() 修補或猜時區。

C 專用版本化 Mock profile 可明示寬列的欄位何時共同釋出，另建 C7 延後／逐目標 fixtures；不得套用正式來源。正式時間映射未確認時只播放有證據的通道，無可信事件時回放不可用但快照仍可檢查。若只有最終重測而欠缺當時版本證據，品質歷史不可用；C 不推導重測優先序。

替代方案：依 timestamp 一次放行整列會洩漏晚到品質；依五目標最晚時間才放整列會隱藏早已可用的製程及其他目標，均不採用。

### D2：可信可得時間原子群與唯一游標

事件依可信 available_at、穩定來源序號排序；同可得時刻為一個原子群。單一步進消費一群，包括其所有列／channel；occurred_at 留作圖表及材料追溯，不混同模擬時鐘。游標為已消費群數，範圍 0..N；起點沒有觀測，介面顯示「尚未播放」，不創造來源 timestamp。

時間／批號篩選仍依既有 timestamp 選材料 cohort，該 cohort 的可信晚到品質事件保留，即使晚於材料選取 time_end；UI 分別標示 cohort 範圍與 availability horizon。不能把篩選外材料引入。已播放來源列按穩定 source-row ID 去重，事件群數另列，不因同列多目標晚到而重複計數。

ReplayState 擴充 timeline_id、virtual_clock、monotonic_anchor、last_tick_sequence 等；stream ID 綁來源內容、映射／時間 profile／版本與篩選，generation 在 restart／來源生命週期遞增。只有游標／時鐘服務可推進，不設 SPC 或圖表各自的游標。

### D3：共同 VisibilitySnapshot，按用途輸出受限視圖

每次計算先建立不可變的 VisibilitySnapshot：stream／generation／cursor／cutoff、版本、已釋出識別、feature_view、measurement_views[target]、欄位 mask、availability／原因、可見 raw preview／validation issues 與進度。這些是同一截止的不同用途投影，非獨立時間軸。

尚未可得值及其旗標在送進服務前遮蔽，不以空值填回原 CSV。sidebar 的最新環境／材料摘要、原始與正規化預覽、問題清單及排除數都受此界線控制。可事先顯示來源名稱、schema、總列數與篩選範圍；不得提前顯示未來品質分布或可辨識其值的錯誤訊息。C2 致命格式錯誤仍先拒絕載入。

快照模式保留原完整篩選分析；回放只傳 VisibilitySnapshot。服務不得回讀全域 full CSV 或 What-if。以未來值擾動測試比較相同 cutoff 的業務內容，允許來源 hash 等中繼資料不同，但數值／事件／可見問題不得不同。

### D4：單一非阻塞計時入口

本機 Streamlit 1.66.1 支援 `st.fragment(run_every=...)`，規劃以單一 fragment 計時入口搭配受控 rerun 更新全畫面，不使用 while／sleep 或常駐背景執行緒。實際 Apply 須驗證 browser 自動刷新，AppTest 不足以證明計時正常。

計時服務注入 monotonic clock，將到期通知識別為 generation＋deadline sequence；一般重跑沒有新到期槽就不 advance，相同槽只處理一次。歷史虛擬時間依 wall-clock 經過量乘 0.5／1／2／4 倍前進，跨多群依序處理以保留中間警報，不丟棄事件。單步先暫停再消費一群；暫停及變倍率重設 anchor，不補入暫停經過量。終點自動停止，再按播放不自動重啟。倍率為 UI 播放設定，與 m/min 線速完全分離。

替代方案：每次 script rerun 增加一列會讓操作頻率改變進度；多個 Tab 各自計時會重複推進，均不採用。

### D5：保留固定 SPC 與分離監控預測

SPC 使用逐目標已釋出量測投影，帶正確取樣／可得時間及原子組識別，未完成或無效組保留為邊界，不刪列湊組。沿用 compute_spc、既有合理子組驗證、超界／六點趨勢／九點同側規則；必要時由 orchestration 分別傳入目標投影再組合原 SpcResult，不修改判定門檻。

獨立歷史基準必須早於回放起點、樣本不重疊且通過既有條件檢查；版本固定，不隨 cutoff 重估。同一可信切片及基準的快照／回放統計一致。analysis_scope_id 使用穩定的 stream＋generation 範圍，不把每個 prefix hash 當新事件來源；結果快取另納入 cursor／內容。SPC Tab 與主 Alarm 共用分析結果，晚到及重跑不重複附加事件。重新開始建立新世代並清除當前顯示的舊範圍事件。

目前監控對象以最新已可得製程的原發生／完成順序選定，不以最後抵達的品質事件選最新材料。AI 每個目標只用當下可得必要特徵；缺特徵、規格或模型能力各自降級。模型版本及訓練／適用時間不足時不得宣稱 as-of 無前視，正式來源待 C9；公式 Mock 保留示範標示，無真正 SHAP。

### D6：What-if 固定快照與明確失效

What-if 選項使用穩定材料識別，不讓 dataclass 的欄位變化觸發隱性重選。主動選取／更新基準時擷取當下 feature snapshot、環境、來源版本、批號／卷／MD／時間；原設定與候選保存在情境副本。晚到特徵或品質不修改該副本，使用者要更新須明確操作並重設候選／舊結果。

重啟使游標歸零且暫停，已選區段可保留內部識別作失效提示，但不得呈現其尚未可見的參數／預測／建議，控制停用。設 invalidated／requires_reselect 標記，阻止目前 ensure_what_if_selection 的自動重選；再次播放到該段也不恢復，須主動重選。回到快照不自動復活失效情境。監控 SPC／Alarm 不受固定情境阻擋。

### D7：圖表同截止與來源驗證

Heatmap 只消費已可得特徵與實測標籤的有效配對，保持 Pearson、單位、排除原因與非因果提示。模型輸入、標籤及 SHAP 能力仍分開；缺標籤不直接阻擋有效解釋。SHAP 請求／回應匹配 visible sample IDs、feature order、目標／NG 類別 1、尺度、model／manifest／profile 版本與 cutoff；背景資料時間適用性不明時拒絕相依正式解釋並標待 C9。

快取 key 加入 stream／generation／cursor／cutoff／時間 profile，保留 C6 原 metadata 驗證；相同數值但 availability 改變也失效。舊請求抵達不能覆蓋新狀態，不因每個 UI rerun 重建無關服務；測試 Figure／Payload 仍明示非真正 SHAP。

### D8：與 Proposed 三模式 Change 的合併邊界

`fccl-three-mode-workspace` 與本案同時 MODIFIED WS-01／WS-02。行為可相容，但全文 Delta 基於同一舊主規格，存在後同步者覆蓋前者情境的文字衝突；strict 不會證明跨 Change 合併安全。本輪不修改其文件、不引入 registry 或 B／C 模擬。

C7 先完成時，未來三模式 Apply／Archive 前需以新主規格重建其完整 WS-01／02 Delta，保留 C7 播放情境、移除過時的回放未交付敘述。三模式先獲批時，本案 Apply 前須同樣重對齊其外層導航、模式獨立狀態、暫停與 activation_epoch；回放只接模式 A。對應清單見 docs/C7_THREE_MODE_COMPATIBILITY.md。未審核這兩項全文合併，不可盲目順序 Archive。

回放服務接受預設單一 workspace scope 及可選生命週期 token，保留將來模式切出時暫停／拒絕晚到結果的接點，不強制依賴未批准導航。TCP-007 待團隊討論狀態不變。

## Risks / Trade-offs

- 正式可得時間不足 → 顯示逐通道限制，C Mock 獨立驗收；不以 timestamp fallback 放行。
- 延後品質造成圖表回補 → 保留取樣時間與可得截止兩者，不將晚到值偽裝當時已知，SPC 去重及連續性須測試。
- 全部預覽／問題清單可能洩漏 → 強制共用可見性投影，未來值擾動涵蓋所有 Tabs／側欄，不只 SPC。
- fragment 與 widget 重跑交互影響 → 單一到期序號、注入時鐘測試及真瀏覽器驗收；不能只靠 AppTest 宣告 timer 通過。
- 寬表每目標不同時間 → 用欄位釋出事件，不一律推遲整列；有來源 revision 才處理歷史版本，缺證據降級。
- 大資料全量重算 → 投影／索引綁來源及版本快取、結果綁 cutoff；先確保因果時間邊界，效能優化不能跳過事件。

## Migration Plan

依 tasks 的 7.1～7.5 來源群順序實作，新增獨立 C7 fixtures，不覆寫既有資料。快照保留既有入口，逐項接上共用可見性參數，完成 C1～C6 回歸後才宣告 C7 完成。若回放出錯，停用回放並呈現限制，快照可用；不得為回退修改 Archive、原始資料或正式契約。本次 Propose 不做上述實作或正式主規格同步。

## Open Questions

下列是正式交接填值，C Mock 規劃可獨立進行：A／B 提供事件／三站完成／量測／發布時間欄名、時區及可靠性、逐特徵與逐目標可得性、卷／MD／檢驗 ID、as-of 修訂歷史及 source／alignment／dataset 版本；B 提供模型訓練截止／歷史適用範圍、SHAP 背景與 manifest 宣告。欠缺時依 REPLAY-07／04 降級，不由 C 猜定，也不重做上游 JOIN。
