"""C presentation projections only; no JOIN, label selection or spec pivot."""

from dataclasses import dataclass

import pandas as pd

from c_dashboard.data.schema import TARGET_UNITS

LABEL_FLAGS = dict(zip(TARGET_UNITS, (
    "peel_label_available", "md_label_available", "td_label_available",
    "heat_label_available", "appearance_label_available")))
TARGET_PREFIX = dict(zip(TARGET_UNITS, ("peel", "md", "td", "heat", "appearance")))
BASE_METADATA = (
    "root_roll_id", "aligned_sample_id", "material_md_start_m", "material_md_end_m",
    "dataset_version", "schema_version", "alignment_version", "label_version",
    "spec_version", "spec_source", "label_source", "label_scope", "inspection_method",
    "test_method_version", "inspection_id", "sampling_event_id", "source_segment_ids",
    "alignment_status", "label_available_at", "quality_label_available",
)


@dataclass(frozen=True)
class SourceProfile:
    kind: str = "legacy-csv"
    version: str = "c-chart-source-v1"
    dataset_version: str = "c-local-v1"
    schema_version: str = "c-view-v1"
    alignment_version: str = "not-applicable"
    label_version: str = "c-local-labels-v1"
    spec_version: str = "not-provided"
    label_source: str = "simulated_inspection"
    # Explicit method mapping, not a formal cross-team contract.
    methods: tuple[tuple[str, str], ...] = tuple(
        (t, "online_vision" if t == "appearance_ng" else "laboratory_segment") for t in TARGET_UNITS)


def metadata_columns(rows):
    return tuple(n for n in rows if n in BASE_METADATA or n.endswith((
        "_label_available", "_label_reason", "_label_source", "_label_scope",
        "_label_method", "_label_available_at", "_coverage")))


def has_projection_metadata(rows):
    return any(n in rows for n in ("root_roll_id", "aligned_sample_id", "label_source", "label_scope",
                                  "quality_label_available", *LABEL_FLAGS.values()))


def infer_profile(rows, source_kind):
    if has_projection_metadata(rows):
        return SourceProfile(kind="unresolved")
    return SourceProfile(kind="c-mock" if source_kind == "mock" else "legacy-csv")


def profile_for_workspace(workspace, rows):
    dataset = workspace.data.dataset
    kind = dataset.source_kind if dataset else "not-loaded"
    manifest = dataset.metadata.get("canonical_manifest") if dataset is not None else None
    if isinstance(manifest, dict):
        profile_kind = "synthetic-ground-truth" if manifest.get("profile", "").startswith("synthetic") else "segment-inspection"
        return SourceProfile(
            kind=profile_kind,
            version=manifest.get("manifest_schema", "fccl-canonical-dataset-1.0"),
            dataset_version=manifest.get("dataset_version", ""),
            schema_version=manifest.get("schema_version", ""),
            alignment_version=manifest.get("alignment_version", ""),
            label_version=manifest.get("profile", ""),
            spec_version=manifest.get("spec_version", ""),
            label_source="synthetic_ground_truth" if profile_kind == "synthetic-ground-truth" else "simulated_inspection",
        )
    manifest = dataset.metadata.get("canonical_manifest") if dataset is not None else None
    if isinstance(manifest, dict):
        profile_kind = "synthetic-ground-truth" if manifest.get("profile", "").startswith("synthetic") else "segment-inspection"
        return SourceProfile(
            kind=profile_kind,
            version=manifest.get("manifest_schema", "fccl-canonical-dataset-1.0"),
            dataset_version=manifest.get("dataset_version", ""),
            schema_version=manifest.get("schema_version", ""),
            alignment_version=manifest.get("alignment_version", ""),
            label_version=manifest.get("profile", ""),
            spec_version=manifest.get("spec_version", ""),
            label_source="synthetic_ground_truth" if profile_kind == "synthetic-ground-truth" else "simulated_inspection",
        )
    # The old loader retains these only in raw_frame. Never read raw values as
    # an already validated projection or let them silently bypass label flags.
    if dataset is not None and has_projection_metadata(dataset.raw_frame):
        return SourceProfile(kind="unresolved")
    return infer_profile(rows, kind)


def source_context(rows):
    context = []
    for name in metadata_columns(rows):
        if name.endswith(("_label_reason", "_label_available")) or name == "quality_label_available":
            continue
        values = tuple(str(v) for v in rows[name].dropna().unique())
        if values:
            context.append((name, ", ".join(values[:4]) + (" …" if len(values) > 4 else "")))
    return tuple(context)


