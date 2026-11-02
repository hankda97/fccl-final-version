"""Strict presentation validation; no SHAP values are computed here."""

from dataclasses import dataclass, fields
from hashlib import sha256
import json

import numpy as np

from c_dashboard.adapters.explanations import (
    ExplanationInfo, ExplanationPayload, ExplanationRequest, ExplanationResponse,
)
from c_dashboard.data.schema import TARGET_UNITS, FEATURE_UNITS
from c_dashboard.visualization.sources import BASE_METADATA, LABEL_FLAGS
from c_dashboard.visualization.config import EXPLANATION_SCHEMA_VERSION, SHAP_KINDS
from c_dashboard.visualization.heatmap import eligible_rows, numeric_values


class ExplanationUnavailable(ValueError):
    """A valid local limitation rather than a fabricated result."""


@dataclass(frozen=True)
class ValidatedPayload:
    contributions: tuple[tuple[float, ...], ...]
    base_values: tuple[float, ...]


def make_request(rows, source, model_info, info: ExplanationInfo, *, target, kind,
                 feature=None, model_manifest=None) -> ExplanationRequest:
    if not model_info.available or not model_info.supports_shap:
        raise ExplanationUnavailable("目前模型沒有真正 SHAP 能力；待 B 模型與 C9 整合。")
    if not info.available:
        raise ExplanationUnavailable(info.message or "解釋 Provider 尚未交付，待 C9 整合。")
    if info.model_version != model_info.version or info.model_source != model_info.source:
        raise ValueError("解釋 Provider 模型來源／版本與目前模型不符。")
    if info.schema_version != EXPLANATION_SCHEMA_VERSION:
        raise ValueError("解釋 schema 版本不符。")
    if info.source_kind not in {"model", "render-test"}:
        raise ValueError("未知解釋來源種類。")
    if not all(isinstance(v, str) and v.strip() for v in (
        info.source, info.model_version, info.preprocessing_version,
        info.explanation_version, info.background_source)):
        raise ValueError("解釋來源／前處理／版本／背景資訊不完整。")
    if target not in TARGET_UNITS or target not in info.supported_targets:
        raise ExplanationUnavailable("此 Provider 未支援選定品質目標。")
    if target not in model_info.supports_targets:
        raise ExplanationUnavailable("目前模型未支援選定品質目標。")
    if kind not in SHAP_KINDS:
        raise ValueError("不支援的 SHAP 圖型。")
    names, units = info.feature_names, info.feature_units
    if (not names or len(set(names)) != len(names) or len(units) != len(names)
            or not all(isinstance(u, str) and u.strip() for u in units)):
        raise ValueError("解釋特徵名稱／單位維度缺失或重複。")
    forbidden = {*TARGET_UNITS, "sample_id", "product_batch", "timestamp", "available_at",
                 "source_row", "segment_id", "subgroup_id", "specimen_id", *BASE_METADATA,
                 *LABEL_FLAGS.values(), "appearance_ng_flag", "appearance_ng_probability", "appearance_ng_risk",
                 "overall_pass_flag", "process_phase", "product_id", "recipe_id", "dataset_split"}
    if any(not isinstance(n, str) or n in forbidden or n.startswith(("pred_", "hidden_", "spec_", "drift_"))
           or n.endswith(("_spec_pass_flag", "_label_available", "_label_reason")) for n in names):
        raise ValueError("解釋特徵含品質真值／識別／預測等不允許輸入。")
    if any(n in FEATURE_UNITS and FEATURE_UNITS[n] != u for n, u in zip(names, units)):
        raise ValueError("原始解釋特徵單位與正規化來源不符。")
    if any(name not in rows for name in names):
        raise ExplanationUnavailable("目前切片缺少 Provider 所需解釋特徵：" + "、".join(n for n in names if n not in rows))
    if kind == SHAP_KINDS[1] and feature not in names:
        raise ValueError("Dependence 特徵不在宣告的解釋特徵域。")
    scales, output_units = dict(info.output_scales), dict(info.output_units)
    scale, output_unit = scales.get(target), output_units.get(target)
    if target == "appearance_ng":
        expected_unit = {"probability": "probability", "raw_margin": "raw_margin", "log_odds": "log_odds"}.get(scale)
    else:
        expected_unit = TARGET_UNITS[target] if scale == "regression_output" else None
    if expected_unit is None or output_unit != expected_unit:
        raise ValueError("解釋輸出尺度或單位未知／不符；不推測成機率。")
    validate_manifest(info, source, model_manifest, target)
    valid = eligible_rows(rows)
    if "sample_id" not in valid:
        raise ExplanationUnavailable("缺少可追溯樣本識別。")
    numeric = valid[list(names)].copy()
    for name in names:
        numeric[name] = numeric_values(valid, name)
    mask = numeric.notna().all(axis=1)
    valid, numeric = valid.loc[mask], numeric.loc[mask]
    if valid.empty:
        raise ExplanationUnavailable("切片中沒有具完整且有限特徵的解釋樣本。")
    sample_ids = tuple(str(v) for v in valid.sample_id)
    values = tuple(tuple(float(v) for v in row) for row in numeric.to_numpy())
    context = (source, info, sample_ids, names, units, values, target, scale, output_unit, kind,
               feature if kind == SHAP_KINDS[1] else None)
    key = sha256(json.dumps(context, default=str, ensure_ascii=False).encode()).hexdigest()
    return ExplanationRequest(key, source, info, sample_ids, names, units, values,
                              target, output_unit, scale, kind,
                              feature if kind == SHAP_KINDS[1] else None,
                              1 if target == "appearance_ng" else None, len(rows) - len(valid))


