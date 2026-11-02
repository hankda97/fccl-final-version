"""Business state independent of widget keys and future data/model adapters."""

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Literal
from typing import TYPE_CHECKING

from c_dashboard.visualization.types import VisualizationState

if TYPE_CHECKING:
    from c_dashboard.data.loader import LoadResult
    from c_dashboard.quality.types import PredictionView, Recommendation, WhatIfComparison
    from c_dashboard.spc.types import BaselineBundle, SpcResult

WORKSPACE_KEY = "fccl_workspace"


@dataclass
class DataState:
    source_id: str | None = None
    source_name: str | None = None
    source_version: str | None = None
    csv_bytes: bytes | None = None
    selected_batch: str | None = None
    validation_status: str = "not_loaded"
    dataset: "LoadResult | None" = None
    last_attempt: "LoadResult | None" = None
    time_start: str | None = None
    time_end: str | None = None
    temporal_config: dict | None = None


@dataclass
class ReplayState:
    mode: Literal["snapshot", "replay"] = "snapshot"
    stream_id: str | None = None
    generation: int = 0
    cursor: int = 0
    playing: bool = False
    speed: float = 1.0
    last_tick: float | None = None
    virtual_clock: str | None = None
    last_tick_sequence: int = -1
    timeline: object | None = None
    lifecycle_token: str = "workspace"
    spc_events: dict = field(default_factory=dict)
    spc_processed_cursor: int = 0


@dataclass(frozen=True)
class SegmentSnapshot:
    """Immutable C-internal identification and original what-if context."""

    source_id: str
    batch_id: str
    segment_id: str
    timestamp: str
    process_settings: tuple[tuple[str, float], ...] = ()
    environment: tuple[tuple[str, float], ...] = ()
    sample_id: str = ""
    root_roll_id: str = ""
    material_md_start: str = ""
    material_md_end: str = ""


@dataclass
class WhatIfState:
    selected: SegmentSnapshot | None = None
    parameters: dict[str, float] = field(default_factory=dict)
    editing_started: bool = False
    advanced_unlocked: bool = False
    parameter_revision: int = 0
    result_key: str | None = None
    comparison: "WhatIfComparison | None" = None
    recommendation: "Recommendation | None" = None
    requires_reselect: bool = False


@dataclass
class ModelState:
    source_id: str | None = None
    version: str | None = None
    baseline_version: str | None = None
    rules_version: str | None = None
    current_prediction_key: str | None = None
    current_prediction: "PredictionView | None" = None


@dataclass
class SpcState:
    baseline_key: str | None = None
    baseline: "BaselineBundle | None" = None
    result_key: str | None = None
    result: "SpcResult | None" = None


@dataclass
class WorkspaceState:
    mode_context: object | None = None
    data: DataState = field(default_factory=DataState)
    replay: ReplayState = field(default_factory=ReplayState)
    what_if: WhatIfState = field(default_factory=WhatIfState)
    model: ModelState = field(default_factory=ModelState)
    spc: SpcState = field(default_factory=SpcState)
    visualization: VisualizationState = field(default_factory=VisualizationState)


def ensure_workspace(session: MutableMapping) -> WorkspaceState:
    """Initialize once; ordinary reruns must not reset user work."""
    if WORKSPACE_KEY not in session:
        session[WORKSPACE_KEY] = WorkspaceState()
    if not hasattr(session[WORKSPACE_KEY], "visualization"):
        session[WORKSPACE_KEY].visualization = VisualizationState()
    return session[WORKSPACE_KEY]
