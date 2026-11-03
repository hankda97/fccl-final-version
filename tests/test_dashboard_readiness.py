from types import SimpleNamespace

import pandas as pd

from c_dashboard.adapters.base import AdapterInfo
from c_dashboard.adapters.explanations import ExplanationInfo
from c_dashboard.ui.readiness import build_readiness_matrix, with_computing


def _workspace(dataset=None):
    return SimpleNamespace(data=SimpleNamespace(dataset=dataset))


def test_readiness_distinguishes_unloaded_from_selected_source():
    rows = pd.DataFrame()
    adapter = AdapterInfo("mock", "1", True, False, "")
    matrix = build_readiness_matrix(_workspace(), rows, [], adapter, ExplanationInfo("none"))
    assert all(item.status == "error" for item in matrix.values())
    assert "載入" in matrix["data"].next_step


def test_ready_data_whatif_heatmap_and_formal_shap_are_independent():
    rows = pd.DataFrame({"line_speed_m_min": [1.0], "peel_strength_n_mm": [1.2]})
    adapter = AdapterInfo("formal", "1", True, True, "")
    explanation = SimpleNamespace(available=True, manifest=object(), message="")
    matrix = build_readiness_matrix(_workspace(object()), rows, [object()], adapter, explanation)
    assert {name: item.status for name, item in matrix.items()} == {
        "data": "ready", "what_if": "ready", "heatmap": "ready",
        "summary": "ready", "dependence": "ready",
    }
    assert with_computing(matrix["heatmap"], "計算中").status == "computing"


def test_missing_adapter_blocks_whatif_without_blocking_observed_heatmap():
    rows = pd.DataFrame({"line_speed_m_min": [1.0], "peel_strength_n_mm": [1.2]})
    adapter = AdapterInfo("none", None, False, False, "")
    matrix = build_readiness_matrix(_workspace(object()), rows, [object()], adapter, ExplanationInfo("none"))
    assert matrix["what_if"].status == "error"
    assert matrix["heatmap"].status == "ready"
    assert matrix["summary"].status == "error"
