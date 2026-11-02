"""Configurable C demonstration alarms; absent criteria stay indeterminate."""

from hashlib import sha256
import json
import math
from collections.abc import Mapping

from c_dashboard.quality.config import RISK_POLICY_VERSION, TARGET_LABELS
from c_dashboard.quality.types import PredictionAlarm


def assess_record(record, *, source_id: str, sample_id: str, batch_id: str,
                  segment_id: str, timestamp: str, scenario: str,
                  quality_specs: Mapping | None, appearance_threshold: float | None,
                  model_version: str | None) -> tuple[tuple[PredictionAlarm, ...], tuple[str, ...]]:
    alarms = []
    indeterminate = []
    if record is None:
        return (), ("沒有可用預測。",)
    specs = quality_specs or {}
    for target in ("peel_strength_n_mm", "dimensional_stability_md_pct",
                   "dimensional_stability_td_pct", "heat_resistance_c"):
        value = record.targets.get(target)
        if value is None:
            if (record.unavailable_targets or {}).get(target):
                indeterminate.append(f"{TARGET_LABELS[target]}無法預測：{record.unavailable_targets[target]}")
            else:
                indeterminate.append(f"{TARGET_LABELS[target]}缺少預測輸出。")
            continue
        spec = specs.get(target)
        bounds = _bounds(spec)
        if bounds is None:
            indeterminate.append(f"{TARGET_LABELS[target]}沒有已配置的示範測試條件。")
            continue
        number = float(value)
        if not math.isfinite(number):
            indeterminate.append(f"{TARGET_LABELS[target]}預測不是有限數值。")
            continue
        lsl, usl = bounds
        side = "低於示範下限" if lsl is not None and number < lsl else None
        if side is None and usl is not None and number > usl:
            side = "高於示範上限"
        if side:
            threshold = (f"LSL={lsl}" if "低於" in side else f"USL={usl}")
            alarms.append(_alarm(source_id, sample_id, batch_id, segment_id, timestamp, target,
                                 number, side, threshold, model_version, scenario))

    risk = record.appearance_ng_risk
    appearance_spec = specs.get("appearance_ng")
    if risk is None or not math.isfinite(float(risk)):
        indeterminate.append("外觀示範風險不可用；不推定為 0 或正常。")
    elif (appearance_threshold is None or not isinstance(appearance_spec, Mapping)
          or not _valid_threshold(appearance_threshold)):
        indeterminate.append("外觀沒有已配置的示範 NG 風險門檻／測試條件。")
    elif float(risk) >= float(appearance_threshold):
        alarms.append(_alarm(source_id, sample_id, batch_id, segment_id, timestamp,
                             "appearance_ng", float(risk), "達到示範風險門檻",
                             f"risk ≥ {appearance_threshold}", model_version, scenario))
    return tuple(alarms), tuple(indeterminate)


def _bounds(spec):
    if not isinstance(spec, Mapping) or not ("lsl" in spec or "usl" in spec):
        return None
    values = []
    for name in ("lsl", "usl"):
        if name not in spec:
            values.append(None)
            continue
        try:
            value = float(spec[name])
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        values.append(value)
    if values[0] is not None and values[1] is not None and values[0] > values[1]:
        return None
    return tuple(values)


def _valid_threshold(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and 0 <= number <= 1


def _alarm(source_id, sample_id, batch_id, segment_id, timestamp, target, value,
           condition, threshold, model_version, scenario):
    identity = json.dumps((source_id, sample_id, target, condition, threshold,
                           model_version, scenario, RISK_POLICY_VERSION), ensure_ascii=False)
    return PredictionAlarm(sha256(identity.encode("utf-8")).hexdigest()[:24], source_id,
                           sample_id, batch_id, segment_id, timestamp, target, float(value),
                           condition, threshold, model_version or "unknown", scenario)