def validate_response(request: ExplanationRequest, response: ExplanationResponse):
    if not isinstance(response, ExplanationResponse):
        raise ValueError("解釋回應不是受支援的 envelope。")
    if not isinstance(response.request, ExplanationRequest):
        raise ValueError("解釋回應沒有可核對的請求中繼資料。")
    for item in fields(ExplanationRequest):
        if getattr(request, item.name) != getattr(response.request, item.name):
            raise ValueError(f"解釋回應來源／版本／選項不符：{item.name}")
    if response.status != "available":
        raise ExplanationUnavailable(response.message or "解釋服務不可用。")
    if (response.payload is None) == (response.figure is None):
        raise ValueError("解釋回應須且只能含一個 payload 或 Figure。")
    if response.figure is not None:
        _validate_class(request, response.class_labels, response.output_index)
        return None
    payload = response.payload
    if not isinstance(payload, ExplanationPayload):
        raise ValueError("解釋 payload 型別不符。")
    if payload.sample_ids != request.sample_ids or len(set(payload.sample_ids)) != len(payload.sample_ids):
        raise ValueError("解釋樣本識別／順序不符或重複。")
    if payload.feature_names != request.feature_names or payload.feature_units != request.feature_units:
        raise ValueError("解釋特徵名稱／順序／單位不符。")
    n, f = len(request.sample_ids), len(request.feature_names)
    values = _matrix(payload.feature_values, (n, f), "特徵值")
    if not np.array_equal(values, np.asarray(request.feature_values)):
        raise ValueError("解釋特徵值與請求資料不符。")
    contributions = _matrix(payload.contributions, (n, f), "貢獻值")
    try:
        bases = np.asarray(payload.base_values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("基準值須為有限數值。") from exc
    if payload.scalar_base and bases.shape == ():
        bases = np.repeat(bases.item(), n)
    elif bases.shape != (n,):
        raise ValueError("基準值維度不符；scalar 必須明確宣告。")
    if not np.isfinite(bases).all():
        raise ValueError("基準值不是有限數值。")
    _validate_class(request, payload.class_labels, payload.output_index)
    return ValidatedPayload(tuple(tuple(float(v) for v in row) for row in contributions),
                            tuple(float(v) for v in bases))


def _validate_class(request, labels, index):
    if request.class_label is not None:
        if (not labels or len(set(labels)) != len(labels) or set(labels) != {0, 1}
                or isinstance(index, bool) or not isinstance(index, int)
                or not 0 <= index < len(labels) or labels[index] != request.class_label):
            raise ValueError("外觀 NG 輸出類別標籤／索引不符；必須明確選標籤 1。")
        if tuple(labels) != request.info.manifest.class_labels:
            raise ValueError("外觀 NG 類別順序與選定模型 manifest 不符。")
    elif labels or index is not None:
        raise ValueError("迴歸解釋不可帶分類輸出映射。")


def _matrix(values, shape, label):
    try:
        matrix = np.asarray(values, dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label}不是有效數值矩陣。") from exc
    if matrix.shape != shape or not np.isfinite(matrix).all():
        raise ValueError(f"{label}維度不符或含非有限值，預期 {shape}。")
    return matrix


def select_class_output(class_labels, outputs, label=1):
    """Provider helper selects by label, never by an assumed array position."""
    labels = tuple(class_labels)
    if len(labels) != len(outputs) or len(set(labels)) != len(labels) or label not in labels:
        raise ValueError("分類輸出缺少唯一且可對齊的 NG 標籤。")
    index = labels.index(label)
    return outputs[index], index


def validate_manifest(info, source, selected, target):
    from c_dashboard.adapters.explanations import ExplanationManifest
    manifest = info.manifest
    if not isinstance(manifest, ExplanationManifest) or not isinstance(selected, ExplanationManifest):
        raise ValueError("缺少可核對的解釋／選定模型 manifest。")
    if manifest != selected:
        raise ValueError("解釋 manifest 與選定模型 manifest 不符。")
    for name in ("manifest_id", "model_source", "model_type", "model_version", "schema_version",
                 "feature_version", "preprocessing_version", "label_version", "spec_version",
                 "dataset_version", "background_source"):
        if not isinstance(getattr(manifest, name), str) or not getattr(manifest, name).strip():
            raise ValueError("manifest 必要欄位不完整：" + name)
    for name in ("model_source", "model_version", "preprocessing_version", "feature_names",
                 "feature_units", "background_source"):
        if getattr(manifest, name) != getattr(info, name):
            raise ValueError("manifest 與解釋宣告不符：" + name)
    if target not in manifest.supported_targets or target in dict(manifest.unavailable_targets):
        raise ExplanationUnavailable(dict(manifest.unavailable_targets).get(target, "manifest 目標模型不可用"))
    for name in ("output_scales", "output_units"):
        if dict(getattr(manifest, name)).get(target) != dict(getattr(info, name)).get(target):
            raise ValueError("manifest 輸出尺度／單位不符。")
    profile = source.profile
    if (profile.kind not in manifest.compatible_source_kinds
            or profile.schema_version not in manifest.compatible_schemas
            or profile.label_version not in manifest.compatible_label_versions):
        raise ExplanationUnavailable("manifest 未宣告此來源 schema／標籤版本／粒度相容；跨組待確認。")
