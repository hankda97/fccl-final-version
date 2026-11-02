"""Validate declared release times. Never guess a formal publication time."""
from dataclasses import asdict
from hashlib import sha256
import json
import pandas as pd
from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS
from c_dashboard.replay.types import ChannelTime, TemporalProfile, ReplayEvent, Timeline

IDENTIFIERS = {"source_row", "sample_id", "timestamp", "product_batch", "segment_id",
               "subgroup_id", "specimen_id", "product_id", "recipe_id", "root_roll_id",
               "aligned_sample_id", "material_md_start_m", "material_md_end_m",
               "length_m", "position_m", "identity_valid", "duplicate_record", "local_segment_id"}


def profile_for(dataset, config=None):
    if config is not None:
        if not isinstance(config, dict) or not config.get("version") or not config.get("source"):
            raise ValueError("時間 profile 需要 version、source 及明確 identity／channels。")
        if not isinstance(config.get("revision_evidence", False), bool):
            raise ValueError("revision_evidence 必須為布林值並具有上游證據。")
        if config.get("timezone"):
            from zoneinfo import ZoneInfo
            ZoneInfo(config["timezone"])
        if not isinstance(config.get("channels", {}), dict) or set(config.get("channels", {})) - {*FEATURE_UNITS, *TARGET_UNITS}:
            raise ValueError("channels 僅接受已正規化的製程／品質欄位。")
        result = TemporalProfile(config["version"], config["source"], ChannelTime(**config["identity"]),
                               tuple((k, ChannelTime(**v)) for k, v in config.get("channels", {}).items()),
                               config.get("timezone"), config.get("revision_evidence", False))
        for timing in (result.identity, *(v for k, v in result.channels)):
            if not all(isinstance(v, str) and v.strip() for v in (timing.available_at, timing.occurred_at)):
                raise ValueError("available_at／occurred_at 需要明確原始欄名。")
        return result
    if dataset and dataset.source_kind == "mock" and dataset.metadata.get("version") == "c-fixtures-v1":
        channel = ChannelTime("available_at")
        return TemporalProfile("c-mock-row-release-v1", "C 專用列內共同可得測試假設，非正式時間契約",
                               channel, tuple((k, channel) for k in (*FEATURE_UNITS, *TARGET_UNITS)))
    return None


def aware(value, timezone=None):
    t = pd.Timestamp(value)
    if pd.isna(t):
        raise ValueError("缺時間")
    if t.tzinfo is None:
        if not timezone:
            raise ValueError("未知時區")
        t = t.tz_localize(timezone, ambiguous="raise", nonexistent="raise")
    return t.tz_convert("Asia/Taipei")


