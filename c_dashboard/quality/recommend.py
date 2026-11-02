"""Single-focus candidate strategy for configured C demo scenarios only."""

from collections.abc import Mapping, Sequence

from c_dashboard.adapters.base import ModelAdapter
from c_dashboard.quality.config import (
    PARAMETER_CONTROLS,
    RECOMMENDATION_CANDIDATES,
    RECOMMENDATION_FOCUS_TARGET,
    RECOMMENDATION_MIN_EFFECT,
    RECOMMENDATION_POLICY_VERSION,
    parameter_bounds,
)
from c_dashboard.quality.prediction import predict_one
from c_dashboard.quality.types import Recommendation
from c_dashboard.state import SegmentSnapshot


def choose_recommendation(snapshot: SegmentSnapshot, baseline_features: Mapping[str, float],
                          baseline_record, adapter: ModelAdapter, quality_specs: Mapping | None,
                          *, candidates: Sequence[tuple[str, float]] = RECOMMENDATION_CANDIDATES,
                          focus_target: str = RECOMMENDATION_FOCUS_TARGET) -> Recommendation:
    """Choose by one configured demo focus; no official multi-target trade-off."""
    if baseline_record is None:
        return Recommendation("unavailable", "原設定預測不可用，無法比較候選。",
                             policy_version=RECOMMENDATION_POLICY_VERSION)
    if focus_target not in baseline_record.targets:
        return Recommendation("unavailable", f"缺少示範目標 {focus_target}，無法評估建議。",
                             focus_target=focus_target,
                             policy_version=RECOMMENDATION_POLICY_VERSION)
    spec = (quality_specs or {}).get(focus_target)
    if not isinstance(spec, Mapping) or not ("lsl" in spec or "usl" in spec):
        return Recommendation("unavailable", "缺少此測試情境的目標條件，無法評估建議。",
                             focus_target=focus_target,
                             policy_version=RECOMMENDATION_POLICY_VERSION)
    if not candidates:
        return Recommendation("none", "目前測試設定沒有可比較候選。",
                             focus_target=focus_target,
                             policy_version=RECOMMENDATION_POLICY_VERSION)

    before = float(baseline_record.targets[focus_target])
    if "lsl" in spec and "usl" not in spec:
        direction = 1.0
    elif "usl" in spec and "lsl" not in spec:
        direction = -1.0
    else:
        center = (float(spec["lsl"]) + float(spec["usl"])) / 2
        direction = 1.0 if before < center else -1.0

    eligible = []
    for parameter, delta in candidates:
        if parameter not in PARAMETER_CONTROLS or parameter not in baseline_features:
            continue
        try:
            delta_value = float(delta)
        except (TypeError, ValueError):
            continue
        candidate_value = float(baseline_features[parameter]) + delta_value
        low, high, _ = parameter_bounds(parameter, float(baseline_features[parameter]))
        if not low <= candidate_value <= high:
            continue
        candidate_features = dict(baseline_features)
        candidate_features[parameter] = candidate_value
        record, _ = predict_one(adapter, snapshot.sample_id, candidate_features)
        if record is None or record.targets.get(focus_target) is None:
            continue
        after = float(record.targets[focus_target])
        effect = (after - before) * direction
        if effect > RECOMMENDATION_MIN_EFFECT:
            eligible.append((effect, parameter, delta_value, after))
    if not eligible:
        return Recommendation("none", "測試候選沒有改善目前設定的示範目標，無合適調整建議。",
                             focus_target=focus_target,
                             before_value=before,
                             adapter_version=adapter.describe().version,
                             policy_version=RECOMMENDATION_POLICY_VERSION)
    # Stable tie-break by configured order after effect; no random ranking.
    effect, parameter, delta, after = max(eligible, key=lambda item: item[0])
    del effect
    return Recommendation(
        "suggested", "依單一示範目標的版本化測試策略選出；不是正式多目標政策。",
        parameter=parameter, delta=delta, unit=PARAMETER_CONTROLS[parameter].unit,
        focus_target=focus_target, before_value=before, after_value=after,
        adapter_version=adapter.describe().version,
        policy_version=RECOMMENDATION_POLICY_VERSION,
    )
