from c_dashboard.visualization.heatmap_summary import (
    QUALITY_DIRECTION_VERSION, summarize_heatmap,
)
from c_dashboard.visualization.types import ChartSource, HeatmapCell, HeatmapResult


def _result(cells):
    source = ChartSource("s", "m", "mock", None, None, None, None, "digest")
    return HeatmapResult(source, tuple(cells), 10, 10, 0, 3, "v")


def test_summary_selects_strongest_signs_and_stable_ties():
    result = _result([
        HeatmapCell("z", "peel_strength_n_mm", 0.8, 8, 2),
        HeatmapCell("a", "peel_strength_n_mm", 0.8, 9, 1),
        HeatmapCell("b", "peel_strength_n_mm", -0.7, 7, 3),
        HeatmapCell("c", "peel_strength_n_mm", None, 1, 9, "不足"),
    ])
    summary = summarize_heatmap(result)[0]
    assert summary.strongest_positive.feature == "a"
    assert summary.strongest_positive.n == 9
    assert summary.strongest_negative.feature == "b"
    assert summary.usable_cells == 3


def test_direction_metadata_handles_bounded_and_appearance_ng_semantics():
    result = _result([
        HeatmapCell("x", "dimensional_stability_md_pct", 0.2, 10, 0),
        HeatmapCell("x", "appearance_ng", -0.4, 10, 0),
    ])
    md, appearance = summarize_heatmap(result)
    assert md.direction == "bounded"
    assert appearance.direction == "lower-is-better"
    assert "1=NG" in appearance.interpretation
    assert {md.metadata_version, appearance.metadata_version} == {QUALITY_DIRECTION_VERSION}
