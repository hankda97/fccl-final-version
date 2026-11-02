"""C-only composition helpers; calculations consume explicit visible rows."""

from hashlib import sha256
import json
import math

import pandas as pd

from c_dashboard.adapters.base import ModelAdapter
from c_dashboard.data.schema import FEATURE_UNITS
from c_dashboard.quality.assessment import assess_record
from c_dashboard.quality.config import (
    ENVIRONMENT_FEATURES, PARAMETER_CONTROLS, PROCESS_FEATURES,
    RECOMMENDATION_POLICY_VERSION, parameter_bounds,
)
from c_dashboard.quality.prediction import predict_one
from c_dashboard.quality.recommend import choose_recommendation
from c_dashboard.quality.types import PredictionView, WhatIfComparison
from c_dashboard.state import SegmentSnapshot, WhatIfState, WorkspaceState


def available_segments(rows: pd.DataFrame, source_id: str = "") -> list[SegmentSnapshot]:
    if rows.empty or "segment_id" not in rows or "product_batch" not in rows:
        return []
    valid = rows.loc[rows.get("identity_valid", pd.Series(False, index=rows.index)).fillna(False)]
    if valid.empty:
        return []
    order = "available_at" if "available_at" in valid else "timestamp"
    valid = valid.sort_values([order, "source_row"], kind="stable")
    latest = valid.groupby(["product_batch", "segment_id"], sort=False, dropna=False).tail(1)
    snapshots = []
    for _, row in latest.iterrows():
        process = _values(row, PROCESS_FEATURES)
        env = _values(row, ENVIRONMENT_FEATURES)
        timestamp = row.get("timestamp")
        snapshots.append(SegmentSnapshot(
            source_id=source_id,
            batch_id=str(row["product_batch"]),
            segment_id=str(row["segment_id"]),
            timestamp=timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
            process_settings=tuple(sorted(process.items())),
            environment=tuple(sorted(env.items())),
            sample_id=str(row.get("sample_id") or ""),
            root_roll_id=str(row.get("root_roll_id", "")),
            material_md_start=str(row.get("material_md_start_m", "")),
            material_md_end=str(row.get("material_md_end_m", "")),
        ))
    return sorted(snapshots, key=lambda item: item.timestamp)


def ensure_what_if_selection(workspace: WorkspaceState, rows: pd.DataFrame) -> list[SegmentSnapshot]:
    options = available_segments(rows, workspace.data.source_id or "not-loaded")
    if not options:
        return []
    current = workspace.what_if.selected
    if workspace.what_if.requires_reselect:
        return options
    if current is None or not any(_snapshot_key(item) == _snapshot_key(current) for item in options):
        workspace.what_if = WhatIfState(selected=options[-1])
    return options


def select_what_if_segment(workspace: WorkspaceState, snapshot: SegmentSnapshot, *, force=False) -> None:
    if workspace.what_if.selected == snapshot and not force and not workspace.what_if.requires_reselect:
        return
    workspace.what_if = WhatIfState(selected=snapshot, parameter_revision=workspace.what_if.parameter_revision + 1)


def snapshot_features(snapshot: SegmentSnapshot, overrides=None) -> dict[str, float]:
    values = dict(snapshot.environment)
    values.update(dict(snapshot.process_settings))
    for name, value in (overrides or {}).items():
        if name not in PARAMETER_CONTROLS:
            raise ValueError(f"不允許調整參數：{name}")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} 必須是有效數值") from exc
        if not math.isfinite(number):
            raise ValueError(f"{name} 必須是有限數值")
        baseline = values.get(name)
        if baseline is None or not math.isfinite(float(baseline)):
            raise ValueError(f"{name} 缺少有效原始設定")
        low, high, _ = parameter_bounds(name, float(baseline))
        if not low <= number <= high:
            raise ValueError(f"{name} 超出版本化示範範圍 {low:g}～{high:g}")
        values[name] = number
    return values


def features_from_row(row: pd.Series) -> dict[str, float]:
    return _values(row, FEATURE_UNITS)


def monitor_prediction(workspace: WorkspaceState, rows: pd.DataFrame,
                       adapter: ModelAdapter) -> PredictionView | None:
    if rows.empty:
        workspace.model.current_prediction = None
        workspace.model.current_prediction_key = None
        return None
    visible = rows.loc[rows.get("identity_valid", pd.Series(False, index=rows.index)).fillna(False)]
    if visible.empty:
        workspace.model.current_prediction = None
        workspace.model.current_prediction_key = None
        return None
    latest = visible.sort_values(["timestamp" if workspace.replay.mode == "replay" else "available_at", "source_row"], kind="stable").iloc[-1]
    sample_id = str(latest.get("sample_id") or "")
    features = features_from_row(latest)
    from c_dashboard.workspace_modes.controller import request_token, content_scope, model_identity
    request_context = request_token(workspace)
    key = _key((content_scope(workspace), workspace.data.source_id, workspace.data.source_version, sample_id, features, model_identity(adapter),
                workspace.replay.mode, workspace.replay.generation, workspace.replay.virtual_clock))
    if key == workspace.model.current_prediction_key:
        return workspace.model.current_prediction
    from c_dashboard.replay.controller import historical_model_reason
    error = historical_model_reason(workspace, adapter)
    record = None
    if error is None:
        record, error = predict_one(adapter, sample_id, features)
    if request_context != request_token(workspace):
        return workspace.model.current_prediction  # Discard a late result after reset/source/cursor change.
    view = PredictionView(
        source_id=workspace.data.source_id or "not-loaded", sample_id=sample_id,
        batch_id=str(latest.get("product_batch", "")), segment_id=str(latest.get("segment_id", "")),
        timestamp=latest["timestamp"].isoformat(), adapter_source=adapter.describe().source,
        adapter_version=adapter.describe().version, record=record, unavailable_reason=error,
    )
    workspace.model.current_prediction_key = key
    workspace.model.current_prediction = view
    workspace.model.source_id = view.source_id
    workspace.model.version = view.adapter_version
    return view


