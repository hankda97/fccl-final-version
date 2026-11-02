"""Focused C1 presentation checks; not C8's real browser/replay acceptance."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from c_dashboard.state import SegmentSnapshot, WORKSPACE_KEY
from c_dashboard.ui.tabs import TAB_LABELS

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_empty_dashboard_preserves_all_feature_areas_without_fake_results():
    app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
    assert not app.exception
    assert app.title[0].value == "FCCL 品質預測與 SPC 動態監控"
    assert [tab.proto.label for tab in app.get("tab")] == list(TAB_LABELS)
    headings = {element.value for element in app.subheader}
    assert {
        "產品規格", "環境參數", "監控摘要", "AI Alarm", "X-bar 管制圖",
        "What-if 參數比較", "具體調參建議", "Heatmap", "SHAP Summary Plot",
        "SHAP Dependence Plot", "CSV 匯入與欄位驗證",
    } <= headings
    assert all(metric.value == "—" for metric in app.metric)
    assert all(button.disabled for button in app.button)
    assert not app.get("file_uploader")[0].proto.disabled  # C2 intentionally enables upload.
    assert not app.error
    assert any("尚未判定" in item.value for item in app.info)
    assert any("C4／C5 What-if" in item.value for item in app.info)
    assert not app.get("plotly_chart")
    assert not app.get("imgs")
    assert any("真實產線" in item.value for item in app.caption)


def test_rerun_and_tab_state_do_not_reset_csv_cursor_or_fixed_context():
    app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
    workspace = app.session_state[WORKSPACE_KEY]
    workspace.data.csv_bytes = b"test-only unparsed bytes"
    workspace.data.selected_batch = "TEST-B"
    workspace.replay.cursor = 5
    workspace.what_if.selected = SegmentSnapshot(
        "test", "TEST-B", "TEST-S", "2026-11-01T08:00:00+08:00"
    )
    workspace.what_if.parameters["line_speed_m_min"] = 1.2
    workspace.what_if.advanced_unlocked = True

    for label in ("AI 圖表", "資料檢查", "What-if"):
        app.session_state["ui_workspace_tabs"] = label
        app.run()
        assert not app.exception
        current = app.session_state[WORKSPACE_KEY]
        assert current.data.csv_bytes == b"test-only unparsed bytes"
        assert current.data.selected_batch == "TEST-B"
        assert current.replay.cursor == 5
        assert current.what_if.selected.segment_id == "TEST-S"
        assert current.what_if.parameters == {"line_speed_m_min": 1.2}
        assert current.what_if.advanced_unlocked
