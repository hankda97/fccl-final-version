"""Explicit C consumption profiles; these are not A/B source contracts."""
from dataclasses import dataclass, field
import pandas as pd


@dataclass(frozen=True)
class ChannelTime:
    available_at: str
    occurred_at: str = "timestamp"
    completed_at: str | None = None
    availability_flag: str | None = None


@dataclass(frozen=True)
class TemporalProfile:
    version: str
    source: str
    identity: ChannelTime
    channels: tuple[tuple[str, ChannelTime], ...]
    timezone: str | None = None
    revision_evidence: bool = False


@dataclass(frozen=True)
class ReplayEvent:
    source_row: int
    field: str
    occurred_at: pd.Timestamp
    available_at: pd.Timestamp


@dataclass(frozen=True)
class Timeline:
    stream_id: str
    profile: TemporalProfile | None
    frame: pd.DataFrame = field(compare=False, repr=False)
    raw: pd.DataFrame = field(compare=False, repr=False)
    groups: tuple[tuple[ReplayEvent, ...], ...] = ()
    reasons: tuple[str, ...] = ()
    diagnostics: tuple[tuple[int, str, str | None, str], ...] = ()


@dataclass(frozen=True)
class VisibilitySnapshot:
    token: tuple
    cutoff: str | None
    rows: pd.DataFrame = field(compare=False, repr=False)
    raw: pd.DataFrame = field(compare=False, repr=False)
    measurements: dict = field(compare=False, repr=False)
    released: frozenset[tuple[int, str]] = frozenset()
    played_rows: int = 0
    total_rows: int = 0
    cursor: int = 0
    total_groups: int = 0
    reasons: tuple[str, ...] = ()
