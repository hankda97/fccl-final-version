# Synthetic v3 測試線資料字典

本文件是 `build-testline-simulation-control-room` Gate 1 的人類可讀契約。所有值均為 Synthetic demo 假設，不是工廠標準。

## 邊界與責任

- 使用者表面：單一 Mode B；四個連續品質目標，不含外觀、預測良率或 SHAP 一般入口。
- 資料：A 負責可重現 v3、穩定 reference 與漂移真值隔離；B 負責四目標 allowlist、模型與支援範圍；C 負責 Run、模擬器、製程 SPC、Alarm 與 UI。
- 儲存：Run 僅在 `runtime_data/testline_runs/<run_id>/`；訓練、reference、v2、artifact 與 demo Run 互相隔離。

## 共通識別與時間

所有時間使用含時區 ISO-8601；`run_id`、`segment_id`、`event_id` 在所屬 Run 唯一；`tick_sequence` 嚴格遞增。`schema_version` 初版為 `testline-v3.0`。

## 五份 Run CSV

| 檔案 | 一列粒度 | 必要內容 |
|---|---|---|
| `process_signals.csv` | 一個 tick／站別／訊號 | run、tick、時間、材料、station、signal、actual、unit、setpoint、quality flag |
| `material_segments.csv` | 一個材料區段 | 三站進出時間、MD 半開區間、完成與品質可得時間 |
| `parameter_events.csv` | 一次原子參數提交 | event、時間、站別、舊／新值 JSON、適用材料邊界、來源 |
| `spc_events.csv` | 一個 SPC 事件群 | signal、chart、severity、event kind、規則、開始／結束、影響點、baseline |
| `quality_predictions.csv` | 一個完成區段／目標 | target、prediction、unit、模型版本、輸入截止、支援狀態 |

## 訊號與單位

| signal | station | unit | SPC |
|---|---|---|---|
| `dry_thickness_um`（五點） | coating | `um` | X-bar／R |
| `line_speed_m_min` | coating | `m/min` | I-MR |
| `coating_gap_um` | coating | `um` | I-MR（可記錄） |
| `coating_temp_c` | coating | `degC` | I-MR（詳細頁） |
| `coating_viscosity_mpa_s` | coating | `mPa*s` | I-MR（詳細頁） |
| `curing_temp_c` | curing | `degC` | I-MR |
| `exhaust_airflow_m3_h` | curing | `m3/h` | EWMA |
| `curing_time_min` | curing | `min` | 配方／事件 |
| `lamination_temp_c` | lamination | `degC` | I-MR |
| `lamination_pressure_mpa` | lamination | `MPa` | I-MR |
| `lamination_time_min` | lamination | `min` | 配方／事件 |

## 四個品質預測

`peel_strength_n_mm` (`N/mm`)、`dimensional_stability_md_pct` (`pct`)、`dimensional_stability_td_pct` (`pct`)、`heat_resistance_c` (`degC`)。品質僅在三站完成及延遲到期後產生；不得複製舊區段或使用未來訊號。

## Manifest

`manifest.json` 記錄 schema、產品、配方、seed、情境、狀態（running／completed／interrupted／error）、開始／結束／checkpoint 時間、版本、每檔列數與 SHA-256。完成 Run 不觸發訓練或 baseline 更新。
