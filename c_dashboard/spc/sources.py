"""Explicitly bind registered C test bytes to their sampling evidence."""

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd

from c_dashboard.spc.baseline import frame_signature
from c_dashboard.spc.config import digest, profile_from_dict

SPC_FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "c_spc"


@dataclass(frozen=True)
class SpcSourceData:
    profile: object | None
    history: pd.DataFrame | None = None
    monitoring: pd.DataFrame | None = None
    identity: str = ""
    issues: tuple[str, ...] = ()
    baseline_source: str = ""


def load_c_profile():
    return profile_from_dict(json.loads((SPC_FIXTURES / "profile.json").read_text(encoding="utf-8")))


def spc_source_for_dataset(dataset):
    if dataset is None:
        return SpcSourceData(None, identity="not-loaded")
    if dataset.source_kind == "mock":
        profile = load_c_profile()
        if dict(profile.monitoring_hashes).get(dataset.source_name) != sha256(dataset.content).hexdigest():
            return SpcSourceData(None, identity=dataset.source_id)
        return SpcSourceData(profile, identity=digest((dataset.source_id, profile.signature())),
                             baseline_source="C 獨立歷史 Mock（固定基準）")
    if dataset.source_kind != "canonical-projection":
        return SpcSourceData(None, identity=dataset.source_id)
    evidence = dataset.metadata.get("spc_evidence")
    if not isinstance(evidence, dict):
        return SpcSourceData(None, identity=digest((dataset.source_id, "no-spc-evidence")),
                             issues=tuple(dataset.metadata.get("spc_issues", ())))
    definition = evidence["profile"]
    frame = evidence["frame"].copy()
    candidates = frame.loc[frame.baseline_candidate.eq(1)].copy()
    ordered_groups = (candidates.groupby("subgroup_id", as_index=False).timestamp.min()
                      .sort_values(["timestamp", "subgroup_id"]).subgroup_id.head(25))
    history = candidates.loc[candidates.subgroup_id.isin(set(ordered_groups))].copy()
    monitoring = frame.loc[frame.monitoring_eligible.eq(1)].copy()
    history_hash = digest((evidence["sidecar_hash"], frame_signature(history), definition["version"]))
    profile = profile_from_dict({
        "profile_id": definition["profile_id"], "version": definition["version"],
        "product": definition["product"], "recipe": definition["recipe"],
        "n": definition["subgroup_size"], "minimum_history_groups": definition["minimum_history_groups"],
        "independent_specimens": True, "monitoring_origin": definition["monitoring_origin"],
        "interval_seconds": definition["interval_seconds"], "conditions": definition["conditions"],
        "condition_tolerance": definition["condition_tolerance"],
        "environment_ranges": definition["environment_ranges"],
        "units": list(definition["units"].items()), "history_hash": history_hash,
    })
    identity = digest((dataset.source_id, evidence["sidecar_hash"], profile.signature(),
                       history_hash, frame_signature(monitoring)))
    return SpcSourceData(profile, history, monitoring, identity, (),
                         "Canonical Synthetic 合成資料示範基準（非產線）")


def profile_for_dataset(dataset):
    """Backward-compatible profile-only seam used by existing tests and callers."""
    return spc_source_for_dataset(dataset).profile
