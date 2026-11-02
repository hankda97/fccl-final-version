from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import pytest

from c_dashboard.workspace_modes.state import ensure_registry
from c_dashboard.workspace_modes.controller import switch_mode, request_token, current_events
from c_dashboard.workspace_modes.ports import (
    ProviderRegistry, validate_payload, visible_payload, model_features, predict_visible, submit_payload,
)
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.adapters.base import PredictionResult
from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS
from mode_support import payload, FixedInterfaceProvider, EARLY, LATE


def setup(mode='testline'):
    r=ensure_registry({});switch_mode(r,mode)
    w=r.workspaces[mode];w.mode_context.run_id='test-run'
    return r,w,payload(w.mode_context)


def test_unavailable_registry_actions_never_start_write_or_change_formal_adapter():
    providers=ProviderRegistry()
    with patch('builtins.open',side_effect=AssertionError('unexpected I/O')):
        for mode in ('testline','production'):
            provider=providers.get(mode)
            assert not provider.describe().available
            for result in (provider.start_run(None),provider.advance(None,EARLY),provider.reset(None),provider.apply_confirmed_event(None,{})):
                assert not result.available and 'unavailable' in result.reason
    assert not hasattr(DeterministicMockAdapter(),'start_run')
    with pytest.raises(ValueError):providers.get('analysis')


@pytest.mark.parametrize('mode',['testline','production'])
def test_fixed_provider_time_channels_units_and_actual_shared_prediction(mode):
    r,w,p=setup(mode);provider=FixedInterfaceProvider(w.mode_context);providers=ProviderRegistry()
    providers.register(mode,provider)
    assert '介面測試' in provider.describe().reason
    with patch('builtins.open',side_effect=AssertionError('must not write/read production files')):
        visible,issues=visible_payload(providers.get(mode).inspect(),w.mode_context,EARLY)
        assert not issues and visible['source_kind']=='Synthetic'
        assert visible['truth']==[]
        assert visible['measurement'][0]['values']=={'peel_strength_n_mm':1.3}
        assert visible['prediction'][0]['values']['peel_strength_n_mm']==1.9
        assert visible['raw_signal']!=visible['processed_signal']
        captured=[]
        class Spy(DeterministicMockAdapter):
            def predict(self,samples):
                captured.extend(samples)
                return super().predict(samples)
        record,error=predict_visible(Spy(),visible,tuple(FEATURE_UNITS),'sample')
        assert error is None and set(record.targets)==set(TARGET_UNITS)
        assert captured[0].features==model_features(visible,tuple(FEATURE_UNITS))
        assert 'noise_cause' not in captured[0].features and 'peel_strength_n_mm' not in captured[0].features
    assert not w.model.current_prediction and not w.data.dataset
    later,_=visible_payload(p,w.mode_context,LATE)
    assert 'heat_resistance_c' in later['measurement'][0]['values']
    p['process'][0]['field_available_at']['line_speed_m_min']=LATE
    early,_=visible_payload(p,w.mode_context,EARLY)
    record,error=predict_visible(DeterministicMockAdapter(),early,tuple(FEATURE_UNITS),'sample')
    assert record is None and 'line_speed' in error
    assert 'line_speed_m_min' not in model_features(early,tuple(FEATURE_UNITS))
    assert not model_features(later,('noise_cause','peel_strength_n_mm'))


@pytest.mark.parametrize('field,value',[
    ('mode_id','analysis'),('workspace_id','wrong'),('run_id','wrong'),('schema_version','unknown'),
    ('source_kind','formal'),('simulator_version',None),('seed',None),
    ('destination','generated_data/v2/new.csv'),('destination',r'C:\python\FCCL final\generated_data\v2\process_segments.csv'),
    ('events','invalid'),('measurement',[None]),
])
def test_invalid_envelope_rejected_without_mutating_valid_state(field,value):
    r,w,p=setup();original=deepcopy(p)
    w.what_if.parameters['line_speed_m_min']=1.2
    p[field]=value
    assert validate_payload(p,w.mode_context)
    visible,issues=submit_payload(r,'testline',request_token(w),p,EARLY)
    assert visible is None and issues and w.what_if.parameters=={'line_speed_m_min':1.2}
    assert not current_events(r,'testline')


@pytest.mark.parametrize('field,value',[
    ('station',None),('timestamp',None),('available_at','2026-10-31T08:00:00+08:00'),
    ('timestamp','2026-11-01T08:00:00'),('material_md_end_m',-1),('material_md_start_m',float('nan')),
    ('values',{'line_speed_m_min':float('inf')}),('units',{}),('units',{'line_speed_m_min':'wrong'}),
    ('field_available_at',{}),('availability',{}),
])
def test_invalid_record_time_units_md_and_values_are_structured_errors(field,value):
    r,w,p=setup();p['process'][0][field]=value
    issues=validate_payload(p,w.mode_context)
    assert issues and all(i.code and i.field and i.message for i in issues)


def test_partial_targets_unavailable_are_not_filled_and_no_fake_probabilities():
    r,w,p=setup();visible,_=visible_payload(p,w.mode_context,EARLY)
    class Partial(DeterministicMockAdapter):
        def predict(self,samples):
            result=super().predict(samples);record=result.records[0]
            targets=dict(record.targets);targets.pop('heat_resistance_c')
            return PredictionResult(result.info,(replace(record,targets=targets,
                unavailable_targets={'heat_resistance_c':'TEST_TARGET_UNAVAILABLE'}),))
    record,error=predict_visible(Partial(),visible,tuple(FEATURE_UNITS),'s')
    assert error is None and len(record.targets)==4
    assert record.unavailable_targets['heat_resistance_c']=='TEST_TARGET_UNAVAILABLE'
    assert not hasattr(record,'appearance_ng_probability')


def test_candidate_unconfirmed_event_rejected_and_dedup_by_run_source_type():
    r,w,p=setup();original=deepcopy(p)
    token=request_token(w,'request')
    for _ in range(2):
        visible,issues=submit_payload(r,'testline',token,p,EARLY)
        assert not issues
    assert len(current_events(r,'testline'))==1 and p==original
    p['events'][0]['confirmed']=False
    assert validate_payload(p,w.mode_context)
    assert len(current_events(r,'testline'))==1
    p=deepcopy(original);p['process'][0]['noise_cause']='must not surface'
    visible,issues=visible_payload(p,w.mode_context,EARLY)
    assert 'noise_cause' not in visible['process'][0]
    switch_mode(r,'production')
    assert submit_payload(r,'testline',token,original,EARLY)[0] is None
    assert not current_events(r,'production')