def label_eligibility(rows, target, profile):
    """Use upstream decisions. Reject mixed/unknown semantics, never choose labels."""
    allowed = pd.Series(True, index=rows.index)
    reasons = {}

    def exclude(mask, code):
        mask = mask.fillna(True).astype(bool)
        count = int((allowed & mask).sum())
        if count:
            reasons[code] = reasons.get(code, 0) + count
        allowed.loc[mask] = False

    if profile.kind in {"c-mock", "legacy-csv"} and not has_projection_metadata(rows):
        return allowed, ()
    if profile.kind not in {"segment-inspection", "synthetic-ground-truth"}:
        exclude(allowed.copy(), "SOURCE_PROFILE_REQUIRED：正式來源投影／跨組整合待確認")
        return allowed, tuple(reasons.items())
    if not all((profile.version, profile.dataset_version, profile.schema_version,
                profile.alignment_version, profile.label_version)):
        exclude(allowed.copy(), "MISSING_SOURCE_VERSIONS")
        return allowed, tuple(reasons.items())
    prefix = TARGET_PREFIX[target]

    def series(name, fallback=None):
        column = name if name in rows else fallback
        return rows[column] if column in rows else pd.Series(None, index=rows.index, dtype=object)

    for name in ("root_roll_id", "aligned_sample_id"):
        exclude(series(name).isna() | series(name).astype(str).str.strip().eq(""), "MISSING_" + name.upper())
    start = pd.to_numeric(series("material_md_start_m"), errors="coerce")
    end = pd.to_numeric(series("material_md_end_m"), errors="coerce")
    exclude(~(start.ge(0) & end.gt(start) & end.lt(float("inf"))), "INVALID_MD_INTERVAL")
    scope = series(prefix + "_label_scope", "label_scope")
    exclude(scope.ne("segment"), "INCOMPATIBLE_LABEL_SCOPE：非區段標籤")
    expected = "synthetic_ground_truth" if profile.kind == "synthetic-ground-truth" else profile.label_source
    if not expected or (profile.kind == "segment-inspection" and expected == "synthetic_ground_truth"):
        exclude(allowed.copy(), "INVALID_LABEL_SOURCE_PROFILE")
    source = series(prefix + "_label_source", "label_source")
    exclude(source.ne(expected), "INCOMPATIBLE_LABEL_SOURCE：來源不得混算")
    reason = series(prefix + "_label_reason").fillna("").astype(str)
    for code in reason[reason.str.strip().ne("")].unique():
        exclude(reason.eq(code), code)
    if "alignment_status" in rows:
        exclude(rows.alignment_status.ne("valid"), "ALIGNMENT_INCOMPLETE")
    if profile.kind == "segment-inspection":
        flag = LABEL_FLAGS[target]
        if flag not in rows:
            exclude(allowed.copy(), "MISSING_TARGET_AVAILABILITY：" + flag)
        else:
            exclude(pd.to_numeric(rows[flag], errors="coerce").ne(1), "TARGET_LABEL_UNAVAILABLE：" + flag)
            if "quality_label_available" in rows:
                exclude(pd.to_numeric(rows.quality_label_available, errors="coerce").ne(1)
                        & pd.to_numeric(rows[flag], errors="coerce").eq(1), "AVAILABILITY_CONFLICT")
        method = series(prefix + "_label_method", "inspection_method")
        expected_method = dict(profile.methods).get(target)
        if not expected_method:
            exclude(allowed.copy(), "MISSING_TARGET_METHOD_MAPPING")
        else:
            exclude(method.ne(expected_method), "INCOMPATIBLE_LABEL_METHOD")
        method_version = series("test_method_version")
        exclude(method_version.isna() | method_version.astype(str).str.strip().eq(""), "MISSING_TEST_METHOD_VERSION")
    else:
        # The explicit synthetic profile declares complete truth validity;
        # if per-target flags are supplied, they still cannot be ignored.
        if LABEL_FLAGS[target] in rows:
            exclude(pd.to_numeric(rows[LABEL_FLAGS[target]], errors="coerce").ne(1), "TARGET_LABEL_UNAVAILABLE")
    for name in ("dataset_version", "schema_version", "alignment_version", "label_version"):
        if name in rows:
            exclude(rows[name].ne(getattr(profile, name)), "SOURCE_VERSION_MISMATCH：" + name)
    for name in ("spec_version", "test_method_version", prefix + "_label_method"):
        if name in rows and rows.loc[allowed, name].fillna("not-provided").nunique() > 1:
            exclude(allowed.copy(), "INCOMPATIBLE_METADATA：" + name)
    return allowed, tuple(reasons.items())
