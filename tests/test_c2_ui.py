from pathlib import Path

from streamlit.testing.v1 import AppTest

from c_dashboard.data.session import selected_rows
from c_dashboard.state import SegmentSnapshot, WORKSPACE_KEY

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "c_mock"


def new_app():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not app.exception
    return app


def load_mock(app, label="正常模擬資料"):
    app.radio(key="ui_source_choice").set_value("C 專用 Mock").run()
    app.selectbox(key="ui_mock_scenario").set_value(label).run()
    app.button(key="ui_load_mock").click().run()
    assert not app.exception
    return app


def upload(app, payload, name="uploaded.csv"):
    app.radio(key="ui_source_choice").set_value("上傳 CSV").run()
    app.file_uploader(key="ui_csv_upload").set_value((name, payload, "text/csv")).run()
    app.button(key="ui_load_upload").click().run()
    assert not app.exception
    return app


def test_mock_load_preview_context_and_filters():
    app = load_mock(new_app())
    workspace = app.session_state[WORKSPACE_KEY]
    assert len(workspace.data.dataset.frame) == 150
    assert any("非真實產線" in item.value for item in app.caption)
    assert any("C-DEMO-01" in item.value for item in app.text)
    # C3 adds tables ahead of Data Inspection; keep checking the actual raw preview.
    preview = next(item.value for item in app.dataframe if "sample_id" in item.value.columns)
    assert len(preview) == 150
    assert app.metric[0].value == f"{workspace.spc.result.targets[0].latest.mean:.6g}"
    assert app.metric[4].value != "—"  # Explicitly labeled Mock risk, separate from measured SPC.
    token = workspace.data.source_id[:12]
    app.selectbox(key=f"ui_batch_{token}").set_value("M-B02").run()
    app.select_slider(key=f"ui_time_{token}").set_value((
        "2026-11-01T08:16:00+08:00", "2026-11-01T08:18:00+08:00",
    )).run()
    assert not app.exception
    workspace = app.session_state[WORKSPACE_KEY]
    assert len(selected_rows(workspace)) == 15
    expected = selected_rows(workspace).iloc[-1].ambient_temp_c
    assert app.sidebar.metric[0].value == f"{expected:.2f}"
    preview = next(item.value for item in app.dataframe if "sample_id" in item.value.columns)
    assert len(preview) == 15


def test_native_upload_loads_csv_and_invalid_replacement_retains_good_data():
    app = upload(new_app(), (FIXTURES / "normal.csv").read_bytes())
    first_id = app.session_state[WORKSPACE_KEY].data.source_id
    assert app.session_state[WORKSPACE_KEY].data.dataset.source_kind == "upload"
    assert any("來源待確認" in item.value for item in app.caption)
    assert not any("示範設定" in item.value for item in app.warning)
    upload(app, b"", "empty.csv")
    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.data.source_id == first_id
    assert not workspace.data.last_attempt.accepted
    assert any("上一份有效資料" in item.value for item in app.error)


def test_partial_quality_invalid_rows_and_source_switch_reset_state():
    app = load_mock(new_app())
    workspace = app.session_state[WORKSPACE_KEY]
    workspace.what_if.selected = SegmentSnapshot("test", "B", "S", "2026-11-01T08:00:00+08:00")
    workspace.what_if.parameters["line_speed_m_min"] = 1.2
    workspace.what_if.advanced_unlocked = True
    workspace.replay.cursor = 7
    load_mock(app, "部分品質欄位缺失")
    workspace = app.session_state[WORKSPACE_KEY]
    assert workspace.what_if.selected is not None
    assert workspace.what_if.selected.source_id == workspace.data.source_id
    assert workspace.what_if.parameters == {}
    assert not workspace.what_if.advanced_unlocked
    assert workspace.replay.cursor == 0
    assert "heat_resistance_c" not in workspace.data.dataset.frame
    assert any(item.code == "MISSING_COLUMN" for item in workspace.data.dataset.issues)
    load_mock(app, "無效值與重複紀錄")
    assert not app.exception
    assert "INVALID_NUMBER" in {item.code for item in app.session_state[WORKSPACE_KEY].data.dataset.issues}


def test_mapping_configuration_via_upload_controls():
    payload = (FIXTURES / "normal.csv").read_text(encoding="utf-8").replace("product_batch", "批號").encode()
    app = new_app()
    app.text_area(key="ui_mapping_json").set_value('{"columns":{"product_batch":{"column":"批號"}}}').run()
    upload(app, payload)
    assert app.session_state[WORKSPACE_KEY].data.dataset.accepted
    assert "COLUMN_MAPPED" in {item.code for item in app.session_state[WORKSPACE_KEY].data.dataset.issues}


def test_filter_empty_range_and_tabs_preserve_loaded_source():
    app = load_mock(new_app())
    workspace = app.session_state[WORKSPACE_KEY]
    token = workspace.data.source_id[:12]
    app.selectbox(key=f"ui_batch_{token}").set_value("M-B02").run()
    app.select_slider(key=f"ui_time_{token}").set_value((
        "2026-11-01T08:00:00+08:00", "2026-11-01T08:01:00+08:00",
    )).run()
    assert not app.exception
    assert selected_rows(app.session_state[WORKSPACE_KEY]).empty
    source_id = app.session_state[WORKSPACE_KEY].data.source_id
    app.session_state["ui_workspace_tabs"] = "AI 圖表"
    app.run()
    assert not app.exception
    assert app.session_state[WORKSPACE_KEY].data.source_id == source_id
    assert app.session_state[WORKSPACE_KEY].data.selected_batch == "M-B02"
