"""Tree SHAP over hash-verified Champion bundles and fixed train backgrounds."""

from __future__ import annotations

from hashlib import sha256
import json

import numpy as np
import pandas as pd

from c_dashboard.adapters.explanations import (
    ExplanationInfo,
    ExplanationManifest,
    ExplanationPayload,
    ExplanationRequest,
    ExplanationResponse,
)
from c_dashboard.data.schema import TARGET_UNITS
from fccl_ml.paths import resolve_within
from fccl_ml.validation import file_sha256


EXPLANATION_VERSION = "tree-shap-v1"
ADDITIVITY_ATOL = 5e-3


def build_explanation_manifest(adapter) -> ExplanationManifest:
    info = adapter.describe()
    manifests = adapter.manifests
    supported = tuple(info.supports_targets)
    representative = next(iter(manifests.values()), None)
    if representative is None:
        return ExplanationManifest(
            manifest_id="formal-shap-unavailable",
            model_source=info.source,
            model_type="RandomForest Champion",
            model_version=info.version or "unavailable",
            schema_version="unavailable",
            feature_version="unavailable",
            preprocessing_version="unavailable",
            label_version="unavailable",
            spec_version="unavailable",
            dataset_version="unavailable",
            feature_names=(),
            feature_units=(),
            supported_targets=(),
            output_scales=(),
            output_units=(),
            class_labels=(),
            background_source="unavailable",
            compatible_schemas=(),
            compatible_label_versions=(),
            compatible_source_kinds=(),
            unavailable_targets=tuple(sorted(adapter.unavailable.items())),
        )
    background_identity = sha256(
        json.dumps(
            {target: manifests[target]["background_sha256"] for target in supported},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    profile = representative["profile"]
    source_kind = "synthetic-ground-truth" if profile.startswith("synthetic") else "segment-inspection"
    units = tuple(representative["feature_units"][name] for name in representative["feature_names"])
    output_scales = tuple((target, manifests[target]["output_scale"]) for target in supported)
    output_units = tuple(
        (target, "probability" if target == "appearance_ng" else TARGET_UNITS[target])
        for target in supported
    )
    appearance = manifests.get("appearance_ng", {})
    return ExplanationManifest(
        manifest_id=f"{representative['profile']}:{info.version}:tree-shap",
        model_source=info.source,
        model_type="RandomForest Champion",
        model_version=info.version or "unavailable",
        schema_version=representative["schema_version"],
        feature_version=representative["feature_version"],
        preprocessing_version=representative["preprocessing_version"],
        label_version=representative["label_version"],
        spec_version=representative["spec_version"],
        dataset_version=representative["dataset_version"],
        feature_names=tuple(representative["feature_names"]),
        feature_units=units,
        supported_targets=supported,
        output_scales=output_scales,
        output_units=output_units,
        class_labels=tuple(int(value) for value in appearance.get("class_labels", ())),
        background_source=f"verified-train-backgrounds:{background_identity}",
        compatible_schemas=(representative["schema_version"],),
        compatible_label_versions=(representative["label_version"],),
        compatible_source_kinds=(source_kind,),
        unavailable_targets=tuple(sorted(adapter.unavailable.items())),
    )


class FormalTreeShapProvider:
    """Explain only already-verified adapter bundles; never read canonical/global CSV."""

    def __init__(self, adapter):
        self.adapter = adapter
        self._manifest = build_explanation_manifest(adapter)
        self._explainers: dict[tuple[str, str, str, str], object] = {}

    def describe(self) -> ExplanationInfo:
        manifest = self._manifest
        available = bool(manifest.supported_targets)
        return ExplanationInfo(
            source="已驗證 Champion Tree SHAP",
            model_source=manifest.model_source,
            model_version=manifest.model_version,
            preprocessing_version=manifest.preprocessing_version,
            explanation_version=EXPLANATION_VERSION,
            available=available,
            feature_names=manifest.feature_names,
            feature_units=manifest.feature_units,
            supported_targets=manifest.supported_targets,
            output_scales=manifest.output_scales,
            output_units=manifest.output_units,
            background_source=manifest.background_source,
            message="固定 train 背景抽樣；Synthetic 模型解釋不代表因果關係。" if available else "沒有可解釋的已驗證目標模型。",
            manifest=manifest,
        )

    def explain(self, request: ExplanationRequest) -> ExplanationResponse:
        if request.info != self.describe():
            raise ValueError("EXPLANATION_PROVIDER_CONTEXT_MISMATCH")
        target = request.target
        if target not in self.adapter.bundles:
            return ExplanationResponse(request, status="unavailable", message="選定目標模型不可用。")
        bundle = self.adapter.bundles[target]
        manifest = self.adapter.manifests[target]
        pipeline = bundle["pipeline"]
        imputer = pipeline.named_steps["imputer"]
        model = pipeline.named_steps["model"]
        background = self._verified_background(target, manifest)
        background_values = imputer.transform(background.loc[:, request.feature_names])
        request_values = imputer.transform(pd.DataFrame(request.feature_values, columns=request.feature_names))
        explainer = self._explainer(target, manifest, model, background_values)
        explanation = explainer(request_values, check_additivity=False)
        contributions = np.asarray(explanation.values, dtype=float)
        bases = np.asarray(explanation.base_values, dtype=float)
        labels: tuple[int, ...] = ()
        output_index = None
        if target == "appearance_ng":
            labels = tuple(int(value) for value in model.classes_)
            if 1 not in labels or labels != tuple(int(value) for value in manifest["class_labels"]):
                raise ValueError("MODEL_CLASS_MAPPING_MISMATCH")
            output_index = labels.index(1)
            if contributions.ndim != 3 or bases.ndim != 2:
                raise ValueError("UNSUPPORTED_CLASSIFICATION_SHAP_SHAPE")
            contributions = contributions[:, :, output_index]
            bases = bases[:, output_index]
            expected = model.predict_proba(request_values)[:, output_index]
        else:
            if contributions.ndim != 2:
                raise ValueError("UNSUPPORTED_REGRESSION_SHAP_SHAPE")
            expected = model.predict(request_values)
        reconstructed = bases + contributions.sum(axis=1)
        # Interventional Tree SHAP can accumulate small floating-point error on
        # deeper ensembles; reject material drift while tolerating <0.005 in
        # the declared output scale.
        if not np.allclose(reconstructed, expected, rtol=1e-5, atol=ADDITIVITY_ATOL):
            raise ValueError("SHAP_ADDITIVITY_CHECK_FAILED")
        payload = ExplanationPayload(
            sample_ids=request.sample_ids,
            feature_names=request.feature_names,
            feature_units=request.feature_units,
            feature_values=request.feature_values,
            contributions=contributions,
            base_values=bases,
            class_labels=labels,
            output_index=output_index,
        )
        return ExplanationResponse(request, payload=payload)

    def _verified_background(self, target: str, manifest: dict) -> pd.DataFrame:
        entry = self.adapter.entries[target]
        manifest_path = resolve_within(entry["manifest"], self.adapter.profile_root, must_exist=True)
        background_path = resolve_within(manifest["background_path"], manifest_path.parent, must_exist=True)
        # The manifest was verified during adapter construction, but recheck at
        # use time so a later filesystem change cannot enter an explanation.
        if file_sha256(background_path) != manifest["background_sha256"]:
            raise ValueError("SHAP_BACKGROUND_HASH_MISMATCH")
        return pd.read_csv(background_path)

    def _explainer(self, target: str, manifest: dict, model, background_values):
        key = (
            manifest["model_version"],
            target,
            manifest["background_sha256"],
            manifest["preprocessing_version"],
        )
        if key not in self._explainers:
            import shap
            self._explainers[key] = shap.TreeExplainer(
                model,
                data=background_values,
                feature_perturbation="interventional",
                model_output="probability" if target == "appearance_ng" else "raw",
            )
        return self._explainers[key]
