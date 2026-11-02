"""Independent historical calibration. No monitoring values are fitted."""

from dataclasses import replace
import math

import pandas as pd

from c_dashboard.data.schema import CONTINUOUS_TARGETS, TARGET_UNITS
from c_dashboard.spc.config import CONSTANTS, digest
from c_dashboard.spc.rules import detect_signals
from c_dashboard.spc.subgroups import build_subgroups, text_id, timestamp
from c_dashboard.spc.types import BaselineBundle, TargetBaseline


def frame_signature(frame):
    """Content version only, not a fit or statistical use of other data."""
    return digest(frame.to_json(orient="split", date_format="iso", double_precision=15))


def natural_samples(frame):
    return tuple(sorted(set((text_id(row.get("product_batch", "")), text_id(row.get("specimen_id", "")))
                            for _, row in frame.iterrows())))


def build_baseline(history_rows, profile, monitoring_origin=None, *, history_hash=None,
                   source="C 專用獨立歷史 Mock（非真實產線）", monitor_samples=()):
    origin = monitoring_origin or profile.monitoring_origin
    declared_origin = timestamp(origin)
    data_hash = history_hash or frame_signature(history_rows)
    # Unit applicability is target-specific; a bad heat unit must not stop peel.
    common = [code for code in profile.issues() if code != "UNIT_MISMATCH"]
    if declared_origin is None or timestamp(profile.monitoring_origin) != declared_origin:
        common.append("INVALID_MONITORING_ORIGIN")
    if profile.history_hash and history_hash != profile.history_hash:
        common.append("HISTORY_CONTENT_MISMATCH")
    observation = [timestamp(v) for v in history_rows.get("timestamp", pd.Series(dtype=object))]
    availability = [timestamp(v) for v in history_rows.get("available_at", pd.Series(dtype=object))]
    starts = [t for t in observation if t is not None]
    ends = [t for t in availability if t is not None]
    if (not starts or not ends or len(starts) != len(history_rows) or len(ends) != len(history_rows)
            or declared_origin is None or max(starts) >= declared_origin or max(ends) >= declared_origin):
        common.append("HISTORY_NOT_PRIOR")
    samples = natural_samples(history_rows)
    if set(samples).intersection(monitor_samples):
        common.append("HISTORY_SAMPLE_OVERLAP")
    targets = []
    for name in CONTINUOUS_TARGETS:
        reasons = list(dict.fromkeys((*common, *profile.issues(name))))
        groups = build_subgroups(history_rows, profile, name)
        if type(profile.minimum_history_groups) is not int or len(groups) < profile.minimum_history_groups:
            reasons.append("INSUFFICIENT_HISTORY_GROUPS")
        if not groups or any(not g.valid for g in groups):
            reasons.append("INVALID_HISTORY_GROUP")
        cl = rb = ucl = lcl = None
        if not reasons:
            cl = math.fsum(g.mean for g in groups) / len(groups)
            rb = math.fsum(g.span for g in groups) / len(groups)
            if rb <= 0:
                reasons.append("ZERO_HISTORY_VARIATION")
            else:
                a2, d3, d4 = CONSTANTS[profile.n]
                ucl, lcl = cl + a2 * rb, cl - a2 * rb
                provisional = TargetBaseline(name, TARGET_UNITS[name], cl, ucl, lcl, rb, len(groups))
                for g in groups:
                    if g.span < d3*rb or g.span > d4*rb:
                        reasons.append(f"UNSTABLE_HISTORY_RANGE:{g.batch}/{g.subgroup}")
                for i, rule, _ in detect_signals(groups, provisional):
                    reasons.append(f"UNSTABLE_HISTORY_MEAN:{rule}:{groups[i].batch}/{groups[i].subgroup}")
        result = TargetBaseline(name, TARGET_UNITS[name], cl, ucl, lcl, rb, len(groups),
                                tuple(dict.fromkeys(reasons)))
        # A rejected baseline never exposes provisional lines as effective limits.
        if not result.valid:
            result = replace(result, cl=None, ucl=None, lcl=None)
        targets.append(result)
    version = digest((data_hash, frame_signature(history_rows), profile.signature(), origin, "baseline-v1"))
    return BaselineBundle(version, profile.signature(), data_hash, source,
                          min(starts).isoformat() if starts else None,
                          max(ends).isoformat() if ends else None, origin,
                          profile.n, profile.constants_version, profile.stability_version,
                          profile.conditions, profile.product, profile.recipe, samples, tuple(targets))
