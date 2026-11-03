"""Hash-verified Synthetic formal adapter implementing the existing C port."""

from __future__ import annotations

from collections.abc import Sequence
import math
from pathlib import Path

import pandas as pd

from c_dashboard.adapters.base import AdapterInfo, PredictionInput, PredictionRecord, PredictionResult
from c_dashboard.data.schema import TARGET_UNITS
from fccl_ml.artifacts import ArtifactValidationError, load_registry, load_target_bundle
from fccl_ml.config import FEATURES, TARGETS
from fccl_ml.training import predict_bundle


FORMAL_SOURCE = "Synthetic 正式模型 artifact（非產線）"


class FormalModelAdapter:
    def __init__(self, trusted_profile_root: Path | str, source_manifest: dict | None, *, enforce_packages: bool = True):
        self.profile_root = Path(trusted_profile_root).resolve()
        self.source_manifest = source_manifest
        self.bundles: dict[str, dict] = {}
        self.manifests: dict[str, dict] = {}
        self.entries: dict[str, dict] = {}
        self.unavailable: dict[str, str] = {}
        try:
            self.registry = load_registry(self.profile_root)
        except Exception as exc:
            self.registry = {"active_model_version": None, "targets": {}}
            self.unavailable = {target: f"REGISTRY_UNAVAILABLE:{exc}" for target in TARGETS}
            return
        for target in TARGETS:
            entry = self.registry.get("targets", {}).get(target)
            if not entry:
                self.unavailable[target] = "TARGET_ARTIFACT_MISSING"
                continue
            try:
                bundle, manifest = load_target_bundle(self.profile_root, entry, enforce_packages=enforce_packages)
                self._validate_compatibility(target, manifest)
            except Exception as exc:
                self.unavailable[target] = f"TARGET_ARTIFACT_UNAVAILABLE:{exc}"
                continue
            self.bundles[target] = bundle
            self.manifests[target] = manifest
            self.entries[target] = dict(entry)

    def _validate_compatibility(self, target: str, manifest: dict) -> None:
        source = self.source_manifest
        if not source:
            raise ArtifactValidationError("CANONICAL_SOURCE_PROFILE_REQUIRED")
        checks = {
            "profile": (manifest["profile"], source.get("profile")),
            "schema_version": (manifest["schema_version"], source.get("schema_version")),
            "feature_version": (manifest["feature_version"], source.get("feature_version")),
            "feature_names": (tuple(manifest["feature_names"]), tuple(source.get("feature_names", ()))),
            "feature_units": (manifest["feature_units"], source.get("feature_units")),
            "label_version": (manifest["label_version"], source.get("profile")),
            "spec_version": (manifest["spec_version"], source.get("spec_version")),
            "dataset_version": (manifest["dataset_version"], source.get("dataset_version")),
        }
        mismatches = [name for name, values in checks.items() if values[0] != values[1]]
        if target not in source.get("projection_rows", {}):
            mismatches.append("target_projection")
        if mismatches:
            raise ArtifactValidationError("SOURCE_MODEL_INCOMPATIBLE:" + ",".join(mismatches))

    def describe(self) -> AdapterInfo:
        available = tuple(target for target in TARGETS if target in self.bundles)
        message = "合成資料訓練模型；非真實產線效能或因果保證。"
        if self.unavailable:
            message += " 不可用目標：" + "；".join(f"{target}={reason}" for target, reason in self.unavailable.items())
        return AdapterInfo(
            source=FORMAL_SOURCE,
            version=self.registry.get("active_model_version"),
            available=bool(available),
            supports_shap=bool(available),
            message=message,
            supports_targets=available,
        )

    def manifest_hook(self) -> dict[str, dict]:
        return dict(self.manifests)

    def explanation_manifest(self):
        from c_dashboard.adapters.formal_explanations import build_explanation_manifest
        return build_explanation_manifest(self)

    def predict(self, samples: Sequence[PredictionInput]) -> PredictionResult:
        info = self.describe()
        if not samples:
            return PredictionResult(info, ())
        records = [PredictionRecord(sample.sample_id, {}, None, dict(self.unavailable), TARGET_UNITS.copy()) for sample in samples]
        frames = []
        row_errors: list[str | None] = []
        for sample in samples:
            values, problems = {}, []
            for name in FEATURES:
                try:
                    value = float(sample.features[name])
                except (KeyError, TypeError, ValueError):
                    problems.append(f"MISSING_OR_INVALID_FEATURE:{name}")
                    continue
                if not math.isfinite(value):
                    problems.append(f"NONFINITE_FEATURE:{name}")
                values[name] = value
            frames.append(values)
            row_errors.append(";".join(problems) if problems else None)
        for target, bundle in self.bundles.items():
            valid_indices, target_errors = [], {}
            ranges = bundle["supported_ranges"]
            for index, values in enumerate(frames):
                if row_errors[index]:
                    target_errors[index] = row_errors[index]
                    continue
                outside = [name for name in FEATURES if not ranges[name]["min"] <= values[name] <= ranges[name]["max"]]
                if outside:
                    target_errors[index] = "OUTSIDE_TRAINING_SUPPORT:" + ",".join(outside)
                else:
                    valid_indices.append(index)
            predicted = {}
            if valid_indices:
                matrix = pd.DataFrame([frames[index] for index in valid_indices], index=valid_indices)
                try:
                    values = predict_bundle(bundle, matrix)
                    predicted = values.to_dict()
                except Exception as exc:
                    for index in valid_indices:
                        target_errors[index] = f"INFERENCE_ERROR:{exc}"
            for index in range(len(samples)):
                current = records[index]
                targets = dict(current.targets)
                unavailable = dict(current.unavailable_targets or {})
                risk = current.appearance_ng_risk
                if index in target_errors:
                    unavailable[target] = target_errors[index]
                elif index in predicted:
                    if target == "appearance_ng":
                        risk = float(predicted[index])
                        targets[target] = int(risk >= float(bundle["threshold"]))
                    else:
                        targets[target] = float(predicted[index])
                    unavailable.pop(target, None)
                records[index] = PredictionRecord(current.sample_id, targets, risk, unavailable, TARGET_UNITS.copy())
        return PredictionResult(info, tuple(records))

