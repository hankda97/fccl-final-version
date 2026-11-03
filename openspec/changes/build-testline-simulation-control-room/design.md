# Design

## Context

See `proposal.md` - Why. 目前專案已有 v2 canonical dataset、五目標樹模型、模式 A 的 CSV／SPC／What-if／Heatmap／SHAP 與部分 Mode B 骨架；但這些能力以快照分析為主，沒有連續材料流、setpoint／actual、參數事件、製程訊號 SPC 或 Run 生命週期。使用者已確認只保留 Mode B 作正式產品面，且必須先看到可操作版面再投入後端建置。

## Goals / Non-Goals

**Goals:**

- 以 Gate 0 靜態原型先驗收資訊架構、字體、密度、導覽與互動，再建立契約、資料、模型與執行後端。
- 建立可重現、可追溯、不中斷既有 v2 的單產品連續測試線。
- 將配方標準、產品規格、UI 操作範圍、模型支援範圍及 SPC 管制界限分離。
- 讓調參只影響尚未通過適用站別的材料，並以製程訊號及四項品質呈現延遲結果。
- 控制計算量，避免 Streamlit 重跑、模型／圖表重算及 Alarm 明細使本機無法操作。

**Non-Goals:**

- 不接真實生產資料、PLC、MES、資料庫或設備控制。
- 不建立外觀 v3 模型、預測良率、站別早期品質模型或真實因果最佳化。
- 不在一般導覽提供 SHAP、Alarm 人工簽核／靜音／工單或中斷 Run 續跑。
- 不自動把 Run 資料加入訓練、模型升版或 baseline。

## Decisions

### 1. 以單一 Mode B 產品面取代三模式導航

一般使用者直接進入測試線控制台；舊 A 的資料、模型、What-if、Heatmap 與 SPC 實作只作內部可重用服務，C 隱藏。這比繼續維護三套可見工作區更容易避免 session state、來源及成熟度混淆。替代方案是保留 A／B／C 選擇，但已被使用者否決。

### 2. Gate 0 使用固定 fixture，不依賴後端

先建立獨立、可啟動的 Streamlit 靜態原型，包含四頁導航與全部主要控制，固定數值一律標示為原型。Gate 0 不載入 v2 模型、不偷偷啟動模擬器，也不以舊功能拼出「看似完成」的畫面。使用者驗收後才進 Gate 1；若版面不合意，只需改 UI 契約與原型，避免重做後端。

### 3. 控制台分成四個頁面

- 生產控制台：產線位置、產品／配方、七項主要輸入、三張關鍵圖、四項品質、開啟 Alarm。
- SPC 詳細監控：所有適用圖、事件群、技術明細與完整狀態。
- What-if／Heatmap：按需分析，與 live Run 隔離。
- Run 紀錄：completed／interrupted manifest 與唯讀資料。

首頁固定最多三張小圖及最近 60 點，避免大量圖表、技術 ID 與歷史紅字壓縮操作區。SHAP 不在這四頁中呈現。

### 4. 單一產品與版本化配方

初版只有 `FCCL-DEMO-001`／`SIM-RECIPE-3.0`。預設主要參數如下：

| 參數 | Setpoint | 配方範圍 | UI 範圍 |
|---|---:|---:|---:|
| 線速 (m/min) | 4.80 | 4.40–5.20 | 4.00–5.60 |
| 塗佈間隙 (μm) | 28.0 | 26.5–29.5 | 25–31 |
| 熟化溫度 (°C) | 171 | 168–174 | 165–177 |
| 排風量 (m³/h) | 2100 | 1900–2300 | 1700–2500 |
| 熟化時間 (min) | 12.5 | 11.8–13.2 | 11–14 |
| 壓合溫度 (°C) | 181 | 178–184 | 175–187 |
| 壓合壓力 (MPa) | 2.55 | 2.35–2.75 | 2.20–2.90 |

進階參數為塗佈溫度 82 °C（78–86）、黏度 1180 mPa·s（1080–1280）、壓合時間 18 min（16–20）。乾膠厚度產品目標為 25.0 μm、允收 23–27 μm。模型支援範圍由 v3 train manifest 計算，不能硬編碼成 UI 範圍。這些都是 synthetic demo 假設，不是工廠標準。

### 5. 事件驅動的材料流與延遲

Run 啟動時預載穩態連續線，不從空機等待整條線填滿。單一模擬時鐘每 5 秒提交一個 tick；材料區段帶有 MD 位置及塗佈、熟化、壓合進出時間。參數表單採「編輯候選 → 整組驗證 → 確認套用」，成功後只新增不可變 ParameterEvent。各站 actual 依設備響應與擾動逐步接近 setpoint；事件只對尚未通過該站的材料生效。

四目標品質只在材料完成三站及品質延遲後推論，每 30 模擬秒或新參數導致新的適用完成區段時更新。這避免使用未來特徵，也避免建置證據不足的站別早期模型。

### 6. Synthetic v3 與四模型組

