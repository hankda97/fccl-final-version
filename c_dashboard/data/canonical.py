"""Load an already-built canonical projection; never JOIN seven tables in C."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pandas as pd

from c_dashboard.data.loader import DataIssue, LoadResult, load_csv
from c_dashboard.data.schema import CONTINUOUS_TARGETS, MappingProfile, TARGET_UNITS
from fccl_ml.config import TARGETS
from fccl_ml.validation import file_sha256


SUPPORTED_SPC_PROFILE = "synthetic-xbar-profile-v1"


def _canonical_spc_evidence(root: Path, manifest: dict, canonical: pd.DataFrame, display: pd.DataFrame):
    profile = manifest.get("spc_profile")
    if not isinstance(profile, dict):
        return None, ("MISSING_SAMPLING_EVIDENCE",)
    try:
        if profile.get("version") != SUPPORTED_SPC_PROFILE:
            raise ValueError("UNSUPPORTED_SPC_PROFILE_VERSION")
        name = profile.get("source_file")
        if name != "spc_samples.csv":
            raise ValueError("INVALID_SPC_SIDECAR_NAME")
        path = root / name
        expected = manifest.get("output_hashes", {}).get(name)
        if not path.is_file() or not expected:
            raise ValueError("SPC_SIDECAR_MISSING")
        if file_sha256(path) != expected:
            raise ValueError("SPC_SIDECAR_HASH_MISMATCH")
        sidecar = pd.read_csv(path)
        required = {
            "aligned_sample_id", "sampling_event_id", "subgroup_id", "specimen_id",
            "root_roll_id", "dataset_split", "synthetic_phase", "material_md_start_m",
            "material_md_end_m", "observed_at", "sampled_at", "available_at",
            "spc_condition_code", "baseline_candidate", "monitoring_eligible",
        }
        if not required <= set(sidecar):
            raise ValueError("SPC_SIDECAR_COLUMNS_MISSING")
        if sidecar.aligned_sample_id.duplicated().any() or sidecar.specimen_id.duplicated().any():
            raise ValueError("SPC_SPECIMEN_REUSED")
        if not sidecar.groupby("subgroup_id").size().eq(int(profile["subgroup_size"])).all():
            raise ValueError("SPC_SUBGROUP_SIZE_MISMATCH")
        source = canonical.set_index("aligned_sample_id")
        if not set(sidecar.aligned_sample_id) <= set(source.index):
            raise ValueError("SPC_SAMPLE_NOT_CANONICAL")
        joined = sidecar.join(source[["root_roll_id", "dataset_split", "material_md_start_m", "material_md_end_m"]],
                              on="aligned_sample_id", rsuffix="_canonical")
        for name in ("root_roll_id", "dataset_split"):
            if not joined[name].astype(str).eq(joined[f"{name}_canonical"].astype(str)).all():
                raise ValueError("SPC_IDENTITY_MISMATCH:" + name)
        for name in ("material_md_start_m", "material_md_end_m"):
            if not pd.to_numeric(joined[name], errors="coerce").round(9).eq(
                    pd.to_numeric(joined[f"{name}_canonical"], errors="coerce").round(9)).all():
                raise ValueError("SPC_MD_MISMATCH:" + name)
        units = profile.get("units", {})
        if units != {name: TARGET_UNITS[name] for name in CONTINUOUS_TARGETS}:
            raise ValueError("SPC_UNIT_MISMATCH")
        base = display.set_index("segment_id", drop=False)
        spc = base.loc[sidecar.aligned_sample_id].copy().reset_index(drop=True)
        spc["material_segment_id"] = spc.segment_id
        spc["segment_id"] = sidecar.sampling_event_id.to_numpy()
        for name in ("product_batch", "subgroup_id", "specimen_id"):
            source_name = {"product_batch": "root_roll_id"}.get(name, name)
            spc[name] = sidecar[source_name].to_numpy()
        spc["timestamp"] = pd.to_datetime(sidecar.sampled_at).to_numpy()
        spc["available_at"] = pd.to_datetime(sidecar.available_at).to_numpy()
        spc["product_id"] = profile["product"]
        spc["recipe_id"] = profile["recipe"]
        for name in ("dataset_split", "synthetic_phase", "spc_condition_code",
                     "baseline_candidate", "monitoring_eligible", "aligned_sample_id"):
            spc[name] = sidecar[name].to_numpy()
        spc["source_row"] = range(2, len(spc) + 2)
        return {"profile": profile, "frame": spc, "sidecar_hash": expected}, ()
    except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError) as exc:
        return None, (str(exc),)


def load_canonical_projection(dataset_dir: Path | str) -> LoadResult:
    root = Path(dataset_dir).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    canonical_path = root / "canonical.csv"
    expected = manifest.get("output_hashes", {}).get("canonical.csv")
    if expected != file_sha256(canonical_path):
        raise ValueError("Canonical projection hash mismatch")
    frame = pd.read_csv(canonical_path)
    display = pd.DataFrame({
        "timestamp": frame.timestamp,
        "available_at": frame.timestamp,
        "product_batch": frame.root_roll_id,
        "segment_id": frame.aligned_sample_id,
        "subgroup_id": "",
        "specimen_id": "",
        "product_id": frame.product_id,
        "recipe_id": manifest["dataset_version"],
        "length_m": frame.material_md_end_m - frame.material_md_start_m,
        "position_m": frame.material_md_start_m,
    })
    for name in (*manifest["feature_names"], *TARGETS):
        display[name] = frame[name]
    content = display.to_csv(index=False, lineterminator="\n").encode("utf-8")
    result = load_csv(content, f"canonical-{manifest['profile']}.csv", source_kind="canonical-projection", profile=MappingProfile("版本化 canonical projection", manifest["schema_version"]))
    if not result.accepted:
        return result
    by_id = frame.set_index("aligned_sample_id")
    result.frame["root_roll_id"] = result.frame.segment_id.map(by_id.root_roll_id)
    result.frame["aligned_sample_id"] = result.frame.segment_id
    for name in ("material_md_start_m", "material_md_end_m", "process_phase"):
        result.frame[name] = result.frame.segment_id.map(by_id[name])
    for name, value in (
        ("dataset_version", manifest["dataset_version"]), ("schema_version", manifest["schema_version"]),
        ("alignment_version", manifest["alignment_version"]), ("label_version", manifest["profile"]),
        ("spec_version", manifest["spec_version"]), ("label_source", "synthetic_ground_truth" if manifest["profile"].startswith("synthetic") else "simulated_inspection"),
        ("label_scope", "segment"),
    ):
        result.frame[name] = value
    result.frame["alignment_status"] = result.frame.segment_id.map(by_id.alignment_valid).map({1: "valid", 0: "invalid"})
    availability_map = {
        "peel_strength_n_mm": "peel_label_available", "dimensional_stability_md_pct": "md_label_available",
        "dimensional_stability_td_pct": "td_label_available", "heat_resistance_c": "heat_label_available",
        "appearance_ng": "appearance_label_available",
    }
    for target, flag in availability_map.items():
        result.frame[flag] = result.frame.segment_id.map(by_id[f"{target}_available"]).fillna(0).astype(int)
    result.frame["quality_label_available"] = result.frame[list(availability_map.values())].max(axis=1)
    evidence, spc_issues = _canonical_spc_evidence(root, manifest, frame, result.frame)
    result.metadata = {"canonical_manifest": manifest, "profile": manifest["profile"],
                       "spc_evidence": evidence, "spc_issues": spc_issues}
    if spc_issues:
        result.issues.append(DataIssue("SPC_EVIDENCE_UNAVAILABLE", None, None,
                                      "SPC 取樣證據不可用：" + "；".join(spc_issues), "warning"))
    result.source_id = sha256((result.source_id + json.dumps(manifest, sort_keys=True, ensure_ascii=False)
                               + (evidence or {}).get("sidecar_hash", "missing")).encode()).hexdigest()
    result.settings = {
        "version": manifest["dataset_version"],
        "source": "Synthetic canonical projection",
        "quality_specs": manifest.get("quality_specs", {}),
        "appearance_ng_risk_threshold": 0.5,
    }
    return result

