"""Immutable SPC values; no Streamlit or mutable DataFrames in results."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from c_dashboard.spc.config import SpcProfile


@dataclass(frozen=True)
class SourceContext:
    source_id: str
    profile: "SpcProfile | None" = None
    mapping_version: str = ""
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroupPoint:
    target: str
    batch: str
    subgroup: str
    segment: str
    timestamp: str | None
    completed_at: str | None
    n: int
    values: tuple[float, ...]
    mean: float | None
    span: float | None
    reasons: tuple[str, ...]
    source_rows: tuple[int, ...]
    conditions: tuple[str, ...]
    break_before: bool = True

    @property
    def valid(self):
        return not self.reasons and self.mean is not None


@dataclass(frozen=True)
class TargetBaseline:
    target: str
    unit: str
    cl: float | None = None
    ucl: float | None = None
    lcl: float | None = None
    r_bar: float | None = None
    groups: int = 0
    reasons: tuple[str, ...] = ()

    @property
    def valid(self):
        return not self.reasons and self.cl is not None


@dataclass(frozen=True)
class BaselineBundle:
    version: str
    profile_signature: str
    history_hash: str
    source: str
    start: str | None
    end: str | None
    origin: str
    n: int
    constants_version: str
    stability_version: str
    conditions: tuple[tuple[str, float], ...]
    product: str
    recipe: str
    natural_samples: tuple[tuple[str, str], ...]
    targets: tuple[TargetBaseline, ...]

    def target(self, name):
        return next(item for item in self.targets if item.target == name)


@dataclass(frozen=True)
class SpcEvent:
    event_id: str
    source_id: str
    scope_id: str
    target: str
    rule: str
    batch: str
    subgroup: str
    segment: str
    triggered_at: str
    value: float
    cl: float
    ucl: float
    lcl: float
    sequence: tuple[float, ...]
    source_rows: tuple[int, ...]


@dataclass(frozen=True)
class TargetResult:
    target: str
    unit: str
    groups: tuple[GroupPoint, ...]
    baseline: TargetBaseline | None
    reasons: tuple[str, ...]
    status: str

    @property
    def latest(self):
        return self.groups[-1] if self.groups else None


@dataclass(frozen=True)
class RawMeasurement:
    target: str
    timestamp: str
    value: float
    batch: str
    source_row: int


@dataclass(frozen=True)
class SpcResult:
    source_id: str
    scope_id: str
    cutoff: str | None
    profile_version: str | None
    rule_version: str
    baseline: BaselineBundle | None
    targets: tuple[TargetResult, ...]
    events: tuple[SpcEvent, ...]
    raw: tuple[RawMeasurement, ...]
    appearance_count: int = 0
    appearance_ng: int = 0

    def target(self, name):
        return next(item for item in self.targets if item.target == name)
