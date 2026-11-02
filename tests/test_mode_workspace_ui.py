from unittest.mock import patch
import pytest
from c_dashboard.state import WORKSPACE_KEY
from c_dashboard.workspace_modes.state import REGISTRY_KEY
from c_dashboard.replay.controller import snapshot_for
from test_c2_ui import new_app, load_mock
from test_c7_ui import replay_app


def navigate(app,mode):
    app.radio(key='ui_application_mode').set_value(mode).run()
    assert not app.exception
    return app


def test_default_and_unavailable_routes_never_call_A_services_or_leak_results():
    app=load_mock(new_app(),'上升趨勢情境')
    registry=app.session_state[REGISTRY_KEY];a=registry.workspaces['analysis']
    source=a.data.source_id;baseline=a.spc.baseline;events=a.spc.result.events
    assert events and any('SPC Alarm' in x.value for x in app.error)
    for mode in ('testline','production'):
        with patch('c_dashboard.ui.layout.render_sidebar',side_effect=AssertionError('hidden A loading')), \
             patch('c_dashboard.ui.layout.monitor_prediction',side_effect=AssertionError('hidden A prediction')):
            navigate(app,mode)
        assert not app.get('tab') and not app.metric and not app.dataframe
        assert all(x.disabled for x in app.button)
        assert any('unavailable' in x.value for x in app.warning)
        assert not any('SPC Alarm' in x.value for x in app.error)
        assert registry.workspaces[mode].data.dataset is None
        assert registry.workspaces[mode].mode_context.run_id is None
    navigate(app,'analysis')
    assert len(app.get('tab'))==4 and a.data.source_id==source and a.spc.baseline is baseline
    assert a.spc.result.events==events
    assert app.session_state[WORKSPACE_KEY] is a


def test_real_navigation_restores_source_mapping_chart_filter_and_candidate_widgets():
    app=load_mock(new_app());a=app.session_state[WORKSPACE_KEY]
    app.text_area(key='ui_mapping_json').set_value('{"version":"saved"}').run()
    app.selectbox(key='ui_mock_scenario').set_value('部分品質欄位缺失').run() # not loaded
    token=a.data.source_id[:12]
    app.selectbox(key=f'ui_batch_{token}').set_value('M-B02').run()
    speed=next(s for s in app.slider if s.key.startswith('ui_whatif_speed_'))
    speed.set_value(speed.value-.2).run()
    app.selectbox(key='ui_shap_target').set_value('heat_resistance_c').run()
    app.radio(key='ui_shap_kind').set_value('SHAP Dependence Plot').run()
    selected=a.what_if.selected;params=a.what_if.parameters.copy()
    count=a.visualization.heatmap.computations
    for mode in ('testline','production','analysis'):
        navigate(app,mode)
    assert app.radio(key='ui_source_choice').value=='C 專用 Mock'
    assert app.selectbox(key='ui_mock_scenario').value=='部分品質欄位缺失'
    assert app.text_area(key='ui_mapping_json').value=='{"version":"saved"}'
    assert app.selectbox(key=f'ui_batch_{token}').value=='M-B02'
    assert app.selectbox(key='ui_shap_target').value=='heat_resistance_c'
    assert app.radio(key='ui_shap_kind').value=='SHAP Dependence Plot'
    assert a.what_if.selected==selected and a.what_if.parameters==params
    assert a.visualization.heatmap.computations==count


def test_actual_c7_navigation_pause_cursor_epoch_fixed_whatif_cache_and_restart():
    app=replay_app();a=app.session_state[WORKSPACE_KEY]
    for _ in range(2):app.button(key='ui_step_placeholder').click().run()
    app.button(key='ui_reselect_whatif').click().run()
    slider=next(s for s in app.slider if s.key.startswith('ui_whatif_speed_'))
    slider.set_value(slider.value-.2).run()
    cursor=a.replay.cursor;fixed=a.what_if.selected;parameters=a.what_if.parameters.copy()
    # AppTest drains fragment reruns to completion. Freeze timer notifications
    # here to test navigation callbacks; the separate Chrome test uses real ticks.
    with patch('c_dashboard.ui.replay_controls.tick',return_value=False):
        app.button(key='ui_play_placeholder').click().run()
        assert a.replay.playing
        lifecycle=a.replay.lifecycle_token
        navigate(app,'testline')
    assert not a.replay.playing and a.replay.cursor==cursor and a.replay.lifecycle_token!=lifecycle
    navigate(app,'analysis')
    assert not a.replay.playing and a.replay.cursor==cursor
    assert a.what_if.selected==fixed and a.what_if.parameters==parameters
    assert app.radio(key='ui_mode_placeholder').value=='CSV 定時回放'
    assert len(snapshot_for(a).rows)==5
    app.button(key='ui_step_placeholder').click().run()
    assert a.replay.cursor==cursor+1
    app.button(key='ui_restart_placeholder').click().run()
    assert a.replay.cursor==0 and a.what_if.requires_reselect
    navigate(app,'production');navigate(app,'analysis')
    assert a.replay.cursor==0 and a.what_if.requires_reselect
    assert any('已釋出 0／15' in c.value for c in app.caption)


def test_unknown_mode_falls_back_without_reset_and_unknown_registry_keeps_state():
    app=load_mock(new_app());a=app.session_state[WORKSPACE_KEY]
    source=a.data.source_id
    # Seed invalid state before widget construction; injecting a non-option into
    # an already-created AppTest Radio fails in its serializer before app code.
    from streamlit.testing.v1 import AppTest
    from test_c2_ui import ROOT
    old_registry=app.session_state[REGISTRY_KEY]
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
    app.session_state[REGISTRY_KEY]=old_registry
    app.session_state[WORKSPACE_KEY]=a
    app.session_state['ui_application_mode']='invalid'
    app.run()
    assert not app.exception and app.session_state[REGISTRY_KEY].active_mode=='analysis'
    assert a.data.source_id==source
    app.session_state[REGISTRY_KEY].version='future-version';app.run()
    assert not app.exception and any('REGISTRY_VERSION_UNSUPPORTED' in w.value for w in app.warning)
    assert a.data.source_id==source


def test_shared_whatif_renderer_has_distinct_child_widget_keys_and_candidates():
    from streamlit.testing.v1 import AppTest
    script='''
import streamlit as st
from c_dashboard.workspace_modes.state import ensure_registry
from c_dashboard.data.session import commit_dataset, selected_rows
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.quality.controller import ensure_what_if_selection
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.ui.whatif_panel import render_whatif_panel
r=ensure_registry(st.session_state)
for mode in ('testline','production'):
    w=r.workspaces[mode]
    if w.data.dataset is None:commit_dataset(w,load_mock_fixture('normal'))
    options=ensure_what_if_selection(w,selected_rows(w))
    render_whatif_panel(w,options,DeterministicMockAdapter())
'''
    app=AppTest.from_string(script,default_timeout=20).run()
    assert not app.exception
    sliders=list(app.slider);assert len(sliders)==2
    assert sliders[0].key.startswith('testline:') and sliders[1].key.startswith('production:')
    registry=app.session_state[REGISTRY_KEY]
    sliders[0].set_value(sliders[0].value-.2).run()
    assert not app.exception
    assert registry.workspaces['testline'].what_if.parameters
    assert not registry.workspaces['production'].what_if.parameters
    assert registry.workspaces['analysis'].data.dataset is None
