"""Chart values and durable UI state, independent of Streamlit and figures."""

from dataclasses import dataclass, field
from typing import Any, Literal

from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.visualization.sources import SourceProfile

ChartStatus = Literal["not_loaded", "running", "ready", "stale", "unavailable", "error"]


@dataclass(frozen=True)
class ChartSource:
    source_id: str
    mapping_version: str
    source_kind: str
    batch: str | None
    time_start: str | None
    time_end: str | None
    cutoff: str | None
    content_digest: str
    profile: SourceProfile = field(default_factory=SourceProfile)
    context: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class HeatmapCell:
    feature: str
    target: str
    coefficient: float | None
    n: int
    excluded: int
    reason: str | None = None
    exclusions: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class HeatmapResult:
    source: ChartSource
    cells: tuple[HeatmapCell, ...]
    total_rows: int
    eligible_rows: int
    excluded_identity: int
    minimum_pairs: int
    version: str
    method: str = "Pearson"


@dataclass
class ChartSlot:
    status: ChartStatus = "not_loaded"
    request_key: str | None = None
    result: Any = None
    reason: str | None = None
    computations: int = 0

    def invalidate(self) -> None:
        self.status = "stale" if self.request_key else "not_loaded"
        self.request_key = None
        self.result = None
        self.reason = None


@dataclass
class VisualizationState:
    heatmap_features: tuple[str, ...] | None = None
    heatmap_targets: tuple[str, ...] = tuple(TARGET_UNITS)
    shap_kind: str = "SHAP Summary Plot"
    shap_target: str = "peel_strength_n_mm"
    shap_feature: str | None = None
    heatmap: ChartSlot = field(default_factory=ChartSlot)
    explanation: ChartSlot = field(default_factory=ChartSlot)
    generation: int = 0

    def invalidate(self) -> None:
        self.heatmap.invalidate()
        self.explanation.invalidate()
        self.generation += 1
