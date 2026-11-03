"""Deterministic text summaries and quality-direction metadata for Heatmap results."""

from dataclasses import dataclass
import math


QUALITY_DIRECTION_VERSION = "quality-direction-v1"
QUALITY_DIRECTIONS = {
    "peel_strength_n_mm": ("higher-is-better", "數值越高通常代表抗剝離能力較高，仍須依規格判定。"),
    "dimensional_stability_md_pct": ("bounded", "雙側規格；相關正負不直接等於品質改善。"),
    "dimensional_stability_td_pct": ("bounded", "雙側規格；相關正負不直接等於品質改善。"),
    "heat_resistance_c": ("higher-is-better", "最高通過溫度越高通常越佳，仍須依測試契約判定。"),
    "appearance_ng": ("lower-is-better", "1=NG、0=OK；負相關代表特徵增加時 NG 比例傾向下降。"),
}


@dataclass(frozen=True)
class CorrelationHighlight:
    feature: str
    coefficient: float
    n: int


@dataclass(frozen=True)
class TargetCorrelationSummary:
    target: str
    strongest_positive: CorrelationHighlight | None
    strongest_negative: CorrelationHighlight | None
    usable_cells: int
    direction: str
    interpretation: str
    metadata_version: str = QUALITY_DIRECTION_VERSION


def summarize_heatmap(result) -> tuple[TargetCorrelationSummary, ...]:
    """Summarize valid cells per target with stable feature-name tie breaking."""
    targets = tuple(dict.fromkeys(cell.target for cell in result.cells))
    summaries = []
    for target in targets:
        cells = [cell for cell in result.cells if cell.target == target
                 and cell.coefficient is not None and math.isfinite(cell.coefficient)]
        positive = [cell for cell in cells if cell.coefficient > 0]
        negative = [cell for cell in cells if cell.coefficient < 0]
        best_positive = min(positive, key=lambda cell: (-cell.coefficient, cell.feature)) if positive else None
        best_negative = min(negative, key=lambda cell: (cell.coefficient, cell.feature)) if negative else None
        direction, interpretation = QUALITY_DIRECTIONS.get(
            target, ("target-centered", "須依此目標的正式規格解讀相關方向。")
        )
        summaries.append(TargetCorrelationSummary(
            target,
            _highlight(best_positive),
            _highlight(best_negative),
            len(cells),
            direction,
            interpretation,
        ))
    return tuple(summaries)


def _highlight(cell):
    return None if cell is None else CorrelationHighlight(cell.feature, float(cell.coefficient), cell.n)
