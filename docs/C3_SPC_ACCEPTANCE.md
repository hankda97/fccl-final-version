# C3 SPC 品質監控與異常警報驗收

Change：[fccl-spc-monitoring](../openspec/changes/archive/2026-11-01-fccl-spc-monitoring/proposal.md)。本案只交付 C Mock 快照 SPC，不包含模型預測、可操作 What-if、Heatmap／SHAP、回放或正式 A／B 整合。Apply 已完成；使用者另行授權後於 2026-11-01 23:22:59 +08:00 完成 Archive，驗收範圍不變。

## 實際執行結果

| 檢查 | 命令／方式 | 結果 |
|---|---|---|
| 全套 pytest | `.venv/Scripts/python.exe -X utf8 -m pytest -q` | 最終 **107 passed in 51.21s**；原 C1＋C2 40 項、C3 67 項 |
| C3 UI 補強重測 | `.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_c3_ui.py` | **11 passed in 17.98s**；另核對既有 Mock 的 M-G010 超界、M-G008 六點上升、M-G011 九點同側 |
| AppTest 總範圍 | test_c1_ui、test_c2_ui、test_c3_ui | 合計 **18 個案例**；涵蓋正常／偏移／趨勢／同側、部分品質／無品質／無子組／無效值、原生上傳／映射、篩選／分頁／失敗保留及雙區事件 |
| Python 語法 | `python -X utf8 -m compileall -q app.py c_dashboard tests` | 通過 |
| 模組匯入 | 顯式匯入 app、全部九個 spc 模組接點與兩個新 UI 模組 | C3_IMPORT_OK；未要求 A／B 模型 |
| Streamlit 啟動 | 全套包含 test_c1_startup 的獨立子程序／健康端點／首頁測試 | HTTP 200；測試結束停止子程序 |
| 依賴相容 | `uv pip check --python .venv/Scripts/python.exe` | 39 個既有套件相容，沒有新增／升級依賴 |
| 圖表結構 | 使用已安裝 Altair 6.3.0 的 LayerChart.from_dict(validate=True) | 四目標 Vega-Lite 圖表結構通過；僅驗證，不新增 runtime 依賴 |
| OpenSpec | `openspec validate fccl-spc-monitoring --strict` | 通過；只有 tasks 勾選，未同步 main specs／未歸檔 |
| 保全 | 原始檔 SHA-256／原日誌前綴與需求矩陣核對 | 詳見 DEV-20261101-017；C2 原 Mock、主 specs、archive、完整快照與後續未交付功能保留 |

C1 空畫面仍不造數值；C2 載入 Mock 後的摘要預期隨 C3 改為實測均值，CSV 預覽測試以 sample_id 欄辨識，未刪除載入／映射／篩選／原值追溯斷言。畫面紅字使用 Streamlit 原生 error 元素，兩區事件 payload／ID 相同。AppTest／圖表 payload 不是 C8 真實瀏覽器或 C7 timer 驗收。

逐目標單位不符的局部降級另由 test_c3_baseline.py 的 test_one_target_unit_mismatch_only_disables_that_target 驗證；固定監控起點之前的明確切片由 test_c3_service.py 的 test_explicit_slice_before_monitoring_origin_cannot_use_future_calibration 驗證，不能套用對該觀測而言屬未來的基準。兩項均包含於最終 107 項。

## 31 個規格情境逐項對照

原題名保持與本 Change 三份 delta 一致。每個案例已由下列實際執行的測試驗證；參數化測試覆蓋 n、錯誤種類或情境組合。此處 31 是本案細化情境，不重複加入原全案 47 情境分母。

