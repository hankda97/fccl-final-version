from dataclasses import replace

import numpy as np
import pytest

from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.adapters.explanations import UnavailableExplanationProvider
from c_dashboard.visualization.explanations import (
    ExplanationUnavailable, make_request, select_class_output, validate_response,
)
from c_dashboard.visualization.config import SHAP_KINDS
from c6_support import RenderTestModel, RenderTestProvider, request_for
from test_c6_heatmap import hand_rows


def test_optional_port_and_formula_mock_keep_original_prediction_api():
    rows = hand_rows()
    provider = RenderTestProvider()
    request = request_for(rows)
    with pytest.raises(ExplanationUnavailable, match="沒有真正 SHAP"):
        make_request(rows, request.source, DeterministicMockAdapter().describe(), provider.describe(),
                     target=request.target, kind=request.kind)
    assert provider.calls == 0
    assert not hasattr(DeterministicMockAdapter(), "explain")
    assert not UnavailableExplanationProvider().describe().available


def test_valid_payload_regression_scalar_base_and_reverse_ng_class_order():
    provider = RenderTestProvider()
    request = request_for(hand_rows())
    response = provider.explain(request)
    result = validate_response(request, response)
    assert len(result.contributions) == len(request.sample_ids)
    scalar = replace(response, payload=replace(response.payload, base_values=0., scalar_base=True))
    assert validate_response(request, scalar).base_values == (0.,) * 4
    ng = request_for(hand_rows(), target="appearance_ng")
    ng_response = provider.explain(ng)
    assert ng_response.payload.class_labels == (1, 0) and ng_response.payload.output_index == 0
    assert validate_response(ng, ng_response).contributions[0] == (.1, -.02)
    assert select_class_output((0, 1), ("OK", "NG")) == ("NG", 1)


@pytest.mark.parametrize("mutation,reason", [
    (lambda p: replace(p, sample_ids=p.sample_ids[::-1]), "識別"),
    (lambda p: replace(p, sample_ids=(p.sample_ids[0],)*4), "識別"),
    (lambda p: replace(p, feature_names=p.feature_names[::-1]), "特徵名稱"),
    (lambda p: replace(p, feature_units=("bad", "bad")), "特徵名稱"),
    (lambda p: replace(p, feature_values=((1., 2.),)*4), "特徵值"),
    (lambda p: replace(p, contributions=((1.,),)*4), "維度"),
    (lambda p: replace(p, contributions=((np.nan, .1),)*4), "非有限"),
    (lambda p: replace(p, base_values=()), "基準值"),
    (lambda p: replace(p, base_values=0., scalar_base=False), "基準值"),
])
def test_malformed_payload_rejected_without_silent_reshape(mutation, reason):
    request = request_for(hand_rows())
    response = RenderTestProvider().explain(request)
    with pytest.raises(ValueError, match=reason):
        validate_response(request, replace(response, payload=mutation(response.payload)))


@pytest.mark.parametrize("name,value", [
    ("preprocessing_version", "different"), ("model_version", "different"),
    ("schema_version", "different"), ("background_source", ""),
    ("feature_names", ("line_speed_m_min", "line_speed_m_min")),
    ("feature_units", ("m/min",)),
    ("output_scales", (("peel_strength_n_mm", "unknown"),)),
    ("output_units", (("peel_strength_n_mm", "MPa"),)),
])
def test_invalid_provider_schema_units_scale_and_version(name, value):
    info = replace(RenderTestProvider().describe(), **{name: value})
    # New D9 requires every declaration to match the selected model manifest.
    with pytest.raises(ValueError):
        request_for(hand_rows(), info=info)


def test_target_specific_missing_features_unavailable_and_wrong_ng_output():
    info = replace(RenderTestProvider().describe(), supported_targets=("heat_resistance_c",))
    with pytest.raises(ExplanationUnavailable, match="未支援"):
        request_for(hand_rows(), info=info)
    with pytest.raises(ExplanationUnavailable, match="缺少"):
        request_for(hand_rows().drop(columns=["line_speed_m_min"]))
    request = request_for(hand_rows(), target="appearance_ng")
    response = RenderTestProvider().explain(request)
    with pytest.raises(ValueError, match="類別"):
        validate_response(request, replace(response, payload=replace(response.payload, output_index=1)))
    with pytest.raises(ValueError, match="類別"):
        validate_response(request, replace(response, payload=replace(response.payload, class_labels=())))
    with pytest.raises(ValueError):
        select_class_output((0,), ("OK",))


def test_response_context_kind_feature_model_version_and_target_must_match():
    request = request_for(hand_rows(), kind=SHAP_KINDS[1], feature="line_speed_m_min")
    response = RenderTestProvider().explain(request)
    for wrong in (replace(request, target="heat_resistance_c"), replace(request, output_scale="probability"),
                  replace(request, request_key="stale"), replace(request, kind=SHAP_KINDS[0])):
        with pytest.raises(ValueError, match="不符"):
            validate_response(request, replace(response, request=wrong))
