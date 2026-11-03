from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from . import SCHEMA_VERSION
from .dataset import FEATURE_ALLOWLIST
from .generation import TARGETS, TRAINING_SEED


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = TRAINING_SEED
    rf_estimators: int = 60
    rf_max_depth: int = 10
    hgb_iterations: int = 120


def _metrics(y: pd.Series, pred: np.ndarray) -> dict[str, float]:
    return {"mae": float(mean_absolute_error(y, pred)), "rmse": float(mean_squared_error(y, pred) ** .5), "r2": float(r2_score(y, pred))}


def train_target(frame: pd.DataFrame, target: str, config: TrainingConfig = TrainingConfig(), *, drift_rolls: set[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if target not in TARGETS or "appearance" in target:
        raise ValueError("UNSUPPORTED_V3_TARGET")
    train = frame[frame.split == "train"]; val = frame[frame.split == "validation"]; test = frame[frame.split == "test"]
    if min(len(train), len(val), len(test)) == 0:
        raise ValueError("EMPTY_SPLIT")
    x_train, y_train = train.loc[:, FEATURE_ALLOWLIST], train[target]
    models = {
        "baseline": DummyRegressor(strategy="mean"),
        "random_forest": RandomForestRegressor(n_estimators=config.rf_estimators, max_depth=config.rf_max_depth, min_samples_leaf=3, random_state=config.seed, n_jobs=-1),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=config.hgb_iterations, max_depth=7, min_samples_leaf=20, random_state=config.seed),
    }
    report: dict[str, Any] = {"target": target, "split_rows": {s: int((frame.split == s).sum()) for s in ("train", "validation", "test")}, "models": {}}
    for name, model in models.items():
        model.fit(x_train, y_train)
        report["models"][name] = {split: _metrics(part[target], model.predict(part.loc[:, FEATURE_ALLOWLIST])) for split, part in (("train", train), ("validation", val), ("test", test))}
        if drift_rolls is not None:
            stable = test[~test.root_roll_id.isin(drift_rolls)]; drift = test[test.root_roll_id.isin(drift_rolls)]
            report["models"][name]["cohorts"] = {
                "stable": _metrics(stable[target], model.predict(stable.loc[:, FEATURE_ALLOWLIST])) if len(stable) else None,
                "drift": _metrics(drift[target], model.predict(drift.loc[:, FEATURE_ALLOWLIST])) if len(drift) else None,
            }
    base_rmse = report["models"]["baseline"]["test"]["rmse"]
    for name in ("random_forest", "hist_gradient_boosting"):
        report["models"][name]["test"]["baseline_rmse_improvement_pct"] = float(100 * (base_rmse - report["models"][name]["test"]["rmse"]) / base_rmse)
    report["champion"] = "random_forest"; report["challenger"] = "hist_gradient_boosting"
    bundle = {"schema_version": SCHEMA_VERSION, "target": target, "features": list(FEATURE_ALLOWLIST), "model": models["random_forest"], "model_kind": "random_forest"}
    return bundle, report


def train_all(dataset_dir: Path, artifact_root: Path, config: TrainingConfig = TrainingConfig()) -> dict[str, Any]:
    artifact_root.mkdir(parents=True, exist_ok=True); registry: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "bundle_version": "quality-v3.0", "targets": {}, "appearance_included": False}
    drift_path = dataset_dir.parent / "v3" / "drift_ground_truth.csv"
    drift_rolls = set(pd.read_csv(drift_path).root_roll_id.astype(str)) if drift_path.exists() else None
    for target in TARGETS:
        frame = pd.read_csv(dataset_dir / "projections" / f"{target}.csv")
        bundle, report = train_target(frame, target, config, drift_rolls=drift_rolls)
        target_dir = artifact_root / target; target_dir.mkdir(exist_ok=True)
        bundle_path = target_dir / "bundle.joblib"; joblib.dump(bundle, bundle_path)
        metrics_path = target_dir / "metrics.json"; metrics_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        train = frame[frame.split == "train"]
        support = {name: {"min": float(train[name].min()), "max": float(train[name].max())} for name in FEATURE_ALLOWLIST}
        manifest = {
            "schema_version": SCHEMA_VERSION, "bundle_version": "quality-v3.0", "target": target,
            "features": list(FEATURE_ALLOWLIST), "support_range_source": "train_manifest",
            "feature_support_ranges": support, "model_kind": "random_forest", "challenger": "hist_gradient_boosting",
            "seed": config.seed, "split_contract": {"train": 120, "validation": 40, "test": 40},
            "python": platform.python_version(), "scikit_learn": sklearn.__version__, "appearance_included": False,
            "bundle_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest(), "metrics_sha256": hashlib.sha256(metrics_path.read_bytes()).hexdigest(),
        }
        manifest_path = target_dir / "manifest.json"; manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        registry["targets"][target] = {"path": str(target_dir.relative_to(artifact_root)), "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "test_metrics": report["models"]["random_forest"]["test"]}
    registry_path = artifact_root / "registry.json"; registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    return registry


def load_trusted_bundle(bundle_path: Path, trusted_root: Path) -> dict[str, Any]:
    resolved = bundle_path.resolve(); root = trusted_root.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError("UNTRUSTED_MODEL_PATH")
    bundle = joblib.load(resolved)
    if bundle.get("schema_version") != SCHEMA_VERSION or bundle.get("target") not in TARGETS:
        raise ValueError("INCOMPATIBLE_MODEL_BUNDLE")
    return bundle


def predict_bundle(bundle: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    missing = set(bundle["features"]) - set(frame)
    if missing: raise ValueError("MISSING_MODEL_FEATURES:" + ",".join(sorted(missing)))
    return bundle["model"].predict(frame.loc[:, bundle["features"]])
