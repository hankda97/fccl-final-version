import json
from copy import deepcopy
from pathlib import Path
import shutil

import pandas as pd

from c_dashboard.data.canonical import load_canonical_projection
from c_dashboard.data.session import commit_dataset, set_filters
from c_dashboard.quality.config import FEATURE_ALLOWLIST, PARAMETER_CONTROLS
from c_dashboard.spc.controller import analyze_workspace
from c_dashboard.spc.incidents import group_spc_incidents
from c_dashboard.spc.sources import spc_source_for_dataset
from c_dashboard.state import ensure_workspace
from fccl_ml.config import FEATURES


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "generated_data/model_dataset_v2/synthetic-ground-truth-v2"
INSPECTION = ROOT / "generated_data/model_dataset_v2/simulated-inspection-v2"


def copied(tmp_path):
    target = tmp_path / "canonical"
    shutil.copytree(SOURCE, target)
    return target


def test_valid_canonical_sidecar_is_verified_without_display_row_grouping():
    result = load_canonical_projection(SOURCE)
    assert result.accepted
    assert result.metadata["spc_evidence"] is not None
    assert not result.metadata["spc_issues"]
    assert result.frame.subgroup_id.fillna("").eq("").all()
    spc = result.metadata["spc_evidence"]["frame"]
    assert spc.groupby("subgroup_id").size().eq(5).all()


def test_spc_phase_and_cohort_flags_never_enter_model_or_whatif_inputs():
    forbidden = {"synthetic_phase", "baseline_candidate", "monitoring_eligible", "spc_condition_code"}
    assert forbidden.isdisjoint(FEATURES)
    assert forbidden.isdisjoint(FEATURE_ALLOWLIST)
    assert forbidden.isdisjoint(PARAMETER_CONTROLS)
    result = load_canonical_projection(SOURCE)
    assert forbidden.isdisjoint(result.frame.columns)
    assert forbidden <= set(result.metadata["spc_evidence"]["frame"].columns)


def test_canonical_source_separates_fixed_history_and_monitoring_cohorts():
    dataset = load_canonical_projection(SOURCE)
    source = spc_source_for_dataset(dataset)
    assert source.profile is not None
    assert source.history.groupby("subgroup_id").ngroups == 25
    assert source.history.dataset_split.eq("train").all()
    assert source.history.synthetic_phase.eq("stable").all()
    assert source.monitoring.dataset_split.isin(["validation", "test"]).all()
    assert not set(source.history.specimen_id) & set(source.monitoring.specimen_id)
    assert source.history.timestamp.max() < source.monitoring.timestamp.min()
    assert source.monitoring.timestamp.min() == pd.Timestamp(source.profile.monitoring_origin)
    workspace = ensure_workspace({})
    assert commit_dataset(workspace, dataset)
    result = analyze_workspace(workspace)
    assert result.baseline is not None
    assert all(target.baseline.valid for target in result.targets)
    version = result.baseline.version
    set_filters(workspace, "ROLL-0121", None, None)
    filtered = analyze_workspace(workspace)
    assert filtered.baseline.version == version
    assert all(group.batch == "ROLL-0121" for target in filtered.targets for group in target.groups)


def test_canonical_alarm_projection_conserves_and_compresses_raw_events():
    dataset = load_canonical_projection(SOURCE)
    workspace = ensure_workspace({})
    assert commit_dataset(workspace, dataset)
    result = analyze_workspace(workspace)
    incidents = group_spc_incidents(result)
    assert len(result.events) == 2913
    assert len(incidents) == 309
    assert sum(incident.event_count for incident in incidents) == len(result.events)
    assert {event.event_id for event in result.events} == {
        event_id for incident in incidents for event_id in incident.event_ids
    }

    set_filters(workspace, "ROLL-0121", None, None)
    roll = analyze_workspace(workspace)
    roll_incidents = group_spc_incidents(roll)
    assert (len(roll.events), len(roll_incidents)) == (57, 3)
    assert sum(incident.event_count for incident in roll_incidents) == 57


def test_canonical_spc_cache_identity_tracks_sidecar_profile_and_history():
    dataset = load_canonical_projection(SOURCE)
    original = spc_source_for_dataset(dataset)
    repeat = spc_source_for_dataset(dataset)
    assert repeat.identity == original.identity
    workspace = ensure_workspace({})
    commit_dataset(workspace, dataset)
    first = analyze_workspace(workspace)
    assert analyze_workspace(workspace) is first
    baseline_version = first.baseline.version

    changed = deepcopy(dataset)
    changed.metadata["spc_evidence"]["sidecar_hash"] = "changed-test-hash"
    changed.source_id = "changed-source-id"
    changed_source = spc_source_for_dataset(changed)
    assert changed_source.identity != original.identity
    assert changed_source.profile.history_hash != original.profile.history_hash
    commit_dataset(workspace, changed)
    second = analyze_workspace(workspace)
    assert second is not first and second.baseline.version != baseline_version


def test_missing_or_tampered_sidecar_only_disables_spc(tmp_path):
    for mutation in ("missing", "tampered"):
        target = copied(tmp_path / mutation)
        sidecar = target / "spc_samples.csv"
        if mutation == "missing":
            sidecar.unlink()
        else:
            sidecar.write_bytes(sidecar.read_bytes() + b"\n")
        result = load_canonical_projection(target)
        assert result.accepted and len(result.frame) == 20_000
        assert result.metadata["spc_evidence"] is None
        assert result.metadata["spc_issues"]


def test_unsupported_spc_profile_version_only_disables_spc(tmp_path):
    target = copied(tmp_path)
    path = target / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["spc_profile"]["version"] = "future-version"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    result = load_canonical_projection(target)
    assert result.accepted and result.metadata["spc_evidence"] is None
    assert "UNSUPPORTED_SPC_PROFILE_VERSION" in result.metadata["spc_issues"]


def test_inspection_profile_has_no_borrowed_spc_baseline_but_data_stays_available():
    dataset = load_canonical_projection(INSPECTION)
    assert dataset.accepted and len(dataset.frame) == 20_000
    source = spc_source_for_dataset(dataset)
    assert source.profile is None and source.history is None and source.monitoring is None
    workspace = ensure_workspace({})
    commit_dataset(workspace, dataset)
    result = analyze_workspace(workspace)
    assert result.baseline is None
    assert all("MISSING_SAMPLING_EVIDENCE" in target.reasons for target in result.targets)
