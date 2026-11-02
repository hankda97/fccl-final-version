from dataclasses import replace

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import pytest

from c_dashboard.adapters.explanations import ExplanationResponse
from c_dashboard.visualization.charts import prepare_explanation
from c_dashboard.visualization.config import SHAP_KINDS, TEST_NOTICE
from c6_support import RenderTestProvider, request_for
from test_c6_heatmap import hand_rows


def test_summary_and_dependence_preserve_payload_axes_units_and_test_notice():
    provider = RenderTestProvider()
    summary = request_for(hand_rows())
    rendered = prepare_explanation(summary, provider.explain(summary))
    assert TEST_NOTICE in rendered.spec["title"]
    assert len(rendered.spec["data"]["values"]) == 8
    assert rendered.spec["encoding"]["x"]["field"] == "contribution"
    assert "N/mm" in rendered.spec["encoding"]["x"]["title"]
    assert {r["feature"] for r in rendered.spec["data"]["values"]} == set(summary.feature_names)
    request = request_for(hand_rows(), target="appearance_ng", kind=SHAP_KINDS[1], feature="line_speed_m_min")
    spec = prepare_explanation(request, provider.explain(request)).spec
    assert len(spec["data"]["values"]) == 4
    assert spec["encoding"]["x"]["field"] == "value"
    assert "m/min" in spec["encoding"]["x"]["title"]
    assert "probability" in spec["encoding"]["y"]["title"]
    assert [r["value"] for r in spec["data"]["values"]] == [1., 2., 3., 4.]


def test_figures_become_bytes_close_and_never_call_show(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda *a, **kw: pytest.fail("blocking show"))
    request = request_for(hand_rows())
    before = plt.get_fignums()
    for _ in range(5):
        figure, axis = plt.subplots()
        axis.scatter([1, 2], [0.1, -0.1])
        result = prepare_explanation(request, ExplanationResponse(request, figure=figure))
        assert result.png.startswith(b"\x89PNG") and result.spec is None
        assert not hasattr(result, "figure")
        assert plt.get_fignums() == before


@pytest.mark.parametrize("failure", ["metadata", "savefig", "both"])
def test_figure_cleanup_on_every_failure_path(failure, monkeypatch):
    request = request_for(hand_rows())
    figure, _ = plt.subplots()
    response_request = replace(request, request_key="old") if failure in {"metadata", "both"} else request
    if failure == "savefig":
        def fail(*a, **kw):
            raise RuntimeError("figure failed")
        monkeypatch.setattr(figure, "savefig", fail)
    response = ExplanationResponse(response_request, figure=figure,
        payload=RenderTestProvider().explain(request).payload if failure == "both" else None)
    with pytest.raises((ValueError, RuntimeError)):
        prepare_explanation(request, response)
    assert not plt.fignum_exists(figure.number)


def test_unsupported_figure_and_ng_figure_class_mapping():
    request = request_for(hand_rows())
    with pytest.raises(ValueError, match="Figure"):
        prepare_explanation(request, ExplanationResponse(request, figure="untrusted-file.png"))
    request = request_for(hand_rows(), target="appearance_ng")
    figure, _ = plt.subplots()
    result = prepare_explanation(request, ExplanationResponse(request, figure=figure, class_labels=(1, 0), output_index=0))
    assert result.png
    figure, _ = plt.subplots()
    with pytest.raises(ValueError, match="類別"):
        prepare_explanation(request, ExplanationResponse(request, figure=figure, class_labels=(1, 0), output_index=1))
    assert not plt.fignum_exists(figure.number)
