"""Chart orchestration over explicit rows; no global dataset reads."""

from dataclasses import asdict, replace
from hashlib import sha256
import json

from c_dashboard.data.schema import FEATURE_UNITS
from c_dashboard.visualization.config import MINIMUM_PAIRS, VISUALIZATION_VERSION
from c_dashboard.visualization.heatmap import compute_heatmap, source_for
from c_dashboard.visualization.types import ChartSlot
from c_dashboard.adapters.explanations import UnavailableExplanationProvider
from c_dashboard.visualization.explanations import ExplanationUnavailable, make_request
from c_dashboard.visualization.charts import prepare_explanation
from c_dashboard.visualization.sources import profile_for_workspace


def key_for(*values) -> str:
    return sha256(json.dumps(values, default=str, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def begin(slot: ChartSlot, key: str) -> None:
    slot.status, slot.request_key, slot.result, slot.reason = "running", key, None, None
    slot.computations += 1


def complete(slot: ChartSlot, key: str, result=None, *, status="ready", reason=None) -> bool:
    if slot.request_key != key:
        return False  # A late response cannot overwrite a newer request.
    slot.status, slot.result, slot.reason = status, result, reason
    return True


def request_scope(workspace):
    from c_dashboard.workspace_modes.controller import request_token
    return request_token(workspace)


def workspace_source(workspace, rows, *, columns=None, profile=None):
    data = workspace.data
    dataset = data.dataset
    source = source_for(rows, source_id=data.source_id or "not-loaded",
                      mapping_version=data.source_version or "not-loaded",
                      source_kind=dataset.source_kind if dataset else "not-loaded",
                      batch=data.selected_batch, time_start=data.time_start, time_end=data.time_end,
                      columns=columns, profile=profile or profile_for_workspace(workspace, rows))
    from c_dashboard.workspace_modes.controller import content_scope
    if content_scope(workspace):
        source = replace(source, context=(*source.context, ("workspace", str(content_scope(workspace)))))
    if workspace.replay.mode == "replay":
        from c_dashboard.replay.service import content_token
        source = replace(source, cutoff=workspace.replay.virtual_clock,
                         context=(*source.context, ("replay", str(content_token(workspace.replay)))))
    return source


def reconcile_features(state, rows) -> bool:
    present = tuple(name for name in FEATURE_UNITS if name in rows)
    previous = state.heatmap_features
    if previous is None and not present:
        return False
    state.heatmap_features = present if previous is None else tuple(name for name in previous if name in present)
    return previous is not None and state.heatmap_features != previous


def heatmap_for(workspace, rows, *, retry=False, profile=None) -> ChartSlot:
    scope = request_scope(workspace)
    state = workspace.visualization
    reconcile_features(state, rows)
    features, targets = state.heatmap_features or (), state.heatmap_targets
    source = workspace_source(workspace, rows, columns=(*features, *targets), profile=profile)
    key = key_for(asdict(source), features, targets, MINIMUM_PAIRS, VISUALIZATION_VERSION)
    slot = state.heatmap
    if not retry and slot.request_key == key and slot.status in {"ready", "unavailable", "error"}:
        return slot
    begin(slot, key)
    if workspace.data.dataset is None:
        complete(slot, key, status="not_loaded", reason="尚未載入 CSV。")
    elif rows.empty or not features or not targets:
        complete(slot, key, status="unavailable", reason="目前篩選為空或未選取特徵／品質目標。")
    else:
        try:
            result = compute_heatmap(rows, source, features, targets)
            if scope == request_scope(workspace):
                complete(slot, key, result)
            elif slot.request_key == key:
                slot.invalidate()
        except Exception as exc:
            if scope == request_scope(workspace):
                complete(slot, key, status="error", reason=f"Heatmap 計算失敗：{type(exc).__name__}: {exc}")
            elif slot.request_key == key:
                slot.invalidate()
    return slot


def explanation_for(workspace, rows, adapter, provider=None, *, retry=False) -> ChartSlot:
    scope = request_scope(workspace)
    provider = provider or UnavailableExplanationProvider()
    state, slot = workspace.visualization, workspace.visualization.explanation
    started = False
    # Even failed/unsupported requests have a source key, so no old result survives.
    key = key_for(workspace.data.source_id, state.shap_kind, state.shap_target, state.shap_feature)
    try:
        model_info, info = adapter.describe(), provider.describe()
        from c_dashboard.replay.controller import historical_model_reason
        reason = historical_model_reason(workspace, adapter, explanation=True)
        if reason:
            raise ExplanationUnavailable(reason)
        source = workspace_source(workspace, rows, columns=info.feature_names)
        key = key_for(asdict(source), model_info, info, state.shap_kind, state.shap_target, state.shap_feature)
        if workspace.data.dataset is None:
            begin(slot, key)
            complete(slot, key, status="not_loaded", reason="尚未載入可見資料，待 B 模型與 C9 SHAP 整合。")
            return slot
        request = make_request(rows, source, model_info, info, target=state.shap_target,
                               kind=state.shap_kind, feature=state.shap_feature,
                               model_manifest=adapter.explanation_manifest() if hasattr(adapter, "explanation_manifest") else None)
        key = request.request_key
        if not retry and slot.request_key == key and slot.status in {"ready", "unavailable", "error"}:
            return slot
        begin(slot, key)
        started = True
        response = provider.explain(request)
        rendered = prepare_explanation(request, response)
        if scope == request_scope(workspace):
            complete(slot, key, rendered)
        elif slot.request_key == key:
            slot.invalidate()
    except ExplanationUnavailable as exc:
        if scope != request_scope(workspace):
            if slot.request_key == key:
                slot.invalidate()
            return slot
        if not started:
            begin(slot, key)
        complete(slot, key, status="unavailable", reason=str(exc))
    except Exception as exc:
        if scope != request_scope(workspace):
            if slot.request_key == key:
                slot.invalidate()
            return slot
        if not started:
            begin(slot, key)
        complete(slot, key, status="error", reason=f"解釋資料／繪圖錯誤：{type(exc).__name__}: {exc}")
    return slot
