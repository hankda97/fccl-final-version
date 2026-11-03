from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping

from .config import load_product_recipe


class Station(str, Enum):
    COATING = "coating"
    CURING = "curing"
    LAMINATION = "lamination"


@dataclass(frozen=True)
class ParameterValue:
    name: str
    station: Station
    setpoint: float
    actual: float
    unit: str


@dataclass(frozen=True)
class MaterialBoundary:
    segment_id: str
    station: Station
    exited_at: datetime | None


def validate_candidate_set(candidate: Mapping[str, float], *, require_primary: bool = True) -> dict[str, float]:
    parameters = load_product_recipe()["recipe"]["parameters"]
    primary = {name for name, cfg in parameters.items() if not cfg.get("advanced", False)}
    if require_primary and not primary.issubset(candidate):
        raise ValueError("PARTIAL_PARAMETER_SET")
    result: dict[str, float] = {}
    for name, raw in candidate.items():
        if name not in parameters:
            raise ValueError(f"UNKNOWN_PARAMETER:{name}")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"NOT_NUMERIC:{name}")
        value = float(raw); cfg = parameters[name]
        if not cfg["ui_min"] <= value <= cfg["ui_max"]:
            raise ValueError(f"OUTSIDE_UI_RANGE:{name}")
        result[name] = value
    return result


def event_applies(*, event_station: Station, event_at: datetime, material: MaterialBoundary) -> bool:
    if material.station != event_station:
        raise ValueError("STATION_BOUNDARY_MISMATCH")
    return material.exited_at is None or event_at < material.exited_at


def quality_is_available(*, lamination_exited_at: datetime | None, quality_available_at: datetime, now: datetime) -> bool:
    return lamination_exited_at is not None and lamination_exited_at <= quality_available_at <= now


def validate_feature_cutoff(feature_times: Mapping[str, datetime], *, inference_at: datetime) -> None:
    future = sorted(name for name, timestamp in feature_times.items() if timestamp > inference_at)
    if future:
        raise ValueError("FUTURE_FEATURE:" + ",".join(future))


def validate_model_support(values: Mapping[str, float], manifest: Mapping[str, object]) -> dict[str, str]:
    if manifest.get("support_range_source") != "train_manifest":
        raise ValueError("MODEL_SUPPORT_SOURCE_INVALID")
    ranges = manifest.get("feature_support_ranges")
    if not isinstance(ranges, Mapping):
        raise ValueError("MODEL_SUPPORT_RANGES_MISSING")
    statuses: dict[str, str] = {}
    for name, value in values.items():
        bounds = ranges.get(name)
        if not isinstance(bounds, Mapping) or "min" not in bounds or "max" not in bounds:
            raise ValueError(f"MODEL_SUPPORT_FIELD_MISSING:{name}")
        statuses[name] = "in_range" if float(bounds["min"]) <= value <= float(bounds["max"]) else "extrapolation"
    return statuses
