"""Trusted, hash-verified artifact loading; joblib is never accepted from UI uploads."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform

import joblib

from .paths import resolve_within
from .validation import file_sha256


class ArtifactValidationError(ValueError):
    pass


REQUIRED_MANIFEST_FIELDS = {
    "artifact_schema", "manifest_id", "model_version", "profile", "target", "task_type",
    "feature_names", "feature_units", "target_unit", "schema_version", "feature_version",
    "preprocessing_version", "label_version", "spec_version", "dataset_version", "packages",
    "bundle_path", "bundle_sha256", "background_path", "background_sha256", "metrics_path", "metrics_sha256",
}


def load_registry(trusted_profile_root: Path | str, registry_path: Path | str = "registry.json") -> dict:
    root = Path(trusted_profile_root).resolve()
    path = resolve_within(registry_path, root, must_exist=True)
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("registry_schema") != "fccl-model-registry-1.0" or not isinstance(registry.get("targets"), dict):
        raise ArtifactValidationError("INVALID_REGISTRY")
    return registry


def load_target_bundle(trusted_profile_root: Path | str, entry: dict, *, enforce_packages: bool = True) -> tuple[dict, dict]:
    root = Path(trusted_profile_root).resolve()
    manifest_path = resolve_within(entry.get("manifest", ""), root, must_exist=True)
    if entry.get("manifest_sha256") != file_sha256(manifest_path):
        raise ArtifactValidationError("MANIFEST_HASH_MISMATCH")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = REQUIRED_MANIFEST_FIELDS - set(manifest)
    if missing:
        raise ArtifactValidationError(f"MANIFEST_FIELDS_MISSING:{sorted(missing)}")
    manifest_dir = manifest_path.parent
    for path_field, hash_field in (("bundle_path", "bundle_sha256"), ("background_path", "background_sha256"), ("metrics_path", "metrics_sha256")):
        path = resolve_within(manifest[path_field], manifest_dir, must_exist=True)
        if file_sha256(path) != manifest[hash_field]:
            raise ArtifactValidationError(f"ARTIFACT_HASH_MISMATCH:{path_field}")
    if enforce_packages:
        current = {"python": platform.python_version()}
        for package in ("numpy", "pandas", "scikit-learn", "joblib", "shap"):
            current[package] = importlib.metadata.version(package)
        incompatible = {name: (version, current.get(name)) for name, version in manifest["packages"].items() if current.get(name) != version}
        if incompatible:
            raise ArtifactValidationError(f"PACKAGE_INCOMPATIBLE:{incompatible}")
    bundle_path = resolve_within(manifest["bundle_path"], manifest_dir, must_exist=True)
    bundle = joblib.load(bundle_path)
    if tuple(bundle.get("feature_names", ())) != tuple(manifest["feature_names"]) or bundle.get("target") != manifest["target"]:
        raise ArtifactValidationError("BUNDLE_MANIFEST_MISMATCH")
    return bundle, manifest

