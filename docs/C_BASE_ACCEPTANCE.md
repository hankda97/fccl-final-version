# C1＋C2 基礎交付驗收

本文件只對應收斂後 `fccl-streamlit-dashboard` 的兩份 delta（8 需求／14 情境），不是 C8 全案交付驗收。原 28 需求／47 情境／39 任務的完整追蹤見 [Roadmap](CHANGE_ROADMAP.md)，原完整情境不因本表的局部驗收而視作全部通過。

## 實際執行證據

- 環境沿用 Python 3.11.17、Streamlit 1.66.1、pytest 9.2.0 與既有鎖檔，程式／測試／fixtures／依賴均未修改。
- 本輪重新執行 `.venv/Scripts/python.exe -X utf8 -m pytest -q`：**40 passed in 7.82s**，原 C1 9 項、C2 31 項，含 AppTest、模組匯入與本機 Streamlit 健康端點／首頁啟動檢查。
- `openspec validate fccl-streamlit-dashboard --strict` 通過；apply instructions 回報 `all_done`，8／8、remaining 0。
- 依原始檔 SHA-256 比對確認 Python、測試、fixtures、鎖檔及主 specs 未改；文件保全檢查另見 DEV-20261101-014。

## 需求／情境／測試對照

下表測試函式位於 [tests](../tests/)，均為既有測試，本輪沒有新增或修改測試。每列為本案基礎能力的通過證據；涉及其他階段的原完整情境仍在 Roadmap 列未完成。

| 本案需求 | 本案情境 | 既有測試檔／函式 | 結果與限制 |
|---|---|---|---|
| WS-01 | 初次開啟與無資料畫面 | test_c1_ui.py → test_empty_dashboard_preserves_all_feature_areas_without_fake_results；test_c1_startup.py 兩項 | 通過；沒有分析計算 |
| WS-01 | 載入後功能可尋得 | test_c1_ui.py → test_empty_dashboard_preserves_all_feature_areas_without_fake_results；test_c2_ui.py → test_mock_load_preview_context_and_filters | 通過；功能區是占位，只有資料檢查可操作 |
| WS-02 | 分頁切換與同源重載 | test_c1_ui.py → test_rerun_and_tab_state_do_not_reset_csv_cursor_or_fixed_context；test_c2_ui.py → test_filter_empty_range_and_tabs_preserve_loaded_source；test_c2_session.py → test_same_source_reload_and_unchanged_filters_do_not_interrupt_work、test_successful_source_switch_clears_dependent_state_but_not_model_identity | 通過；注入游標／情境只驗證狀態容器，不是動態功能 |
| WS-03 | 資料可用但模型尚未接入 | test_c1_state.py → test_unavailable_adapter_never_invents_predictions；test_c1_ui.py → test_empty_dashboard_preserves_all_feature_areas_without_fake_results；test_c2_ui.py → test_mock_load_preview_context_and_filters | 通過；正式與公式模型皆未接入 |
| WS-04 | 部分品質資料缺失 | test_c2_loader.py → test_partial_quality_and_no_quality_still_allow_data_and_feature_inspection；test_c2_ui.py → test_partial_quality_invalid_rows_and_source_switch_reset_state | 通過；只驗證資料與輸入完整度 |
| WS-04 | 檢視未實作的調參區 | test_c1_ui.py → test_empty_dashboard_preserves_all_feature_areas_without_fake_results | 通過；解鎖停用，沒有機台控制 |
| DATA-01 | 未排序的有效資料 | test_c2_loader.py → test_normal_bom_and_identification、test_stable_sort_and_batch_time_filter_keep_original_rows；test_c2_ui.py → test_mock_load_preview_context_and_filters、test_filter_empty_range_and_tabs_preserve_loaded_source | 通過；包含空篩選結果 |
| DATA-01 | 無法解析的檔案 | test_c2_loader.py → test_bad_csv_is_rejected（參數化）、test_non_csv_and_missing_identifiers；test_c2_session.py → test_failed_attempt_preserves_previous_valid_data_and_filters；test_c2_ui.py → test_native_upload_loads_csv_and_invalid_replacement_retains_good_data | 通過；原生 uploader 注入測試 CSV |
| DATA-02 | 部分品質未量測 | test_c2_loader.py → test_partial_quality_and_no_quality_still_allow_data_and_feature_inspection、test_missing_features_and_no_subgroup_are_local_capability_limitations | 通過；不補造品質欄與數值 |
| DATA-02 | 型別或物理範圍錯誤 | test_c2_loader.py → test_invalid_times_numbers_missing_and_duplicates_are_reported_without_imputation、test_whitespace_normalization_is_reported_and_original_values_preserved、test_availability_order_and_finite_numeric_values | 通過；原值追溯、無效與重複排除候選輸入 |
| DATA-03 | Mock 與其他來源結構不同 | test_c2_loader.py → test_missing_features_and_no_subgroup_are_local_capability_limitations | 通過；無子組可預覽，不驗證 X-bar 適用 |
| DATA-03 | 已知異常與無效資料情境 | test_c2_fixtures.py 三項；test_c2_ui.py → test_partial_quality_invalid_rows_and_source_switch_reset_state | 通過；重建、歷史獨立／先行、組大小配置及已知值，不是異常偵測通過 |
| DATA-04 | 不同欄名與單位的測試上傳 | test_c2_loader.py → test_explicit_names_units_and_timezone_mapping、test_naive_time_is_not_silently_localized、test_bad_mapping_units_and_collisions_are_reported；test_c2_session.py → test_mapping_errors_and_mapping_version_identity；test_c2_ui.py → test_mapping_configuration_via_upload_controls | 通過；僅 C 映射機制，不是 A 正式契約 |
| DATA-04 | 僅有 C Mock 或尚未正式整合的上傳 | test_c2_ui.py → test_mock_load_preview_context_and_filters、test_native_upload_loads_csv_and_invalid_replacement_retains_good_data | 通過；Mock 標示及上傳不套示範規格 |

## Archive 判定與未完成界線

本案八項任務已驗收、兩份基礎 spec 可追溯，strict 通過且沒有 A／B 前置阻礙，具備進入 Archive 的條件。**本次依指示尚未 Archive，也未同步 openspec/specs/**；先由使用者確認需求保留情況，後續依 Archive 技能完成同步與歸檔檢查。

未完成的 SPC、模型、可操作 What-if、Alarm 邏輯、Heatmap／SHAP、回放、整體交付與正式整合均由六份後續計畫保留。沒有執行真實瀏覽器 timer、正式來源／模型／真正 SHAP 或產線驗證，不以 40 項基礎測試代替那些驗收。

## 已完成 Archive｜2026-11-01 22:28:30 +08:00

使用者已確認並授權歸檔；目前 [基礎 Change](../openspec/changes/archive/2026-11-01-fccl-streamlit-dashboard/tasks.md) 已移至 Archive（8／8）。兩份基礎規格已同步至 openspec/specs/，Purpose 與全部需求／情境逐項一致，沒有 delta 操作標頭；主規格 strict 與 archived 任務檢查均通過。此更新取代上節尚未歸檔的時點描述，驗收範圍不變，詳見 DEV-20261101-015。

本輪只執行同步／歸檔與文件檢查，沒有修改 Python 或重跑 pytest；40 項測試證據沿用 DEV-20261101-014，程式／測試／fixtures／依賴雜湊保持一致。未完成能力及六份後續計畫均未升格為已交付規格。

