"""Small prediction port for UI wiring; no model loading or training here."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AdapterInfo:
    source: str
    version: str | None
    available: bool
    supports_shap: bool
    message: str
    supports_targets: tuple[str, ...] = ()


@dataclass(frozen=True)
class PredictionInput:
    sample_id: str
    features: Mapping[str, float]


@dataclass(frozen=True)
class PredictionRecord:
    sample_id: str
    targets: Mapping[str, float | int | None]
    appearance_ng_risk: float | None = None
    unavailable_targets: Mapping[str, str] | None = None
    target_units: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PredictionResult:
    info: AdapterInfo
    records: tuple[PredictionRecord, ...] = ()


class ModelAdapter(Protocol):
    def describe(self) -> AdapterInfo: ...

    def predict(self, samples: Sequence[PredictionInput]) -> PredictionResult: ...
