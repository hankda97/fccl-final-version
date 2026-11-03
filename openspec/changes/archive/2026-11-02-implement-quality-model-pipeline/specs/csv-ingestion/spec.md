# Spec Delta

## ADDED Requirements

### Requirement: DATA-05 Canonical 模型投影載入

系統 SHALL 讓正式模型與 Streamlit 消費由七表整合流程產生的版本化 canonical projection，並驗證 dataset、schema、alignment、feature、label、spec 及 lineage manifest；C 端 MUST NOT 以一般 CSV loader 自行重建七表 JOIN 或猜測缺少的對齊關係。

#### Scenario: 相容投影載入

- **WHEN** canonical projection 的 manifest、欄位、單位、版本與所選模型相容
- **THEN** 系統保留 `aligned_sample_id`、卷、材料 MD、時間與來源 lineage，並逐目標提供推論及圖表適用性

#### Scenario: 投影與模型版本不相容

- **WHEN** projection 的 schema、feature order、單位、label source 或版本不符合模型 manifest
- **THEN** 正式模型功能 SHALL 明示不相容原因並停止推論，既有資料預覽、有效 SPC 與 C Mock 不被偽裝成正式結果

#### Scenario: 使用者直接提供七份來源表

- **WHEN** C 一般上傳入口收到未經 builder 處理的七份來源 CSV
- **THEN** 系統可保留來源檢查，但不得在 UI 內臨時平面合併或宣稱正式模型資料已就緒