| Requirement／情境碼 | 情境原標題 | 可追溯測試 | 結果 |
|---|---|---|---|
| DATA-02/S01 | 部分品質未量測 | [test_c3_subgroups.py](../tests/test_c3_subgroups.py)：`test_loadable_features_do_not_imply_spc_and_partial_targets_keep_preview` | 通過（C Mock／介面層） |
| DATA-02/S02 | 型別或物理範圍錯誤 | [test_c2_loader.py](../tests/test_c2_loader.py)：`test_invalid_times_numbers_missing_and_duplicates_are_reported_without_imputation` | 通過（C Mock／介面層） |
| DATA-03/S01 | Mock 與其他來源結構不同 | [test_c3_subgroups.py](../tests/test_c3_subgroups.py)：`test_registered_missing_profile_columns_and_partial_prefix_never_get_filled` | 通過（C Mock／介面層） |
| DATA-03/S02 | 已知異常與無效資料情境 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_real_mock_spc_chart_events_and_two_alarm_areas_share_result` | 通過（C Mock／介面層） |
| WS-01/S01 | 初次開啟與無資料畫面 | [test_c1_ui.py](../tests/test_c1_ui.py)：`test_empty_dashboard_preserves_all_feature_areas_without_fake_results` | 通過（C Mock／介面層） |
| WS-01/S02 | 載入後功能可尋得 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_real_mock_spc_chart_events_and_two_alarm_areas_share_result` | 通過（C Mock／介面層） |
| WS-02/S01 | 分頁切換與同源重載 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_upload_filters_tabs_and_invalid_replacement_keep_c2_behavior_and_spc_identity` | 通過（C Mock／介面層） |
| WS-03/S01 | 資料可用但模型尚未接入 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_real_mock_spc_chart_events_and_two_alarm_areas_share_result` | 通過（C Mock／介面層） |
| WS-04/S01 | 部分品質資料缺失 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_bad_or_partial_measurements_keep_csv_and_honest_target_state` | 通過（C Mock／介面層） |
| WS-04/S02 | 檢視未實作的調參區 | [test_c1_ui.py](../tests/test_c1_ui.py)：`test_empty_dashboard_preserves_all_feature_areas_without_fake_results` | 通過（C Mock／介面層） |
| WS-04/S03 | 實測事件同步與目標切換 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_real_mock_spc_chart_events_and_two_alarm_areas_share_result` | 通過（C Mock／介面層） |
| WS-04/S04 | 目前無法判定但仍有歷史事件 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_latest_invalid_group_keeps_historical_alarm_and_model_unavailable_does_not_hide_it` | 通過（C Mock／介面層） |
| SPC-01/S01 | C Mock 完整子組 | [test_c3_subgroups.py](../tests/test_c3_subgroups.py)：`test_complete_independent_groups_have_expected_mean_range_and_adjacency` | 通過（C Mock／介面層） |
| SPC-01/S02 | 未完成或不可用子組 | [test_c3_subgroups.py](../tests/test_c3_subgroups.py)：`test_bad_rows_are_not_dropped_to_manufacture_complete_group；test_target_missingness_is_local_and_invalid_group_is_a_barrier；test_same_specimen_reused_in_different_groups_is_not_independent_sampling` | 通過（C Mock／介面層） |
| SPC-01/S03 | 無子組依據或未知順序 | [test_c3_subgroups.py](../tests/test_c3_subgroups.py)：`test_missing_whole_group_unknown_order_batch_and_interval_reset_continuity；test_registered_missing_profile_columns_and_partial_prefix_never_get_filled` | 通過（C Mock／介面層） |
| SPC-01/S04 | 部分品質與外觀標籤 | [test_c3_ui.py](../tests/test_c3_ui.py)：`test_bad_or_partial_measurements_keep_csv_and_honest_target_state` | 通過（C Mock／介面層） |
| SPC-01/S05 | 篩選截斷子組 | [test_c3_subgroups.py](../tests/test_c3_subgroups.py)：`test_registered_missing_profile_columns_and_partial_prefix_never_get_filled` | 通過（C Mock／介面層） |
| SPC-02/S01 | 已知歷史資料的手算界限 | [test_c3_baseline.py](../tests/test_c3_baseline.py)：`test_manual_limits_and_negative_dimension_are_not_clipped` | 通過（C Mock／介面層） |
| SPC-02/S02 | 監控出現漂移或改變篩選 | [test_c3_service.py](../tests/test_c3_service.py)：`test_fixed_baseline_filtering_drift_and_latest_invalid_keep_history_distinct` | 通過（C Mock／介面層） |
| SPC-02/S03 | 歷史不足或條件不符 | [test_c3_baseline.py](../tests/test_c3_baseline.py)：`test_bad_history_is_rejected_without_selecting_clean_subset；test_overlap_hash_and_single_target_rejection` | 通過（C Mock／介面層） |
| SPC-02/S04 | 歷史穩定性失敗 | [test_c3_baseline.py](../tests/test_c3_baseline.py)：`test_historical_stability_refuses_mean_and_range_signals` | 通過（C Mock／介面層） |
| SPC-02/S05 | 新來源不能套用 Mock 基準 | [test_c3_controller.py](../tests/test_c3_controller.py)：`test_unknown_upload_does_not_inherit_previous_mock_baseline` | 通過（C Mock／介面層） |
| SPC-03/S01 | 單點超界與界線相等 | [test_c3_rules.py](../tests/test_c3_rules.py)：`test_limit_equality_and_precision_and_multiple_rules` | 通過（C Mock／介面層） |
| SPC-03/S02 | 已知趨勢序列 | [test_c3_rules.py](../tests/test_c3_rules.py)：`test_trend_first_fires_at_sixth_and_overlapping_window_is_not_duplicated` | 通過（C Mock／介面層） |
| SPC-03/S03 | 九點同側與中心線相等 | [test_c3_rules.py](../tests/test_c3_rules.py)：`test_side_first_fires_at_ninth_and_equal_values_still_count` | 通過（C Mock／介面層） |
| SPC-03/S04 | 相等、缺組或條件邊界 | [test_c3_rules.py](../tests/test_c3_rules.py)：`test_equality_invalid_and_explicit_break_reset_sequences` | 通過（C Mock／介面層） |
| SPC-03/S05 | 同組多規則及重跑去重 | [test_c3_service.py](../tests/test_c3_service.py)：`test_same_input_dedup_all_targets_and_meaningful_event_payload` | 通過（C Mock／介面層） |
| SPC-04/S01 | 相同前綴的計算接點比較 | [test_c3_service.py](../tests/test_c3_service.py)：`test_bounded_prefix_no_lookahead_or_input_mutation_and_no_filter_warmup` | 通過（C Mock／介面層） |
| SPC-04/S02 | 測試替身改變情境參數 | [test_c3_controller.py](../tests/test_c3_controller.py)：`test_session_and_what_if_values_do_not_mutate_measured_result` | 通過（C Mock／介面層） |
| SPC-04/S03 | 圖上來源與數值清楚 | [test_c3_chart.py](../tests/test_c3_chart.py)：`test_chart_layers_preserve_raw_points_means_limits_and_negative_dimensions` | 通過（C Mock／介面層） |
| SPC-04/S04 | 基準無效或資料為空 | [test_c3_chart.py](../tests/test_c3_chart.py)：`test_invalid_group_creates_line_break_and_no_baseline_has_no_control_rules` | 通過（C Mock／介面層） |

## 原 C3 任務與分段交付

| 原全案任務 | 本 Change 分解 | 完成證據／仍留後續 |
|---|---|---|
| 3.1 合理子組 | 1.1、2.1～2.3 | 同次試片／大小／條件／四連續目標與外觀不適用；正式取樣留 C9 |
| 3.2 固定歷史 | 1.2、3.1～3.4 | 手算 n=3／5、歷史不足／晚到／重疊／穩定性／零變異、凍結來源版本；真回放更新留 C7 |
| 3.3 規則與去重 | 4.1～4.2、5.3 | 超界、六點、九點、相等／缺組／換批中斷、跨組重用試片、多規則與重跑去重 |
| 3.4 圖表／同步 | 5.1～5.4、6.1～6.2 | X-bar／原始點、同事件雙區紅字、篩選／Session、候選狀態替身隔離；真滑桿留 C4＋C5、真模式比較留 C7 |

17 個實作任務是原四項 C3 的細分，不能將全案 39 改成 52 再混算。C3 本輪驗收完成後，原全案對應為 12／39（C1＋C2 八項與 C3 四項），其他 27 項仍未完成；31 原始未完成項中的 C3 四項有本表證據，其餘完整留在 Roadmap／後續計畫，凍結原始快照不改。

## 成熟度與實際可操作範圍

- 資料：C 專用固定 bytes Mock 與獨立事前歷史。未知上傳可預覽／映射／篩選，但不因欄位相同套 Mock 基準；正式資料未驗收。
- SPC：四連續目標各自判定。外觀僅實測標籤／NG 計數，沒有 X-bar／模型風險。來源、n、組數、條件、歷史時間窗與基準／規則版本可查。
- 不可判定：不畫假界限、不宣稱正常；最新無效與歷史事件分開，仍保留可用目標及資料檢查。只說未偵測所啟用規則，不代表產品符合允收。
- 模型：仍為未接入 Adapter，沒有公式 Mock／RF／SHAP。What-if 候選替身只測隔離，不宣稱滑桿功能完成。
- 未執行：真實瀏覽器 timer、動態回放、正式模型／真正 SHAP／正式品質規格及產線驗證；沒有機台控制或 Git Commit／Push。

啟動與操作見 [儀表板指南](C_DASHBOARD_GUIDE.md)，內部設定／問題碼與事件契約見 [C3 技術說明](C3_SPC_TECHNICAL.md)。歷史資料檔名或 expected_test_cases metadata 不直接生成警報；只對計算結果核對測試真值。基準通過只是 C Mock 的適用／穩定性篩檢，不是現場統計假設的證明。


## Archive 後核對｜2026-11-01 23:22:59 +08:00

17／17 任務及本表 31 情境完成證據已核對，無未解決的重大實作問題。新增 spc-monitoring 與既有兩份主規格的 6 項 MODIFIED 已逐 requirement／Scenario 比對一致；未變更的 DATA-01／04 與既有 Purpose 保留。主規格 strict／Archive 任務檢查通過，C4～C9 與 TCP 待確認事項沒有被同步為已完成能力。

本次為文件同步及歸檔，沒有重跑 pytest；107 passed 的 Apply 證據仍適用，Python／測試／fixtures／依賴內容雜湊未變。C1＋C2 歸檔歷史與五份未來計畫保留。歸檔位置及保全核對見 DEV-20261101-018。

