# Spec Delta

## ADDED Requirements

### Requirement: DG-07 Synthetic v3 製程與材料契約

Synthetic v3 SHALL 為每個材料區段提供塗佈、熟化、壓合及環境的可用特徵，至少包含線速、塗佈間隙、乾膠厚度五點與聚合、熟化溫度、排風量、熟化時間、壓合溫度、壓力與時間；setpoint、actual、單位、站別與可得時間 MUST 可追溯。

#### Scenario: 生成 v3 區段
- **WHEN** 一個材料區段完成生成
- **THEN** 三站參數、五點厚度、區段位置、品質可得時間與版本齊全，且未來站別特徵不出現在較早可得時間

#### Scenario: 特徵值驗證
- **WHEN** 生成值超出 UI、配方或模型訓練範圍
- **THEN** metadata 分別記錄其所屬範圍及事件原因，不裁切成大量相同邊界值

### Requirement: DG-08 v3 規模、分割與隔離

v3 MUST 產生 200 卷、約 20,000 個完成區段，按互斥完整卷與時間順序切為 120／40／40 train／validation／test；v3 輸出 SHALL 與 raw data、v2、demo Run 及 SPC reference 分開。

#### Scenario: 完整生成驗證
- **WHEN** v3 生成完成
- **THEN** manifest 證明卷不跨 split、demo seed／Run 不在訓練 split、輸出路徑與 v2 不互相覆寫

### Requirement: DG-09 v3 產品、配方與預設範圍

v3 MUST 使用 `FCCL-DEMO-001` 與 `SIM-RECIPE-3.0` 的版本化假設：主要 setpoint 為線速 4.80 m/min、塗佈間隙 28.0 μm、熟化 171 °C、排風 2100 m³/h、熟化 12.5 min、壓合 181 °C、壓力 2.55 MPa；乾膠厚度目標 25.0 μm、允收 23–27 μm。

#### Scenario: 配方 metadata
- **WHEN** 生成器載入預設 v3 設定
- **THEN** metadata 另記主要參數的配方範圍與 UI 範圍，以及進階參數塗佈溫度 82 °C、黏度 1180 mPa·s、壓合時間 18 min 的版本化假設

#### Scenario: 範圍不可互換
- **WHEN** 驗證器檢查生成資料
- **THEN** 產品允收、配方範圍、UI 範圍與資料實際分布分欄保存，不用任一範圍取代另一範圍

### Requirement: DG-10 模擬 Run 與訓練資料隔離

生成器 MUST 使用不同於控制台 demo Run 的 seed 與識別；控制台產生的 runtime_data 不得自動併入 v3、良率調整或 SPC reference。

#### Scenario: demo Run 完成
- **WHEN** runtime_data 新增一個 completed Run
- **THEN** v3 manifest、split、hash、資料列與模型訓練入口保持不變
