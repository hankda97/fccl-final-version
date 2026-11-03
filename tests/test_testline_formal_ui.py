from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_app_routes_only_to_formal_single_mode_control_room() -> None:
    app = (ROOT/"app.py").read_text(encoding="utf-8")
    assert "render_testline_control_room" in app
    assert "render_mode_navigation" not in app and "render_unavailable_mode" not in app


def test_formal_ui_has_four_pages_five_spc_four_targets_and_no_mock_or_shap_navigation() -> None:
    source=(ROOT/"c_dashboard/testline_control_room.py").read_text(encoding="utf-8")
    for page in ("生產控制台","SPC 詳細監控","What-if／Heatmap","Run 紀錄"): assert page in source
    for signal in ("dry_thickness_mean_um","curing_temp_c","exhaust_airflow_m3_h","line_speed_m_min","lamination_pressure_mpa"): assert signal in source
    assert "QUALITY_LABELS" in source and "appearance_ng" not in source and "預測良率" not in source
    assert "Mock" not in source and "模式 A" not in source and "模式 C" not in source
    assert "@st.cache_resource" in source
