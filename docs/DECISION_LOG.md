# 決策紀錄

本文件採追加式 ADR。決策變更時新增 ADR 並以 Superseded／Supersedes 連結，不改寫舊 ADR 原文。

## ADR 模板

- 決策 ID／狀態／日期與決策時間：
- 背景：
- 決策：
- 理由：
- 影響與限制：
- 取代關係／證據：

## ADR-001：保留連續最高通過溫度作為耐熱度目標

- 狀態：Accepted
- 日期與決策時間：2026-11-02；2026-11-02 00:57:58 +08:00 (Asia/Taipei)
- 背景：既有 CSV 只有固定 150 °C、30 分鐘熱收縮，以及固定 288 °C、10 秒焊錫漂浮通過旗標；兩者都不等同 `SKILL.md` 定義的連續 `heat_resistance_c` 最高通過溫度。
- 決策：依使用者選定的第二方案，維持 `SKILL.md` 原契約，新增連續耐熱度模擬目標；保留既有熱收縮、焊錫漂浮及 UL94 欄位。
- 理由：避免將不同測試概念改名混用，並讓未來 Random Forest 可建立連續耐熱度迴歸模型。
- 影響：`quality_timeseries.csv` 新增 `heat_resistance_process_c`、`heat_resistance_measured_c`；`quality_inspection.csv` 新增 `heat_resistance_c`、`heat_resistance_process_c`、`heat_resistance_spec_pass_flag`；`quality_specifications.csv` 新增 `heat_resistance_c` 規格。
- 限制：中心值 305 °C、LSL 300 °C、USL 330 °C 與生成公式皆為模擬假設；正式產品使用前必須確認測試方法及驗收值。
- 取代關係：不適用，首筆 ADR。
- 證據：使用者於 2026-11-02 明確選定第二方案；對應 `DEV-20261102-001`。

## ADR-002：七表保留來源粒度並建立逐目標 canonical model table

- 狀態：Accepted（本機工作草案；跨組正式採用待確認）
- 日期與決策時間：2026-11-02；2026-11-02 02:10:59 +08:00 (Asia/Taipei)
- 背景：七份來源表具有卷、站別區段、追溯、完整合成真值、抽檢、規格與漂移事件等不同粒度，直接平面合併會複製標籤、造成洩漏或破壞追溯。
- 決策：保留七表；以最終壓合 MD 半開區間為 canonical 錨點，依重疊長度對齊三站；正式模型逐目標使用有效抽檢標籤；整卷檢驗不複製到區段；規格依產品、版本、特性及有效期 pivot；重測依有效性與明確 parent 關係選取；外觀以 `appearance_ng_flag` 為真值；availability 採總旗標加逐目標旗標。
- 理由：同時保留來源可追溯性、避免一對多 JOIN 擴增與標籤洩漏，並讓不同抽檢頻率的目標各自取得最大有效樣本。
- 影響與限制：已同步 AGENTS／SKILL 與 `define-seven-table-integration` Change；canonical builder 尚未實作，跨組欄位名稱與正式規格仍待 A／B／C 確認。
- 取代關係／證據：不取代 ADR-001；使用者於本次要求依建議修改需要變動的 MD。

## ADR-003：採用分層 Champion／Challenger 模型治理

- 狀態：Accepted（本機工作草案；跨組正式採用待確認）
- 日期與決策時間：2026-11-02；2026-11-02 02:10:59 +08:00 (Asia/Taipei)
- 背景：使用者希望現在先定義 XGBoost、LightGBM、LSTM／GRU、Autoencoder 等模型的加入規則，以免後續重構資料與介面。
- 決策：常數／線性模型作基準，Random Forest 為初版 Champion，HistGradientBoosting 為必要 Challenger；XGBoost／LightGBM 採共同 adapter 可插拔；LSTM／GRU 僅在 horizon、序列數量及樹模型不足等門檻成立時加入；SPC 保留，PCA／Isolation Forest 作異常基線，Autoencoder 為條件式 Challenger；所有模型共用資料快照、切分、指標、manifest、升版及回退規則。
- 理由：預留擴充點但不過早增加依賴與維護負擔，並確保模型比較公平、可重現、可回退。
- 影響與限制：已同步 AGENTS／SKILL 與 `define-model-selection-governance` Change；尚未訓練任何模型，異常分數不得視為 NG 機率。
- 取代關係／證據：不適用；來源為使用者模型規劃問題及本次修改授權。

## ADR-004：v2 合成資料獨立輸出並以區段聯合良率約 80% 為目標

- 狀態：Accepted
- 日期與決策時間：2026-11-02；2026-11-02 02:10:59 +08:00 (Asia/Taipei)
- 背景：舊資料僅 25 卷且良率過高，外觀 NG 樣本極少，無法支援完整卷時間分割、分類評估、SPC 漂移學習及五目標聯合風險。
- 決策：v2 預設生成 200 卷、每卷約 100 個 canonical 區段、共約 20,000 區段，依時間分成 120／40／40 卷；五項品質的區段聯合良率須為 78%～82%，以穩定、輕度及強度漂移的合理製程機制產生；完整合成真值與模擬抽檢分離。輸出至 `generated_data/v2/`，保留舊 `raw data/` 作歷史比較且不作 v2 預設輸入。
- 理由：提供足量、跨卷且含多種失敗機制的 NG，同時避免刪除歷史資料或讓兩代資料混用。
- 影響與限制：80% 是合成區段聯合良率，不是整卷良率或真實產線承諾；模擬參數與規格仍需製程／品質負責人確認。
- 取代關係／證據：延伸 ADR-001 的連續耐熱目標；v2 將 300 °C 保留為最低允收值，因「最高通過溫度」是越高越佳的特性，330 °C 不再作拒收上限，僅可作生成／顯示範圍參考。此點取代 ADR-001 中把 330 °C 記為 USL 的模擬假設。對應 `regenerate-training-data-v2` Change 與使用者本次資料生成授權。
