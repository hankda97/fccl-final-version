# Design：合成資料 v2

## 規模

- 200 rolls；120 train、40 validation、40 test。
- 每卷 100 個 final canonical segments，合計 20,000。
- coating、curing、lamination 各自使用材料 MD 區間，透過 traceability 對齊。
- inspection 包含線上外觀、每卷固定數量實驗室樣本與整卷資格檢驗。

## 良率

良率以 final segment 五項品質聯合判定。生成器先建立製程與漂移，再以版本化 capability calibration 調整合成製程能力，不能直接改標籤或規格。預設驗收為 78%～82%。

## 失敗機制

- 環境濕度與熟化條件影響剝離及耐熱。
- 塗佈間隙、黏度、流量與張力影響厚度及外觀。
- 壓合溫度、壓力與保持時間影響尺寸及外觀。
- 漂移事件包含 curing temperature、humidity、coating gap、lamination pressure。

## 輸出隔離

新資料輸出至 `generated_data/v2/`。舊 `raw data/` 保留為歷史資料，不作 v2 預設輸入。metadata 記錄 active dataset path、schema version、seed、公式版本、規格、分割、數量、良率及檔案 hash。
