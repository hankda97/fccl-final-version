"""Pure adapter calls and strict output alignment for C prediction consumers."""

from collections.abc import Mapping
import math

from c_dashboard.adapters.base import ModelAdapter, PredictionInput, PredictionRecord
from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.quality.config import FEATURE_ALLOWLIST, TARGET_NAMES


def normalize_features(features: Mapping[str, object]) -> tuple[dict[str, float] | None, str | None]:
    missing = [name for name in FEATURE_ALLOWLIST if name not in features]
    values: dict[str, float] = {}
    invalid = []
    for name in FEATURE_ALLOWLIST:
        if name not in features:
            continue
        try:
            value = float(features[name])
        except (TypeError, ValueError):
            invalid.append(name)
            continue
        if not math.isfinite(value):
            invalid.append(name)
            continue
        values[name] = value
    if missing or invalid:
        parts = []
        if missing:
            parts.append("缺少必要特徵：" + "、".join(missing))
        if invalid:
            parts.append("特徵不是有限數值：" + "、".join(invalid))
        return None, "；".join(parts)
    return values, None


def predict_one(adapter: ModelAdapter, sample_id: str, features: Mapping[str, object]) -> tuple[PredictionRecord | None, str | None]:
    normalized, problem = normalize_features(features)
    if problem:
        return None, problem
    info = adapter.describe()
    if not info.available:
        return None, info.message or "模型 Adapter 不可用。"
    try:
        result = adapter.predict((PredictionInput(sample_id, normalized),))
    except Exception as exc:
        return None, f"Adapter 預測失敗：{type(exc).__name__}: {exc}"
    if not result.info.available:
        return None, result.info.message or "模型 Adapter 回報不可用。"
    if result.info.version != info.version or not result.records:
        return None, "Adapter 未回傳可對齊的預測結果。"
    record = next((item for item in result.records if item.sample_id == sample_id), None)
    if record is None:
        return None, "Adapter 輸出識別與輸入不一致。"
    unavailable = dict(record.unavailable_targets or {})
    missing_targets = [name for name in TARGET_NAMES if name not in record.targets and name not in unavailable]
    if missing_targets:
        return None, "Adapter 未提供目標：" + "、".join(missing_targets)
    incorrect_units = [name for name in record.targets
                       if name in TARGET_UNITS and record.target_units.get(name) != TARGET_UNITS[name]]
    if incorrect_units:
        return None, "Adapter 目標單位缺失或不符：" + "、".join(incorrect_units)
    return record, None