v3 保持 200 卷、約 20,000 segments、120／40／40 完整卷時間切分，新增乾膠厚度、排風量及三站 setpoint／actual／延遲特徵。訓練 seed／卷與 UI demo seed／Run 完全隔離。四目標各比較簡單 baseline、Random Forest Champion 候選與 HistGradientBoosting Challenger；XGBoost、LightGBM、LSTM／GRU、Autoencoder 仍非核心依賴。v2 外觀 artifact 保留，但 v3 bundle 與新 UI 不載入。

### 7. 製程 SPC 採正確圖型與固定 reference

乾膠厚度每次五個橫向量測形成 X-bar／R 子組；溫度、風量、線速、壓力是連續單值訊號，採 I-MR 或 EWMA，不假裝為 X-bar。baseline 來自相同配方的獨立穩定 synthetic reference，固定於整個 Run，不能以目前 Run 滾動重估，也不能用產品規格或配方範圍代替。

狀態分正常、警告、嚴重、證據不足。製程失控與產品超規是不同事件語意。相鄰重複觸發彙整為事件群；按下參數確認不會清除 Alarm，只有規則定義的後續有效點才能復歸。初版不做 acknowledge、sign-off、silence 或工單。

### 8. Heatmap 與 What-if 以完成材料為分析單位

Heatmap 將同一材料區段在各站的 5 秒訊號聚合成一列，再配對四項品質，避免重複品質值造成虛假樣本量。來源可選 v3 reference 或目前 Run；目前 Run 至少 30 個有效完成區段。計算僅由按鈕觸發，結果帶截止與來源版本。

What-if 固定一個完成區段，使用相同 v3 模型比較基準與候選，不讀取之後的 live 狀態。採用候選只會回填控制台表單，必須再次確認才形成 ParameterEvent。此流程是決策輔助，不代表真實因果效果。

### 9. 本機 Run 儲存與不可恢復中斷

每個 Run 寫入 `runtime_data/testline_runs/<run_id>/`：

```text
manifest.json
process_signals.csv
material_segments.csv
parameter_events.csv
spc_events.csv
quality_predictions.csv
```

運轉狀態在記憶體，每 60 模擬秒做一致 checkpoint；正常停止完成最終寫入及 hash。發現未完成資料時標為 interrupted 並允許唯讀檢視，v1 不續跑，避免必須序列化計時器、快取與隨機狀態。`runtime_data/` 納入 `.gitignore`。

### 10. 單一 in-flight tick 與降載策略

模擬器不使用可堆積的定時 callback；任何時刻只有一個 tick 可提交。模型／配方／baseline 於版本不變時快取，SPC 增量更新，首頁只畫最近 60 點，Heatmap／What-if 按需計算。若 tick 超過排程間隔，降低倍率或自動暫停並提示，不跳資料。這比背景累積 backlog 更可驗證，也適合單機 Streamlit。

### 11. Gate 交付與契約同步

- Gate 0：只交付靜態 UI 原型與 UI 驗收測試；完成後停止，等待使用者驗收。
- Gate 1：同步 AGENTS.md、SKILL.md、schema／recipe／Run／事件契約及驗證器。
- Gate 2：產生 v3、訓練／評估四模型、建立 manifest 與 reference。
- Gate 3：實作模擬器、Run store、製程 SPC、事件群及單元／整合測試。
- Gate 4：接入正式控制台、What-if／Heatmap、效能與瀏覽器回歸。

每個 Gate 必須有自己的驗證證據；後一 Gate 不以未驗證前一 Gate 為完成。AGENTS.md／SKILL.md 只在 Gate 1 Apply 時依已批准規格修改，本次 Propose 不改動。

## Risks / Trade-offs

- [靜態原型可能被誤認為成品] → 固定顯示原型 banner，fixture source 進入每張卡片／圖表 metadata，Gate 0 驗收不勾選後端 tasks。
- [模擬機理過度簡化] → 保留版本、seed、漂移真值及 Synthetic 限制；不聲稱工廠因果或真實製程效能。
- [固定 v3 規模在本機訓練較慢] → 先做可重現資料驗證與 baseline，再按目標訓練；核心模型只用 scikit-learn RF／HGB。
- [Run CSV 持續增長] → UI 採有界視窗及 checkpoint，詳細歷史按需讀取；若規模超出單機再另提資料庫變更。
- [配方與模型支援範圍不一致] → UI 同時顯示兩者，推論前由 manifest 驗證，不靜默外插。
- [舊 A 測試與新單一入口衝突] → 將舊路由保留為內部／測試用途，新增 B 專用驗收；移除或重寫衝突測試時保留變更證據。

## Migration Plan

1. 交付 Gate 0 原型，保留目前正式入口作回退；取得使用者版面驗收。
2. Gate 1 更新契約與版本化設定，但不切換模型或預設路由。
3. Gate 2 產生 v3 與四模型 bundle，與 v2 並存並完成離線驗證。
4. Gate 3 以獨立 Run 路徑完成模擬／SPC，不污染舊 session state。
5. Gate 4 將一般入口切至新控制台；保留舊 A 內部路由至回歸通過，再決定後續清理 Change。
6. 發生重大問題時，回退一般入口至既有應用；v3、Run 與新 artifact 皆為隔離路徑，不需改寫 v2。