def build_timeline(dataset, cohort, config=None):
    try:
        profile = profile_for(dataset, config)
    except (TypeError, ValueError, KeyError) as exc:
        profile, config_error = None, str(exc)
    else:
        config_error = "缺可靠時間 profile；AVAILABILITY_ASSUMED 不是發布時間證據。"
    signature = (dataset.source_id if dataset else "", config, asdict(profile) if profile else None,
                 tuple(cohort.get("source_row", ())))
    stream = sha256(json.dumps(signature, default=str, sort_keys=True).encode()).hexdigest()
    frame = cohort.copy(deep=True)
    raw = dataset.raw_frame.copy(deep=True) if dataset else pd.DataFrame()
    if profile is None:
        return Timeline(stream, None, frame, raw, reasons=(config_error,))
    for name in ("root_roll_id", "aligned_sample_id", "material_md_start_m", "material_md_end_m"):
        if name not in frame and name in raw:
            frame[name] = frame.source_row.map(raw[name])
    events, reasons, diagnostics = [], [], []
    # Source names can be mapped, but temporal names refer to explicitly declared raw columns.
    def values(row):
        n = int(row.source_row)
        v = row.to_dict()
        if n in raw.index:
            v.update(raw.loc[n].to_dict())
        return v
    def event(row, v, name, timing):
        try:
            if timing.availability_flag and str(v.get(timing.availability_flag, "")) not in {"1", "1.0", "True"}:
                raise ValueError("TARGET_UNAVAILABLE")
            if name in TARGET_UNITS:
                from c_dashboard.visualization.sources import LABEL_FLAGS, TARGET_PREFIX
                flag = LABEL_FLAGS[name]
                if flag in v and str(v[flag]) not in {"1", "1.0", "True"}:
                    raise ValueError("TARGET_UNAVAILABLE")
                if "quality_label_available" in v and str(v["quality_label_available"]) not in {"1", "1.0", "True"}:
                    raise ValueError("AVAILABILITY_CONFLICT")
                if v.get(TARGET_PREFIX[name] + "_label_scope", v.get("label_scope", "segment")) != "segment":
                    raise ValueError("INCOMPATIBLE_LABEL_SCOPE")
                if v.get(TARGET_PREFIX[name] + "_label_reason"):
                    raise ValueError("UPSTREAM_LABEL_UNAVAILABLE")
                if name == "appearance_ng" and "appearance_ng_flag" in v and "appearance_spec_pass_flag" in v:
                    ng, passed = float(v["appearance_ng_flag"]), float(v["appearance_spec_pass_flag"])
                    if ng not in (0, 1) or passed != 1-ng or float(v[name]) != ng:
                        raise ValueError("APPEARANCE_FLAG_CONFLICT")
            if name in TARGET_UNITS and not profile.revision_evidence and str(v.get("is_retest", "0")).lower() in {"1", "true", "1.0"}:
                raise ValueError("RETEST_HISTORY_UNCONFIRMED")
            # A loader fallback is never evidence for an undeclared raw field.
            a = aware(v.get(timing.available_at) if timing.available_at in raw.columns else None, profile.timezone)
            t = aware(v.get(timing.occurred_at), profile.timezone)
            c = aware(v.get(timing.completed_at), profile.timezone) if timing.completed_at else t
            if a < t or a < c or c < t:
                raise ValueError("INVALID_TIME_ORDER")
            return ReplayEvent(int(row.source_row), name, t, a)
        except (ValueError, TypeError, OverflowError) as exc:
            reason = str(exc)
            if not reason.isupper():
                reason = "MISSING_OR_INVALID_TIME：缺時間、時間無效或未知時區"
            message = f"列 {int(row.source_row)}／{name}：{reason}"
            reasons.append(message)
            try:
                known = aware(v.get(timing.available_at), profile.timezone).isoformat()
            except (ValueError, TypeError, OverflowError):
                known = None  # A capability limitation, never an invented release time.
            # A known publication slot still occurs when its target is invalid.
            # Otherwise future validity flags would change the advertised timeline.
            if known and name != "__identity__":
                try:
                    occurred = aware(v.get(timing.occurred_at), profile.timezone)
                    completed = aware(v.get(timing.completed_at), profile.timezone) if timing.completed_at else occurred
                    identity_at = aware(v.get(profile.identity.available_at), profile.timezone)
                    a = pd.Timestamp(known)
                    if a >= completed >= occurred and a >= identity_at:
                        events.append(ReplayEvent(int(row.source_row), "__unavailable__" + name, occurred, a))
                except (ValueError, TypeError, OverflowError):
                    pass
            diagnostics.append((int(row.source_row), name, known, message))
            return None
    for _, row in frame.iterrows():
        v = values(row)
        base = event(row, v, "__identity__", profile.identity)
        if base is None:
            continue
        events.append(base)
        for name, timing in profile.channels:
            if name not in frame:
                continue
            e = event(row, v, name, timing)
            if e and e.available_at >= base.available_at:
                events.append(e)
            elif e:
                reasons.append(f"列 {int(row.source_row)}／{name}：早於材料識別可得時間")
    groups = {}
    for e in sorted(events, key=lambda e: (e.available_at, e.source_row, e.field)):
        groups.setdefault(e.available_at, []).append(e)
    return Timeline(stream, profile, frame, raw, tuple(tuple(g) for g in groups.values()), tuple(reasons), tuple(diagnostics))