def evaluate_what_if(workspace: WorkspaceState, adapter: ModelAdapter) -> tuple[WhatIfComparison | None, object]:
    if workspace.what_if.requires_reselect:
        return None, None
    snapshot = workspace.what_if.selected
    requested_state = workspace.what_if
    requested_parameters = dict(requested_state.parameters)
    requested_generation = workspace.replay.generation
    from c_dashboard.workspace_modes.controller import request_token, content_scope, model_identity
    requested_context = request_token(workspace)
    if snapshot is None:
        workspace.what_if.comparison = None
        workspace.what_if.recommendation = None
        workspace.what_if.result_key = None
        return None, None
    try:
        if not workspace.what_if.advanced_unlocked and any(
            PARAMETER_CONTROLS.get(name) and PARAMETER_CONTROLS[name].advanced
            for name in workspace.what_if.parameters
        ):
            raise ValueError("熟化與壓合參數尚未解鎖")
        before_features = snapshot_features(snapshot)
        after_features = snapshot_features(snapshot, workspace.what_if.parameters)
    except (TypeError, ValueError) as exc:
        workspace.what_if.comparison = WhatIfComparison(
            workspace.data.source_id or "not-loaded", snapshot.sample_id, snapshot.batch_id,
            snapshot.segment_id, snapshot.timestamp, adapter.describe().source,
            adapter.describe().version, None, None, str(exc),
        )
        return workspace.what_if.comparison, None

    settings = workspace.data.dataset.settings if workspace.data.dataset is not None else {}
    specs = settings.get("quality_specs") if settings else None
    key = _key((content_scope(workspace), snapshot, tuple(sorted(workspace.what_if.parameters.items())),
                model_identity(adapter), RECOMMENDATION_POLICY_VERSION, specs))
    if key == workspace.what_if.result_key:
        return workspace.what_if.comparison, workspace.what_if.recommendation

    from c_dashboard.replay.controller import historical_model_reason
    temporal_error = historical_model_reason(workspace, adapter)
    before, before_error = (None, temporal_error) if temporal_error else predict_one(adapter, snapshot.sample_id, before_features)
    after, after_error = (None, temporal_error) if temporal_error else predict_one(adapter, snapshot.sample_id, after_features)
    error = before_error or after_error
    comparison = WhatIfComparison(
        workspace.data.source_id or "not-loaded", snapshot.sample_id, snapshot.batch_id,
        snapshot.segment_id, snapshot.timestamp, adapter.describe().source,
        adapter.describe().version, before, after, error,
    )
    baseline_record = before
    recommendation = choose_recommendation(snapshot, before_features, baseline_record,
                                           adapter, specs)
    if (requested_context != request_token(workspace) or workspace.what_if is not requested_state or workspace.what_if.parameters != requested_parameters
            or workspace.replay.generation != requested_generation or workspace.what_if.requires_reselect):
        return workspace.what_if.comparison, workspace.what_if.recommendation
    workspace.what_if.comparison = comparison
    workspace.what_if.result_key = key
    workspace.what_if.editing_started = workspace.what_if.editing_started or bool(workspace.what_if.parameters)
    workspace.what_if.recommendation = recommendation
    return comparison, recommendation


def current_prediction_alarms(workspace: WorkspaceState, view: PredictionView | None):
    if view is None:
        return (), ("尚無可見有效資料。",)
    settings = workspace.data.dataset.settings if workspace.data.dataset is not None else {}
    specs = settings.get("quality_specs") if settings else None
    threshold = settings.get("appearance_ng_risk_threshold") if settings else None
    return assess_record(view.record, source_id=view.source_id, sample_id=view.sample_id,
                         batch_id=view.batch_id, segment_id=view.segment_id,
                         timestamp=view.timestamp, scenario="目前可見監控區段",
                         quality_specs=specs, appearance_threshold=threshold,
                         model_version=view.adapter_version)


def what_if_alarms(workspace: WorkspaceState, comparison: WhatIfComparison | None):
    if comparison is None:
        return (), ("尚未選取 What-if 區段。",)
    settings = workspace.data.dataset.settings if workspace.data.dataset is not None else {}
    specs = settings.get("quality_specs") if settings else None
    threshold = settings.get("appearance_ng_risk_threshold") if settings else None
    return assess_record(comparison.after, source_id=comparison.source_id,
                         sample_id=comparison.sample_id, batch_id=comparison.batch_id,
                         segment_id=comparison.segment_id, timestamp=comparison.timestamp,
                         scenario="固定 What-if 情境", quality_specs=specs,
                         appearance_threshold=threshold,
                         model_version=comparison.adapter_version)


def _values(row, names) -> dict[str, float]:
    values = {}
    for name in names:
        try:
            value = float(row[name])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            values[name] = value
    return values


def _snapshot_key(snapshot):
    return (snapshot.source_id, snapshot.batch_id, snapshot.segment_id,
            snapshot.timestamp, snapshot.sample_id)


def _key(value):
    return sha256(json.dumps(value, default=str, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
