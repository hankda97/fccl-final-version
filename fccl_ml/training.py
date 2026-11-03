"""Target-specific baseline, RF Champion and HGB Challenger training."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import platform
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import FEATURES, FEATURE_UNITS, TARGETS, TARGET_UNITS
from .dataset import audit_feature_allowlist
from .paths import assert_output_separated
from .validation import file_sha256


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 42
    rf_estimators: int = 80
    rf_max_depth: int | None = 14
    hgb_max_iter: int = 120
    background_rows: int = 100
    threshold_grid_size: int = 19
    training_version: str = "fccl-training-v1"


@dataclass(frozen=True)
class TrainingResult:
    profile: str
    output_dir: Path
    registry: dict
    metrics: dict


def _pipeline(estimator) -> Pipeline:
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", estimator)])


def train_models(dataset_dir: Path | str, artifact_root: Path | str, config: TrainingConfig | None = None) -> TrainingResult:
    config = config or TrainingConfig()
    dataset_root = Path(dataset_dir).resolve()
    artifact_root = Path(artifact_root).resolve()
    assert_output_separated(artifact_root, (dataset_root.parents[1] / "v2",))
    dataset_manifest = json.loads((dataset_root / "manifest.json").read_text(encoding="utf-8"))
    profile = dataset_manifest["profile"]
    version = model_version(dataset_manifest, config)
    output = artifact_root / profile / version
    output.mkdir(parents=True, exist_ok=True)
    target_entries, all_metrics = {}, {}
    for target in TARGETS:
        frame = pd.read_csv(dataset_root / "projections" / f"{target}.csv")
        result = train_target(frame, target, dataset_manifest, config)
        target_dir = output / target
        target_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = target_dir / "bundle.joblib"
        background_path = target_dir / "background.csv"
        metrics_path = target_dir / "metrics.json"
        manifest_path = target_dir / "manifest.json"
        joblib.dump(result["bundle"], bundle_path, compress=3)
        result["background"].to_csv(background_path, index=False, lineterminator="\n")
        metrics_path.write_text(json.dumps(result["metrics"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "artifact_schema": "fccl-model-artifact-1.0",
            "manifest_id": f"{profile}:{version}:{target}",
            "model_version": version,
            "training_version": config.training_version,
            "pipeline_code_sha256": pipeline_code_hash(),
            "profile": profile,
            "data_classification": "synthetic_test_line_demonstration_only",
            "target": target,
            "task_type": "classification" if target == "appearance_ng" else "regression",
            "champion_type": type(result["bundle"]["pipeline"].named_steps["model"]).__name__,
            "challenger_type": result["challenger_type"],
            "feature_names": list(FEATURES),
            "feature_units": FEATURE_UNITS,
            "target_unit": TARGET_UNITS[target],
            "schema_version": dataset_manifest["schema_version"],
            "feature_version": dataset_manifest["feature_version"],
            "preprocessing_version": "median-imputer-v1",
            "label_version": profile,
            "spec_version": dataset_manifest.get("spec_version", "SIM-2.0"),
            "dataset_version": dataset_manifest["dataset_version"],
            "split_roll_ids": dataset_manifest["split_roll_ids"],
            "seed": config.seed,
            "hyperparameters": asdict(config),
            "class_labels": result["bundle"].get("class_labels", []),
            "ng_label": 1 if target == "appearance_ng" else None,
            "classification_threshold": result["bundle"].get("threshold"),
            "output_scale": "probability" if target == "appearance_ng" else "regression_output",
            "supported_ranges": result["bundle"]["supported_ranges"],
            "packages": package_versions(),
            "bundle_path": "bundle.joblib",
            "bundle_sha256": file_sha256(bundle_path),
            "background_path": "background.csv",
            "background_sha256": file_sha256(background_path),
            "metrics_path": "metrics.json",
            "metrics_sha256": file_sha256(metrics_path),
            "limitations": [
                "Synthetic test-line model only; not validated on real production data.",
                "What-if output is associative model inference, not a causal process guarantee.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        target_entries[target] = {
            "status": "available",
            "manifest": str(manifest_path.relative_to(artifact_root / profile)).replace("\\", "/"),
            "manifest_sha256": file_sha256(manifest_path),
        }
        all_metrics[target] = result["metrics"]
    registry = {
        "registry_schema": "fccl-model-registry-1.0",
        "profile": profile,
        "active_model_version": version,
        "dataset_version": dataset_manifest["dataset_version"],
        "source": "Synthetic model artifacts",
        "targets": target_entries,
        "rollback": {"strategy": "select_prior_verified_registry_or_explicit_mock", "automatic_mock_fallback": False},
    }
    profile_root = artifact_root / profile
    registry_path = profile_root / "registry.json"
    metrics_path = output / "metrics.json"
    metrics_path.write_text(json.dumps(all_metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(output / "MODEL_REPORT.md", profile, version, all_metrics)
    return TrainingResult(profile, output, registry, all_metrics)


def train_target(frame: pd.DataFrame, target: str, dataset_manifest: dict, config: TrainingConfig) -> dict:
    audit_feature_allowlist(FEATURES)
    required = {"aligned_sample_id", "root_roll_id", "dataset_split", "timestamp", "process_phase", *FEATURES, target}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Projection missing columns: {sorted(missing)}")
    split_rolls = dataset_manifest["split_roll_ids"]
    for split, expected_rolls in split_rolls.items():
        actual = set(frame.loc[frame.dataset_split.eq(split), "root_roll_id"])
        if not actual.issubset(set(expected_rolls)):
            raise ValueError(f"ROLL_CROSSES_SPLIT: {split}")
    train = frame.loc[frame.dataset_split.eq("train")].copy()
    validation = frame.loc[frame.dataset_split.eq("validation")].copy()
    test = frame.loc[frame.dataset_split.eq("test")].copy()
    if min(len(train), len(validation), len(test)) == 0:
        raise ValueError("Every target requires non-empty train/validation/test projections")
    X_train, y_train = train[list(FEATURES)], train[target]
    classification = target == "appearance_ng"
    if classification and set(pd.unique(y_train.astype(int))) != {0, 1}:
        raise ValueError("CLASS_MISSING: appearance train split requires labels 0 and 1")
    baseline_estimators = (
        {"prevalence": DummyClassifier(strategy="prior"), "logistic": LogisticRegression(max_iter=1000, random_state=config.seed)}
        if classification else {"mean": DummyRegressor(strategy="mean"), "linear": LinearRegression()}
    )
    rf_candidates = []
    for name, max_depth, min_leaf in (("depth_limited", config.rf_max_depth, 1), ("regularized", None, 3)):
        estimator = (
            RandomForestClassifier(n_estimators=config.rf_estimators, max_depth=max_depth, min_samples_leaf=min_leaf, random_state=config.seed, n_jobs=-1, class_weight="balanced_subsample")
            if classification else RandomForestRegressor(n_estimators=config.rf_estimators, max_depth=max_depth, min_samples_leaf=min_leaf, random_state=config.seed, n_jobs=-1)
        )
        candidate = _pipeline(estimator)
        candidate.fit(X_train, y_train.astype(int) if classification else y_train)
        candidate_metrics = evaluate_model(candidate, validation[list(FEATURES)], validation[target], classification, 0.5)
        score = candidate_metrics.get("pr_auc", -np.inf) if classification else -candidate_metrics.get("mae", np.inf)
        rf_candidates.append((score, name, candidate, {"max_depth": max_depth, "min_samples_leaf": min_leaf}, candidate_metrics))
    _, selected_rf_name, selected_rf, selected_rf_params, _ = max(rf_candidates, key=lambda item: item[0])
    hgb = (
        HistGradientBoostingClassifier(max_iter=config.hgb_max_iter, random_state=config.seed)
        if classification else HistGradientBoostingRegressor(max_iter=config.hgb_max_iter, random_state=config.seed)
    )
    models = {name: _pipeline(estimator) for name, estimator in baseline_estimators.items()}
    models.update({"random_forest": selected_rf, "hist_gradient_boosting": _pipeline(hgb)})
    for name, pipeline in models.items():
        if name == "random_forest":
            continue
        pipeline.fit(X_train, y_train.astype(int) if classification else y_train)
    threshold = select_threshold(models["random_forest"], validation[list(FEATURES)], validation[target], config.threshold_grid_size) if classification else None
    metrics = {
        "target": target,
        "task_type": "classification" if classification else "regression",
        "row_counts": {split: int(frame.dataset_split.eq(split).sum()) for split in ("train", "validation", "test")},
        "models": {},
        "comparison": {},
        "selection": {
            "random_forest": {
                "selected": selected_rf_name,
                "selected_params": selected_rf_params,
                "validation_candidates": {
                    name: {"params": params, "metrics": candidate_metrics}
                    for _, name, _, params, candidate_metrics in rf_candidates
                },
            }
        },
    }
    for name, pipeline in models.items():
        model_metrics = {}
        for split, subset in (("validation", validation), ("test", test)):
            model_metrics[split] = evaluate_model(pipeline, subset[list(FEATURES)], subset[target], classification, threshold if name == "random_forest" else 0.5)
            model_metrics[f"{split}_by_phase"] = {
                phase: evaluate_model(pipeline, group[list(FEATURES)], group[target], classification, threshold if name == "random_forest" else 0.5)
                for phase, group in subset.groupby("process_phase")
            }
        metrics["models"][name] = model_metrics
    baseline_name = "logistic" if classification else "linear"
    primary = "pr_auc" if classification else "mae"
    metrics["relative_to_baseline"] = {}
    for split in ("validation", "test"):
        baseline_value = metrics["models"][baseline_name][split].get(primary)
        metrics["relative_to_baseline"][split] = {}
        for candidate in ("random_forest", "hist_gradient_boosting"):
            candidate_value = metrics["models"][candidate][split].get(primary)
            if baseline_value is None or candidate_value is None:
                improvement = None
            elif classification:
                improvement = float(candidate_value - baseline_value)
            else:
                improvement = float(baseline_value - candidate_value)
            metrics["relative_to_baseline"][split][candidate] = {"metric": primary, "absolute_improvement": improvement}
    metrics["comparison"] = promotion_decision(metrics["models"]["random_forest"]["validation"], metrics["models"]["hist_gradient_boosting"]["validation"], classification)
    pipeline = models["random_forest"]
    classes = [int(v) for v in pipeline.named_steps["model"].classes_] if classification else []
    if classification and 1 not in classes:
        raise ValueError("CLASS_MISSING: Random Forest classes_ lacks NG label 1")
    supported_ranges = {name: {"min": float(X_train[name].min()), "max": float(X_train[name].max())} for name in FEATURES}
    rng = np.random.default_rng(config.seed)
    count = min(config.background_rows, len(train))
    indices = np.sort(rng.choice(len(train), size=count, replace=False))
    background = train.iloc[indices][["aligned_sample_id", *FEATURES]].copy()
    bundle = {
        "pipeline": pipeline,
        "target": target,
        "feature_names": tuple(FEATURES),
        "target_unit": TARGET_UNITS[target],
        "profile": dataset_manifest["profile"],
        "dataset_version": dataset_manifest["dataset_version"],
        "schema_version": dataset_manifest["schema_version"],
        "feature_version": dataset_manifest["feature_version"],
        "spec_version": dataset_manifest.get("spec_version", "SIM-2.0"),
        "supported_ranges": supported_ranges,
        "class_labels": classes,
        "threshold": threshold,
    }
    return {"bundle": bundle, "background": background, "metrics": metrics, "challenger_type": type(hgb).__name__}


def predict_bundle(bundle: dict, rows: pd.DataFrame) -> pd.Series:
    feature_names = tuple(bundle["feature_names"])
    missing = [name for name in feature_names if name not in rows]
    if missing:
        raise ValueError("MISSING_MODEL_FEATURES:" + ",".join(missing))
    matrix = rows.loc[:, feature_names]
    pipeline = bundle["pipeline"]
    if bundle["target"] == "appearance_ng":
        classes = list(pipeline.named_steps["model"].classes_)
        if 1 not in classes:
            raise ValueError("MODEL_CLASS_1_MISSING")
        values = pipeline.predict_proba(matrix)[:, classes.index(1)]
    else:
        values = pipeline.predict(matrix)
    return pd.Series(values, index=rows.index, name=bundle["target"])


def evaluate_model(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, classification: bool, threshold: float = 0.5) -> dict:
    if classification:
        labels = sorted(int(value) for value in pd.unique(y.dropna()))
        if labels != [0, 1]:
            return {"available": False, "reason": f"CLASS_MISSING:{labels}", "row_count": int(len(y))}
        classes = list(pipeline.named_steps["model"].classes_)
        if 1 not in classes:
            return {"available": False, "reason": "MODEL_CLASS_1_MISSING", "row_count": int(len(y))}
        probabilities = pipeline.predict_proba(X)[:, classes.index(1)]
        predicted = (probabilities >= threshold).astype(int)
        return {
            "available": True,
            "row_count": int(len(y)),
            "class_ratio": {str(label): float((y.astype(int) == label).mean()) for label in (0, 1)},
            "pr_auc": float(average_precision_score(y, probabilities)),
            "precision": float(precision_score(y, predicted, zero_division=0)),
            "recall": float(recall_score(y, predicted, zero_division=0)),
            "f1": float(f1_score(y, predicted, zero_division=0)),
            "confusion_matrix": confusion_matrix(y, predicted, labels=[0, 1]).tolist(),
            "brier_score": float(brier_score_loss(y, probabilities)),
            "threshold": float(threshold),
        }
    predicted = pipeline.predict(X)
    return {
        "available": True,
        "row_count": int(len(y)),
        "mae": float(mean_absolute_error(y, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(y, predicted))),
        "r2": float(r2_score(y, predicted)),
    }


def select_threshold(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, grid_size: int) -> float:
    classes = list(pipeline.named_steps["model"].classes_)
    probabilities = pipeline.predict_proba(X)[:, classes.index(1)]
    candidates = np.linspace(0.05, 0.95, grid_size)
    scored = [(f1_score(y, probabilities >= threshold, zero_division=0), float(threshold)) for threshold in candidates]
    return max(scored, key=lambda pair: (pair[0], -abs(pair[1] - 0.5)))[1]


def promotion_decision(champion: dict, challenger: dict, classification: bool) -> dict:
    primary = "pr_auc" if classification else "mae"
    challenger_better = challenger.get(primary, -np.inf if classification else np.inf) > champion.get(primary, -np.inf) if classification else challenger.get(primary, np.inf) < champion.get(primary, np.inf)
    return {
        "current_champion": "random_forest",
        "challenger": "hist_gradient_boosting",
        "promote": False,
        "primary_metric": primary,
        "challenger_primary_better": bool(challenger_better),
        "reason": "Initial RF remains Champion; promotion requires all pre-registered quality, drift, latency and compatibility gates, not one metric.",
    }


def model_version(dataset_manifest: dict, config: TrainingConfig) -> str:
    identity = {"dataset_version": dataset_manifest["dataset_version"], "profile": dataset_manifest["profile"], "config": asdict(config), "features": FEATURES, "pipeline_code_sha256": pipeline_code_hash()}
    return "model-" + sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()[:16]


def pipeline_code_hash() -> str:
    digest = sha256()
    root = Path(__file__).resolve().parent
    for name in ("training.py", "dataset.py", "artifacts.py", "config.py"):
        digest.update(name.encode())
        digest.update((root / name).read_bytes())
    return digest.hexdigest()


def package_versions() -> dict[str, str]:
    values = {"python": platform.python_version()}
    for package in ("numpy", "pandas", "scikit-learn", "joblib", "shap"):
        values[package] = importlib.metadata.version(package)
    return values


def _write_report(path: Path, profile: str, version: str, metrics: dict) -> None:
    lines = [f"# Model Report: {profile}", "", f"Model version: `{version}`", "", "> Synthetic test-line demonstration only. Not real production performance or causal evidence.", ""]
    for target, result in metrics.items():
        test = result["models"]["random_forest"]["test"]
        lines.extend([f"## {target}", "", f"- RF test metrics: `{json.dumps(test, ensure_ascii=False, sort_keys=True)}`", f"- Promotion: `{result['comparison']['reason']}`", ""])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

