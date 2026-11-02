from dataclasses import replace
import pandas as pd
from c_dashboard.replay.controller import operate, snapshot_for, historical_model_reason
from c_dashboard.visualization.controller import heatmap_for, explanation_for, complete
from c_dashboard.quality.controller import monitor_prediction
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.adapters.explanations import ExplanationResponse
from c_dashboard.visualization.config import SHAP_KINDS
from c6_support import RenderTestModel, RenderTestProvider
from c7_support import delayed_workspace, through


class AsOfRenderModel(RenderTestModel):
    def historical_applicability(self):
        return {'available_at':'2026-10-30T00:00:00+08:00',
                'training_cutoff':'2026-10-29T00:00:00+08:00',
                'background_available_at':'2026-10-29T00:00:00+08:00'}


def test_heatmap_released_pair_counts_cutoff_generation_and_retry():
    w=delayed_workspace()
    early=through(w,'2026-11-01T08:00:01+08:00')
    assert all(c.n==0 for c in heatmap_for(w,early.rows).result.cells)
    mid=through(w,'2026-11-01T08:00:04+08:00')
    slot=heatmap_for(w,mid.rows);key=slot.request_key
    assert any(c.n==5 for c in slot.result.cells if c.target=='peel_strength_n_mm')
    assert all(c.n==0 for c in slot.result.cells if c.target=='heat_resistance_c')
    old=slot.result
    assert heatmap_for(w,mid.rows).result is old
    operate(w,'restart',0)
    assert not complete(slot,key,old)
    assert heatmap_for(w,snapshot_for(w).rows).status=='unavailable'


def test_formula_and_formal_model_temporal_capability_are_separate():
    w=delayed_workspace();s=through(w,'2026-11-01T08:00:05+08:00')
    assert historical_model_reason(w,DeterministicMockAdapter()) is None
    slot=explanation_for(w,s.rows,DeterministicMockAdapter())
    assert slot.status=='unavailable' and slot.result is None
    assert 'C9' in slot.reason
    p=monitor_prediction(w,s.rows,RenderTestModel())
    assert p.record is None and 'HISTORICAL' in p.unavailable_reason
    assert historical_model_reason(w,AsOfRenderModel(),explanation=True) is None
    class Future(AsOfRenderModel):
        def historical_applicability(self):
            return {**super().historical_applicability(),'training_cutoff':'2026-12-01T00:00:00+08:00'}
    assert historical_model_reason(w,Future())=='MODEL_NOT_AVAILABLE_AS_OF_CUTOFF'
    class FutureBackground(AsOfRenderModel):
        def historical_applicability(self):
            return {**super().historical_applicability(),'background_available_at':'2026-12-01T00:00:00+08:00'}
    assert historical_model_reason(w,FutureBackground(),explanation=True)=='BACKGROUND_NOT_AVAILABLE_AS_OF_CUTOFF'


def test_render_test_summary_dependence_ng1_and_future_payload_rejected():
    w=delayed_workspace();s=through(w,'2026-11-01T08:00:03+08:00')
    model,provider=AsOfRenderModel(),RenderTestProvider()
    slot=explanation_for(w,s.rows,model,provider)
    assert slot.status=='ready'
    assert slot.result.spec and provider.calls==1
    w.visualization.shap_kind=SHAP_KINDS[1]
    w.visualization.shap_feature='ambient_rh_pct'
    w.visualization.shap_target='appearance_ng'
    slot=explanation_for(w,s.rows,model,provider)
    assert slot.status=='ready'
    assert 'probability' in str(slot.result.spec)
    class InvalidProvider(RenderTestProvider):
        def explain(self,request):
            response=super().explain(request)
            return ExplanationResponse(request,payload=replace(response.payload,
                       sample_ids=(*response.payload.sample_ids,'FUTURE_SAMPLE')))
    assert explanation_for(w,s.rows,model,InvalidProvider(),retry=True).status=='error'
    # Advancing/restarting invalidates even numerically identical data/metadata.
    old=slot.request_key
    operate(w,'restart',0)
    assert not complete(slot,old,object())
    assert explanation_for(w,snapshot_for(w).rows,model,provider).status=='unavailable'


def test_ui_future_flag_diagnostic_is_not_revealed_early():
    from test_c7_temporal import edited
    a=delayed_workspace();b=delayed_workspace(edited(target_flag=0))
    for w in (a,b):
        s=through(w,'2026-11-01T08:00:01+08:00')
        assert not s.reasons
    assert snapshot_for(a).total_groups==snapshot_for(b).total_groups
    assert through(b,'2026-11-01T08:00:04+08:00').reasons


def test_late_prediction_and_whatif_cannot_write_after_restart():
    from c_dashboard.quality.controller import ensure_what_if_selection,evaluate_what_if
    w=delayed_workspace();rows=through(w,'2026-11-01T08:00:01+08:00').rows
    class RestartingModel(AsOfRenderModel):
        def predict(self,samples):
            result=super().predict(samples)
            operate(w,'restart',0)
            return result
    assert monitor_prediction(w,rows,RestartingModel()) is None
    assert w.model.current_prediction is None
    rows=through(w,'2026-11-01T08:00:01+08:00').rows
    ensure_what_if_selection(w,rows)
    assert evaluate_what_if(w,RestartingModel())==(None,None)
    assert w.what_if.comparison is None


def test_inflight_explanation_rejects_cursor_tick_without_prior_invalidation():
    from c_dashboard.replay.service import tick
    from c_dashboard.replay.controller import timeline_for
    w=delayed_workspace();rows=through(w,'2026-11-01T08:00:01+08:00').rows
    class TickProvider(RenderTestProvider):
        def explain(self,request):
            response=super().explain(request)
            operate(w,'play',0)
            tick(w.replay,timeline_for(w),2,w.replay.generation)
            return response
    slot=explanation_for(w,rows,AsOfRenderModel(),TickProvider())
    assert slot.status=='stale' and slot.result is None
