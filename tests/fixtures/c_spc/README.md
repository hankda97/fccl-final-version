# C3 專用 SPC 測試設定

profile.json 以內容 SHA-256 綁定既有 C2 Mock 與獨立 history.csv，聲明 C 專用取樣條件與版本。history 不加入一般資料選單；上傳來源不因欄名相同套用此設定。

cases.json 保存 n=5／n=3 手算答案與故障情境目錄。測試由這些值建立帶不同組／試片識別的歷史表，不生成 A 的正式時序資料。25 組與固定 n 只是 C 測試；穩定性與基準仍須經程式驗證，不能信任檔名或 metadata 的預期警報。

故障樣本在 pytest 暫存／記憶體中對手算表做明確變更；原 c_mock CSV、builder 及 metadata 一律保留 bytes，不改 C2 可重現性。
