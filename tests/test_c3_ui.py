from dataclasses import replace
import json

import pytest

from c_dashboard.state import WORKSPACE_KEY
from c_dashboard.spc.config import digest
from c_dashboard.spc.sources import load_c_profile
from c_dashboard.spc.incidents import group_spc_incidents
from c3_support import HEAT, MD, PEEL
from test_c2_ui import load_mock, new_app, upload, FIXTURES


@pytest.mark.parametrize("label", ["正常模擬資料","單點品質偏移情境","上升趨勢情境","同側偏移情境"])
def test_real_mock_spc_chart_events_and_two_alarm_areas_share_result(label):
    app=load_mock(new_app(),label)
    w=app.session_state[WORKSPACE_KEY]
    r=w.spc.result
    assert r is not None and all(t.baseline.valid for t in r.targets)
    assert len(r.target(PEEL).groups)==30
    # C6 adds Heatmap; keep asserting the single SPC chart by its own title.
    charts=[json.loads(c.proto.spec) for c in app.get("vega_lite_chart")
            if "X-bar" in json.loads(c.proto.spec)["title"]]
    assert len(charts)==1
    spec=charts[0]
    assert "X-bar" in spec["title"]
    if label=="正常模擬資料":
        assert not r.events and not app.error
    else:
        assert r.events
        expected = {
            "單點品質偏移情境": ("M-G010", "BEYOND_LIMIT"),
            "上升趨勢情境": ("M-G008", "TREND_UP_6"),
            "同側偏移情境": ("M-G011", "ABOVE_CL_9"),
        }[label]
        assert any((e.subgroup, e.rule) == expected and e.target == PEEL for e in r.events)
        assert len(app.error) < 10
        assert any("incident_id" in item.value.columns for item in app.dataframe)
        assert sum(item.event_count for item in group_spc_incidents(r)) == len(r.events)
    assert app.metric[4].value!="—"  # Formula Mock risk is shown separately from SPC means.
    assert any("外觀不適用 X-bar" in item.value for item in app.caption)
    event_ids=tuple(e.event_id for e in r.events)
    version=r.baseline.version
    app.selectbox(key="ui_spc_target").set_value(MD).run()
    assert not app.exception
    current=app.session_state[WORKSPACE_KEY].spc.result
    assert current==r and tuple(e.event_id for e in current.events)==event_ids
    assert current.baseline.version==version
    # Peel incidents remain queryable even while looking at MD.
    assert sum(item.event_count for item in group_spc_incidents(current)) == len(current.events)
    assert len(app.error) < 10


@pytest.mark.parametrize("label", ["部分品質欄位缺失","無品質量測","無子組識別","無效值與重複紀錄"])
def test_bad_or_partial_measurements_keep_csv_and_honest_target_state(label):
    app=load_mock(new_app(),label)
    r=app.session_state[WORKSPACE_KEY].spc.result
    assert not app.exception
    assert any("sample_id" in item.value.columns for item in app.dataframe)
    if label=="部分品質欄位缺失":
        assert r.target(PEEL).latest.valid
        assert r.target(HEAT).status=="無法判定 SPC 狀態"
        assert app.metric[8].value=="—"
    elif label in ("無品質量測","無子組識別"):
        assert not r.events and all(t.status=="無法判定 SPC 狀態" for t in r.targets)


def test_upload_filters_tabs_and_invalid_replacement_keep_c2_behavior_and_spc_identity():
    app=load_mock(new_app(),"單點品質偏移情境")
    w=app.session_state[WORKSPACE_KEY];original=w.spc.result
    assert original.events
    upload(app,b"","empty.csv")
    assert app.session_state[WORKSPACE_KEY].spc.result==original
    token=w.data.source_id[:12]
    app.selectbox(key=f"ui_batch_{token}").set_value("M-B02").run()
    current=app.session_state[WORKSPACE_KEY].spc.result
    assert current.baseline.version==original.baseline.version and not current.events
    app.select_slider(key=f"ui_time_{token}").set_value(("2026-11-01T08:00:00+08:00","2026-11-01T08:01:00+08:00")).run()
    assert not app.session_state[WORKSPACE_KEY].spc.result.raw
    app.session_state["ui_workspace_tabs"]="資料檢查";app.run()
    assert not app.exception and app.session_state[WORKSPACE_KEY].data.selected_batch=="M-B02"
    upload(app,(FIXTURES/"normal.csv").read_bytes(),"uploaded.csv")
    r=app.session_state[WORKSPACE_KEY].spc.result
    assert r.raw and not r.events and r.baseline is None
    spec=json.loads(app.get("vega_lite_chart")[0].proto.spec)
    assert not any(layer["mark"]["type"]=="rule" for layer in spec["layer"])


def test_latest_invalid_group_keeps_historical_alarm_and_model_unavailable_does_not_hide_it(monkeypatch):
    # Explicit C-only injected profile lets this altered mock exercise the UI contract.
    monkeypatch.setattr("c_dashboard.spc.controller.profile_for_dataset",lambda d:load_c_profile() if d else None)
    app=load_mock(new_app(),"單點品質偏移情境")
    w=app.session_state[WORKSPACE_KEY]
    last=w.data.dataset.frame.index[-1]
    w.data.dataset.frame.loc[last,PEEL]=float("nan")
    app.run()
    r=app.session_state[WORKSPACE_KEY].spc.result
    assert r.target(PEEL).status=="無法判定 SPC 狀態" and r.events
    assert app.metric[5].value=="—"
    assert any("歷史事件" in item.value for item in app.caption)
    assert any("無法判定 SPC 狀態" in item.value for item in app.warning)
    assert any("未接入" in item.value for item in app.caption)
    assert sum(item.event_count for item in group_spc_incidents(r)) == len(r.events)
    assert len(app.error) < 10


def test_unstable_history_is_shown_as_unavailable_but_raw_chart_and_preview_work(monkeypatch):
    from c_dashboard.data.fixtures import load_spc_history
    def unstable():
        h=load_spc_history()
        h.frame.loc[h.frame.subgroup_id=="H-G010",PEEL]=10
        return h
    monkeypatch.setattr("c_dashboard.spc.controller.load_spc_history",unstable)
    app=load_mock(new_app())
    r=app.session_state[WORKSPACE_KEY].spc.result
    assert not r.target(PEEL).baseline.valid
    assert r.target(HEAT).baseline.valid
    assert any("UNSTABLE_HISTORY" in item.value for item in app.warning)
    spec=json.loads(app.get("vega_lite_chart")[0].proto.spec)
    assert not any(layer["mark"]["type"]=="rule" for layer in spec["layer"])
    assert any("sample_id" in item.value.columns for item in app.dataframe)
