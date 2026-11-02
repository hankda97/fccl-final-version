"""Keep invalid groups as sequence barriers; never drop rows to make n."""

from dataclasses import replace
import math

import pandas as pd

from c_dashboard.data.schema import CONTINUOUS_TARGETS
from c_dashboard.spc.types import GroupPoint


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def timestamp(value):
    try:
        t = pd.Timestamp(value)
        return t if not pd.isna(t) and t.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def text_id(value):
    return "" if pd.isna(value) else str(value).strip()


def build_subgroups(frame, profile, target):
    if target not in CONTINUOUS_TARGETS:
        raise ValueError("X-bar only supports continuous targets")
    if frame.empty:
        return ()
    buckets = {}
    sample_counts = {}
    for ordinal, (_, row) in enumerate(frame.iterrows()):
        batch = text_id(row.get("product_batch", ""))
        group = text_id(row.get("subgroup_id", ""))
        specimen = text_id(row.get("specimen_id", ""))
        if batch and specimen:
            sample_counts[(batch, specimen)] = sample_counts.get((batch, specimen), 0) + 1
        # Missing group evidence never becomes one artificial giant subgroup.
        key = (batch, group or f"missing-row-{ordinal}")
        buckets.setdefault(key, []).append((ordinal, row))
    points = []
    for (batch, group), records in buckets.items():
        rows = pd.DataFrame([row for _, row in records])
        reasons = list(profile.issues(target))
        if not batch or group.startswith("missing-row-"):
            reasons.append("MISSING_GROUP_ID")
        if len(rows) != profile.n:
            reasons.append("INCOMPLETE_OR_OVERSIZED_GROUP")
        specimens = [text_id(row.get("specimen_id", "")) for _, row in records]
        if not all(specimens) or len(set(specimens)) != len(specimens):
            reasons.append("MISSING_OR_DUPLICATE_SPECIMEN")
        if any(sample_counts.get((batch, specimen), 0) > 1 for specimen in specimens if specimen):
            reasons.append("REUSED_SPECIMEN_IN_SOURCE")
        # Include C2 invalid identity flags without discarding their rows.
        if "identity_valid" in rows and not rows.identity_valid.fillna(False).all():
            reasons.append("INVALID_IDENTITY")
        if "duplicate_record" in rows and rows.duplicate_record.fillna(True).any():
            reasons.append("DUPLICATE_RECORD")
        if "local_segment_id" in rows and rows.local_segment_id.fillna(True).any():
            reasons.append("LOCAL_SEGMENT_WITHOUT_SAMPLING_EVIDENCE")
        ids = {}
        for name, expected in (("product_id", profile.product), ("recipe_id", profile.recipe),
                               ("segment_id", None)):
            values = [text_id(row.get(name, "")) for _, row in records]
            ids[name] = values[0]
            if not all(values) or len(set(values)) != 1 or (expected is not None and values[0] != expected):
                reasons.append("INCOMPATIBLE_" + name.upper())
        times = [timestamp(row.get("timestamp")) for _, row in records]
        available = [timestamp(row.get("available_at")) for _, row in records]
        valid_times = [t for t in times if t is not None]
        valid_available = [t for t in available if t is not None]
        if len(valid_times) != len(rows) or len(set(valid_times)) != 1:
            reasons.append("INCONSISTENT_SAMPLING_TIME")
        if len(valid_available) != len(rows) or any(
                a is not None and t is not None and a < t for a, t in zip(available, times)):
            reasons.append("INVALID_AVAILABILITY")
        signature = [ids["product_id"], ids["recipe_id"]]
        for name, expected in profile.conditions:
            values = [finite(row.get(name)) for _, row in records]
            signature.append(str(values[0]))
            if any(v is None or abs(v - expected) > profile.condition_tolerance for v in values):
                reasons.append("INCOMPATIBLE_CONDITIONS:" + name)
            elif max(values) - min(values) > profile.condition_tolerance:
                reasons.append("MIXED_CONDITIONS:" + name)
        for name, lo, hi in profile.environment_ranges:
            if any((v := finite(row.get(name))) is None or not lo <= v <= hi for _, row in records):
                reasons.append("ENVIRONMENT_OUTSIDE_PROFILE:" + name)
        numbers = [finite(row.get(target)) for _, row in records]
        values = tuple(v for v in numbers if v is not None)
        if len(values) != len(rows):
            reasons.append("MISSING_OR_INVALID_MEASUREMENT")
        if target in ("peel_strength_n_mm", "heat_resistance_c") and any(v <= 0 for v in values):
            reasons.append("INVALID_PHYSICAL_MEASUREMENT")
        source_rows = tuple(int(v) if (v := finite(row.get("source_row"))) is not None else ordinal + 2
                            for ordinal, row in records)
        points.append(GroupPoint(
            target, batch, group, ids["segment_id"],
            min(valid_times).isoformat() if valid_times else None,
            max(valid_available).isoformat() if valid_available else None,
            len(rows), values,
            math.fsum(values) / len(values) if values and not reasons else None,
            max(values) - min(values) if values and not reasons else None,
            tuple(dict.fromkeys(reasons)), source_rows, tuple(signature),
        ))
    points.sort(key=lambda p: (timestamp(p.completed_at).value if timestamp(p.completed_at) is not None
                               else 2**63 - 1, p.source_rows[0]))
    output = []
    previous = None
    for point in points:
        continuous = False
        if previous and previous.valid and point.valid and profile.interval_seconds is not None:
            continuous = (previous.batch == point.batch and previous.conditions == point.conditions
                          and timestamp(previous.timestamp) is not None and timestamp(point.timestamp) is not None
                          and (timestamp(point.timestamp) - timestamp(previous.timestamp)).total_seconds()
                          == profile.interval_seconds)
        output.append(replace(point, break_before=not continuous))
        previous = point
    return tuple(output)


def group_inputs(frame, profile, target):
    """Separate C2's load/feature counts from actual subgroup applicability."""
    if profile is None:
        return (), ("MISSING_SAMPLING_EVIDENCE",)
    if frame.empty:
        return (), ("EMPTY_VIEW",)
    groups = build_subgroups(frame, profile, target)
    reasons = profile.issues(target)
    if not any(g.valid for g in groups):
        reasons += ("NO_COMPLETE_TARGET_GROUP",)
    if profile.interval_seconds is None:
        reasons += ("UNKNOWN_ADJACENCY_SINGLE_POINTS_ONLY",)
    return groups, tuple(dict.fromkeys(reasons))
