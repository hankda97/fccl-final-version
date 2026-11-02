"""Pure visible-slice analysis. No file, UI, model or global-data access."""

from dataclasses import replace

from c_dashboard.data.schema import CONTINUOUS_TARGETS, TARGET_UNITS
from c_dashboard.spc.baseline import frame_signature, natural_samples
from c_dashboard.spc.config import RuleConfig, digest
from c_dashboard.spc.rules import detect_signals
from c_dashboard.spc.subgroups import finite, group_inputs, text_id, timestamp
from c_dashboard.spc.types import RawMeasurement, SpcEvent, SpcResult, TargetResult


def compute_spc(visible_rows, source_context, baseline=None, rules=RuleConfig(), analysis_scope_id=""):
    profile = source_context.profile
    scope = analysis_scope_id or digest((source_context.source_id, source_context.mapping_version,
                                         frame_signature(visible_rows)))
    common = list(source_context.issues)
    if profile is None:
        common.append("MISSING_SAMPLING_EVIDENCE")
    if baseline is None:
        common.append("BASELINE_UNAVAILABLE")
    elif profile is not None:
        if baseline.profile_signature != profile.signature():
            common.append("BASELINE_PROFILE_MISMATCH")
        if set(natural_samples(visible_rows)).intersection(baseline.natural_samples):
            common.append("HISTORY_SAMPLE_OVERLAP")
    if rules.version != "c-spc-rules-v1":
        common.append("UNSUPPORTED_RULE_VERSION")
    raw, available, appearances = [], [], []
    for ordinal, (_, row) in enumerate(visible_rows.iterrows()):
        t = timestamp(row.get("timestamp"))
        a = timestamp(row.get("available_at"))
        if a is not None:
            available.append(a)
        if t is not None:
            for name in CONTINUOUS_TARGETS:
                value = finite(row.get(name))
                if value is not None:
                    source_row = finite(row.get("source_row"))
                    raw.append(RawMeasurement(name, t.isoformat(), value, text_id(row.get("product_batch", "")),
                                              int(source_row) if source_row is not None else ordinal + 2))
        label = finite(row.get("appearance_ng"))
        if bool(row.get("identity_valid", False)) and label in (0.0, 1.0):
            appearances.append(int(label))
    targets, events = [], []
    for name in CONTINUOUS_TARGETS:
        groups, input_reasons = group_inputs(visible_rows, profile, name)
        # A pure caller may provide a different slice: never apply a future
        # calibration to observations before the profile's fixed origin.
        origin = timestamp(profile.monitoring_origin) if profile else None
        checked = []
        for group in groups:
            if origin is not None and any(t is not None and t < origin
                                         for t in (timestamp(group.timestamp), timestamp(group.completed_at))):
                group = replace(group, mean=None, span=None, break_before=True,
                                reasons=tuple(dict.fromkeys((*group.reasons, "MONITORING_BEFORE_ORIGIN"))))
            if checked and not checked[-1].valid:
                group = replace(group, break_before=True)
            checked.append(group)
        groups = tuple(checked)
        reasons = list(dict.fromkeys((*common, *input_reasons)))
        base = baseline.target(name) if baseline else None
        if base:
            reasons.extend(base.reasons)
            if common:
                base = replace(base, cl=None, ucl=None, lcl=None,
                               reasons=tuple(dict.fromkeys((*base.reasons, *common))))
        if groups and not groups[-1].valid:
            reasons.extend(groups[-1].reasons)
        valid_base = base is not None and base.valid
        detected = detect_signals(groups, base) if valid_base and not common else ()
        for index, rule, sequence in detected:
            g = groups[index]
            event_id = digest((source_context.source_id, scope, baseline.version, rules.version,
                               name, rule, g.batch, g.subgroup))
            events.append(SpcEvent(event_id, source_context.source_id, scope, name, rule, g.batch,
                                   g.subgroup, g.segment, g.completed_at, g.mean,
                                   base.cl, base.ucl, base.lcl, sequence, g.source_rows))
        latest_signal = bool(groups) and any(i == len(groups)-1 for i, _, _ in detected)
        if not valid_base or not groups or not groups[-1].valid or common:
            status = "無法判定 SPC 狀態"
        elif latest_signal:
            status = "最新子組觸發實測 SPC 訊號"
        else:
            status = "未偵測所啟用規則訊號（不代表產品合格）"
        targets.append(TargetResult(name, TARGET_UNITS[name], groups, base,
                                    tuple(dict.fromkeys(reasons)), status))
    return SpcResult(source_context.source_id, scope, max(available).isoformat() if available else None,
                     profile.version if profile else None, rules.version, baseline, tuple(targets),
                     tuple(events), tuple(raw), len(appearances), sum(appearances))
