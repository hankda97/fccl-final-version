"""Optional C presentation port; ModelAdapter.predict remains unchanged."""

from dataclasses import dataclass
from typing import Any, Protocol

from c_dashboard.visualization.config import EXPLANATION_SCHEMA_VERSION
from c_dashboard.visualization.types import ChartSource


@dataclass(frozen=True)
class ExplanationManifest:
    """C presentation manifest projection, not B's artifact schema."""
    manifest_id: str
    model_source: str
    model_type: str
    model_version: str
    schema_version: str
    feature_version: str
    preprocessing_version: str
    label_version: str
    spec_version: str
    dataset_version: str
    feature_names: tuple[str, ...]
    feature_units: tuple[str, ...]
    supported_targets: tuple[str, ...]
    output_scales: tuple[tuple[str, str], ...]
    output_units: tuple[tuple[str, str], ...]
    class_labels: tuple[int, ...]
    background_source: str
    compatible_schemas: tuple[str, ...]
    compatible_label_versions: tuple[str, ...]
    compatible_source_kinds: tuple[str, ...]
    unavailable_targets: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ExplanationInfo:
    source: str
    model_source: str = "未接入"
    model_version: str | None = None
    preprocessing_version: str = ""
    explanation_version: str = ""
    available: bool = False
    feature_names: tuple[str, ...] = ()
    feature_units: tuple[str, ...] = ()
    supported_targets: tuple[str, ...] = ()
    output_scales: tuple[tuple[str, str], ...] = ()
    output_units: tuple[tuple[str, str], ...] = ()
    background_source: str = ""
    source_kind: str = "model"
    schema_version: str = EXPLANATION_SCHEMA_VERSION
    message: str = ""
    manifest: ExplanationManifest | None = None


@dataclass(frozen=True)
class ExplanationRequest:
    request_key: str
    source: ChartSource
    info: ExplanationInfo
    sample_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    feature_units: tuple[str, ...]
    feature_values: tuple[tuple[float, ...], ...]
    target: str
    output_unit: str
    output_scale: str
    kind: str
    feature: str | None
    class_label: int | None
    excluded_rows: int = 0


@dataclass(frozen=True)
class ExplanationPayload:
    sample_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    feature_units: tuple[str, ...]
    feature_values: Any
    contributions: Any
    base_values: Any
    scalar_base: bool = False
    class_labels: tuple[int, ...] = ()
    output_index: int | None = None


@dataclass(frozen=True)
class ExplanationResponse:
    request: ExplanationRequest
    payload: ExplanationPayload | None = None
    figure: Any = None
    status: str = "available"
    message: str = ""
    class_labels: tuple[int, ...] = ()
    output_index: int | None = None


class ExplanationProvider(Protocol):
    def describe(self) -> ExplanationInfo: ...

    def explain(self, request: ExplanationRequest) -> ExplanationResponse: ...


class UnavailableExplanationProvider:
    def describe(self) -> ExplanationInfo:
        return ExplanationInfo("未接入解釋 Provider", message="待 B 正式模型與 C9 SHAP 整合。")

    def explain(self, request: ExplanationRequest) -> ExplanationResponse:
        return ExplanationResponse(request, status="unavailable", message=self.describe().message)
