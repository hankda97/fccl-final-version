import json
from hashlib import sha256
from pathlib import Path
import shutil

from jsonschema import validate
import pytest

from fccl_ml.artifacts import ArtifactValidationError, load_registry, load_target_bundle
from fccl_ml.config import FEATURES, TARGETS
from fccl_ml.validation import file_sha256


PROJECT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT / "artifacts" / "synthetic_v2"


@pytest.mark.parametrize("profile", ["synthetic-ground-truth-v2", "simulated-inspection-v2"])
def test_actual_registry_has_five_separate_loadable_targets(profile):
    root = ARTIFACT_ROOT / profile
    registry = load_registry(root)
    assert set(registry["targets"]) == set(TARGETS)
    schema = json.loads((PROJECT / "fccl_ml/schemas/model_manifest.schema.json").read_text(encoding="utf-8"))
    for target, entry in registry["targets"].items():
        bundle, manifest = load_target_bundle(root, entry)
        validate(instance=manifest, schema=schema)
        assert bundle["target"] == target
        assert tuple(manifest["feature_names"]) == FEATURES
        assert manifest["profile"] == profile


def _copy_target(tmp_path):
    source_root = ARTIFACT_ROOT / "synthetic-ground-truth-v2"
    registry = load_registry(source_root)
    entry = registry["targets"]["peel_strength_n_mm"]
    source_manifest = source_root / entry["manifest"]
    target_dir = tmp_path / "version" / "peel"
    shutil.copytree(source_manifest.parent, target_dir)
    manifest_path = target_dir / "manifest.json"
    copied_entry = {"manifest": "version/peel/manifest.json", "manifest_sha256": file_sha256(manifest_path)}
    return copied_entry, manifest_path, target_dir


def test_loader_rejects_tampered_bundle_before_deserialization(tmp_path):
    entry, manifest_path, target_dir = _copy_target(tmp_path)
    bundle_path = target_dir / "bundle.joblib"
    with bundle_path.open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ArtifactValidationError, match="ARTIFACT_HASH_MISMATCH:bundle_path"):
        load_target_bundle(tmp_path, entry)


def test_loader_rejects_incompatible_package_manifest(tmp_path):
    entry, manifest_path, _ = _copy_target(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["packages"]["python"] = "0.0.0"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    entry["manifest_sha256"] = file_sha256(manifest_path)
    with pytest.raises(ArtifactValidationError, match="PACKAGE_INCOMPATIBLE"):
        load_target_bundle(tmp_path, entry)

