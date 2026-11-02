# 成員 C 第一批交付操作指南

交付範圍：C1～C7 與三模式第一階段工作區。原始 Roadmap 維持 **29／39**，三模式擴充獨立 **20／20**。完整模式 B／C 模擬器、C8 整體交付及 C9 正式資料／模型整合尚未完成。

## 獨立環境

本批只新增 `requirements-c.in`、`requirements-c.txt`、`requirements-c-test.txt`，沒有指定 A／B 全組的共同依賴，也不修改已有環境。以下命令適用獨立的 C 測試副本：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-c-test.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

`requirements-c.txt` 保留已驗證的 C 版本鎖定（包括 pytest）；test 清單再加 Playwright。只有啟動 UI 時可先安裝 `requirements-c.txt`。這些清單未加入正式 B 模型或 SHAP 訓練依賴。`requirements-c.in` 為可讀來源，實測使用鎖檔，不能把較鬆的最低版本當成全部已驗證。

## 操作

1. 預設模式 A：AI 品質預測與關鍵因子分析。保留 CSV／Mock 載入、批次與時間篩選、產品／環境資訊及四個功能 Tabs。
2. 側欄選「C 專用 Mock」，再按「載入 Mock 資料」。fixtures 為明示的合成示範，不代表真實產線。正式上傳資料仍需明確欄名／單位及來源驗證。
3. SPC 使用同次獨立試片的 C 測試子組及獨立事前歷史基準；CL／UCL／LCL 固定，不因新監控或 What-if 重算。外觀二元標籤不套 X-bar。缺基準或子組無效時無法判定。
4. What-if 固定所選材料區段；線速預設可調，熟化／壓合解鎖只開啟本機模擬欄位。四項連續預測、外觀 NG 示範風險、差值與建議不是實測，也不保證因果改善；Mock risk 不是正式校準機率。
5. AI 圖表保留 Pearson Heatmap、SHAP Summary／Dependence 接點。公式 Mock 沒有真正 SHAP，正常畫面會說明待 B／C9 整合，不用公式係數冒充解釋。
6. 選「CSV 定時回放」後，可播放／暫停、單步、重新開始及調整播放倍率。僅依可信可得時間釋出特徵／品質；缺時間證據的通道保持不可用。倍率不是製程線速。
7. 切至 B／C 只會顯示 unavailable 工作區及停用動作。返回 A 保留來源、有效固定情境與回放位置，但不自動播放。重新開始回放會按既有規則使情境失效，需主動重選。

## 必要資料與責任

`c_dashboard/data/fixtures.py` 及 `c_dashboard/spc/sources.py` 直接讀取 `tests/fixtures/c_mock`、`c_spc`。這些是目前的執行依賴，須隨程式交付；`c_replay`、`c_visualization` 亦供回歸測試。

組長 `generated_data/v2` 七表、`raw data`、生成器及 A／B 模型契約保持不變。本入口只消費 C 既有單 CSV／Mock／明確來源投影，不做正式七表 JOIN、跨站 MD 配對或標籤重測選取。正式模型、校準 NG 機率及真正 SHAP 計算仍屬 C9。未實作機台控制，也未新增當下預測良率。

## 規格與驗收

七份 C 正式主規格位於 `openspec/specs/`，六個完整 C Archive 位於 `openspec/changes/archive/`。組長原有三個 active Change 全部保留；本批不歸檔它們，也不把待跨組確認的數值視為正式規則。

本批不合併共用 AGENTS／SKILL／DEV／ADR／TCP 或原指南，避免 ID 與責任混淆；歷史快照及 raw evidence 不列入候選交付。[C 交付驗收摘要](C_DELIVERY_ACCEPTANCE.md)描述本批成熟度；整合目錄的 `INTEGRATION_TEST_REPORT.md` 記錄此次真正執行結果。

目前兩個 browser 測試依賴 Windows Chrome 的標準安裝路徑。非 Windows CI 尚需另行確認最小可攜性調整，本批不修改測試原碼。Archive 中九份 Markdown 的 CRLF 可能被遠端 `.gitattributes` 正規化為 LF；工作副本保留原 bytes，Dry-run manifest 另列預期轉換，不改寫歷史 SHA 證據。
