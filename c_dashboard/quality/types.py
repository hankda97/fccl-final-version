"""Immutable result records for the C-only demonstration prediction path."""

from dataclasses import dataclass

from c_dashboard.adapters.base import PredictionRecord


@dataclass(frozen=True)
class PredictionView:
    source_id: str
    sample_id: str
    batch_id: str
    segment_id: str
    timestamp: str
    adapter_source: str
    adapter_version: str | None
    record: PredictionRecord | None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class WhatIfComparison:
    source_id: str
    sample_id: str
    batch_id: str
    segment_id: str
    timestamp: str
    adapter_source: str
    adapter_version: str | None
    before: PredictionRecord | None
    after: PredictionRecord | None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class PredictionAlarm:
    alarm_id: str
    source_id: str
    sample_id: str
    batch_id: str
    segment_id: str
    timestamp: str
    target: str
    value: float
    condition: str
    threshold: str
    model_version: str
    scenario: str


@dataclass(frozen=True)
class Recommendation:
    status: str
    reason: str
    parameter: str | None = None
    delta: float | None = None
    unit: str | None = None
    focus_target: str | None = None
    before_value: float | None = None
    after_value: float | None = None
    adapter_version: str | None = None
    policy_version: str | None = None
