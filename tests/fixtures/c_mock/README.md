# C 專用 Mock Fixtures

這些檔案只供成員 C 載入、顯示與測試，**不是成員 A 的正式生成器／CSV 契約，也不是真實產線資料**。`build.py` 是小型固定測試資料建構器，不包含 FCCL 製程機理、模型訓練或正式取樣規則。

- `normal.csv`：150 列、30 次取樣、每次 5 個獨立試片，包含兩個批次、材料區段／位置與所有製程／品質欄位。
- `history.csv`：獨立 125 列、25 組，資料與監控識別不重疊，時間早於監控；僅為歷史穩定測試資料，**C2 不計算或宣稱已驗證 SPC 界限**。
- `out_of_control.csv`、`trend.csv`、`same_side.csv`：已知偏移／六組上升／九組同側情境；實際警報規則驗收待 C3。
- `partial_quality.csv`、`no_quality.csv`、`ungrouped.csv`：資料不足時的用途別降級情境；不補造缺少目標或子組。
- `invalid_values.csv`：壞時間、濕度超界、非數字、缺品質值及重複紀錄。
- `missing_columns.csv`：缺少 timestamp 的無效識別來源。
- `metadata.json`：來源、單位、產品／配方、歷史時間、子組、seed、版本與情境真值；真值不可送進模型。
- `settings.json`：可配置的 C 示範規格與門檻，非團隊正式允收或推薦策略。

測試預設 n=5、歷史 25 組，可由建構器參數改變；不能要求 A 採用相同大小或欄位。測試會另建暫存目錄比較每個 CSV／JSON 位元組，確認 seed=42 及版本下可重現。

只在有意更新測試版本時於專案根目錄執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 tests/fixtures/c_mock/build.py
```

此命令重建本資料夾具名 CSV／JSON。一般使用儀表板只讀取已建立的 fixture，不需重建。
