import json
import pandas as pd
from c_dashboard.state import WORKSPACE_KEY
from c_dashboard.replay.controller import operate, snapshot_for
from test_c2_ui import load_mock, new_app, upload
from c7_support import CONFIG, FIXTURES


def replay_app():
    app=upload(new_app(),(FIXTURES/'delayed.csv').read_bytes())
    app.text_area(key='ui_temporal_json').set_value(json.dumps(CONFIG))
    app.button(key='ui_temporal_apply').click().run()
    app.radio(key='ui_mode_placeholder').set_value('CSV 定時回放').run()
    assert not app.exception
    return app


def test_replay_zero_step_atomic_counts_and_missing_values_in_every_area():
    app=replay_app();w=app.session_state[WORKSPACE_KEY]
    assert w.replay.cursor==0
    assert all(x.value=='—' for x in app.metric)
    assert any('已釋出 0／15 列' in c.value for c in app.caption)
    app.button(key='ui_step_placeholder').click().run()
    assert not app.exception and w.replay.cursor==1
    assert len(snapshot_for(w).rows)==5
    preview=next(d.value for d in app.dataframe if 'sample_id' in d.value)
    assert preview.peel_strength_n_mm.isna().all() and preview.line_speed_m_min.isna().all()
    assert any('已釋出 5／15 列' in c.value for c in app.caption)
    assert app.sidebar.metric[0].value=='—'
    app.button(key='ui_step_placeholder').click().run()
    assert not app.exception and w.replay.cursor==2
    assert app.sidebar.metric[0].value!='—'


def test_restart_invalidation_no_auto_resurrection_or_stale_parameters():
    app=replay_app();w=app.session_state[WORKSPACE_KEY]
    for _ in range(2):app.button(key='ui_step_placeholder').click().run()
    app.button(key='ui_reselect_whatif').click().run()
    slider=next(x for x in app.slider if x.key.startswith('ui_whatif_speed_'))
    slider.set_value(slider.value-.2).run()
    fixed=w.what_if.selected;parameters=w.what_if.parameters.copy()
    app.button(key='ui_step_placeholder').click().run()
    assert w.what_if.selected==fixed and w.what_if.parameters==parameters
    app.button(key='ui_restart_placeholder').click().run()
    assert w.replay.cursor==0 and w.what_if.requires_reselect
    assert not w.what_if.comparison and not w.what_if.parameters
    for _ in range(3):app.button(key='ui_step_placeholder').click().run()
    assert w.what_if.requires_reselect
    assert not any(x.key.startswith('ui_whatif_speed_') for x in app.slider)
    app.button(key='ui_reselect_whatif').click().run()
    assert not app.exception and not w.what_if.requires_reselect
    assert not w.what_if.parameters


def test_reruns_tabs_speed_filters_end_and_mode_switch():
    app=replay_app();w=app.session_state[WORKSPACE_KEY]
    app.button(key='ui_step_placeholder').click().run()
    app.selectbox(key='ui_speed_placeholder').set_value('4x').run()
    cursor=w.replay.cursor
    for tab in ('What-if','AI 圖表','資料檢查','SPC 監控'):
        app.session_state['ui_workspace_tabs']=tab;app.run()
        assert w.replay.cursor==cursor and not w.replay.playing
    for _ in range(12):app.button(key='ui_step_placeholder').click().run()
    assert not app.exception and w.replay.cursor==9 and not w.replay.playing
    assert any('完成' in c.value for c in app.caption)
    assert any('已釋出 15／15' in c.value for c in app.caption)
    app.radio(key='ui_mode_placeholder').set_value('CSV 快照').run()
    assert len(w.data.dataset.frame)==15 and not w.replay.playing
    app.radio(key='ui_mode_placeholder').set_value('CSV 定時回放').run()
    assert w.replay.cursor==0
    sid=w.data.source_id[:12]
    app.select_slider(key=f'ui_time_{sid}').set_value(('2026-11-01T08:00:00+08:00','2026-11-01T08:00:00+08:00')).run()
    assert not app.exception and snapshot_for(w).total_rows==5 and w.replay.cursor==0


def test_untrusted_upload_unavailable_but_snapshot_and_valid_source_survive():
    app=upload(new_app(),(FIXTURES/'delayed.csv').read_bytes())
    app.radio(key='ui_mode_placeholder').set_value('CSV 定時回放').run()
    assert not app.exception and app.button(key='ui_play_placeholder').disabled
    assert any('沒有可信可回放事件' in x.value for x in app.warning)
    app.radio(key='ui_mode_placeholder').set_value('CSV 快照').run()
    assert any('sample_id' in d.value for d in app.dataframe)
    app.text_area(key='ui_temporal_json').set_value('{bad json')
    app.button(key='ui_temporal_apply').click().run()
    assert any('時間設定未套用' in x.value for x in app.error)
    assert app.session_state[WORKSPACE_KEY].data.temporal_config is None


def test_spc_and_ai_alarm_share_cutoff_and_clear_on_restart():
    app=load_mock(new_app(),'上升趨勢情境');w=app.session_state[WORKSPACE_KEY]
    app.radio(key='ui_mode_placeholder').set_value('CSV 定時回放').run()
    assert not w.spc.result.events and w.model.current_prediction is None
    for _ in range(7):app.button(key='ui_step_placeholder').click().run()
    assert w.spc.result.events and w.model.current_prediction.record
    assert len({e.event_id for e in w.spc.result.events})==len(w.spc.result.events)
    assert any('SPC Alarm' in e.value for e in app.error)
    before=w.spc.result.events;app.run();assert w.spc.result.events==before
    app.button(key='ui_restart_placeholder').click().run()
    assert not w.spc.result.events and w.model.current_prediction is None
    assert not any('SPC Alarm' in e.value for e in app.error)


def test_future_value_perturbation_all_ui_values_and_issue_previews():
    original=pd.read_csv(FIXTURES/'delayed.csv')
    changed=original.copy()
    changed['peel_strength_n_mm']='NOT_YET_VISIBLE'
    def visible_tables(payload):
        app=upload(new_app(),payload)
        app.text_area(key='ui_temporal_json').set_value(json.dumps(CONFIG))
        app.button(key='ui_temporal_apply').click().run()
        app.radio(key='ui_mode_placeholder').set_value('CSV 定時回放').run()
        for _ in range(2):app.button(key='ui_step_placeholder').click().run()
        assert not app.exception
        values=[x.value for x in app.metric]
        for table in app.dataframe:
            assert 'NOT_YET_VISIBLE' not in table.value.to_string()
            if {'code','field','row'}<=set(table.value):
                assert not (table.value.code=='INVALID_NUMBER').any()
        return values, snapshot_for(app.session_state[WORKSPACE_KEY]).rows.drop(columns='sample_id')
    values_a,rows_a=visible_tables(original.to_csv(index=False).encode())
    values_b,rows_b=visible_tables(changed.to_csv(index=False).encode())
    assert values_a==values_b
    pd.testing.assert_frame_equal(rows_a,rows_b)
