import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from fccl_ml.artifacts import ArtifactValidationError, load_registry, load_target_bundle
from fccl_ml.config import FEATURES
from fccl_ml.training import (
    TrainingConfig, evaluate_model, model_version, predict_bundle, promotion_decision, train_target,
)


def _frame(classification=False):
    rows = []
    rng = np.random.default_rng(42)
    for split, count, offset in (("train", 80, 0), ("validation", 30, 80), ("test", 30, 110)):
        for index in range(count):
            values = {name: float(rng.normal()) for name in FEATURES}
            target = int(values["line_speed_m_min"] + values["ambient_rh_pct"] > 0) if classification else 2 * values["line_speed_m_min"] - values["ambient_rh_pct"]
            rows.append({"aligned_sample_id": f"A-{offset+index}", "root_roll_id": f"R-{split}-{index//5}", "dataset_split": split, "timestamp": f"2026-01-01T00:{(offset+index)%60:02d}:00+00:00", "process_phase": "stable" if index % 2 else "mild_drift", **values, "appearance_ng" if classification else "peel_strength_n_mm": target})
    return pd.DataFrame(rows)


def _manifest(profile="synthetic-ground-truth-v2", dataset_version="data-v1"):
    frame = _frame()
    return {
        "profile": profile, "dataset_version": dataset_version, "schema_version": "2.0.0",
        "feature_version": "fccl-process-features-v1", "spec_version": "SIM-2.0",
        "split_roll_ids": {split: sorted(frame.loc[frame.dataset_split.eq(split), "root_roll_id"].unique()) for split in ("train", "validation", "test")},
    }


def test_preprocessor_fits_only_train_statistics():
    frame = _frame()
    frame.loc[frame.dataset_split.ne("train"), "ambient_temp_c"] = 1e9
    result = train_target(frame, "peel_strength_n_mm", _manifest(), TrainingConfig(rf_estimators=10, hgb_max_iter=10))
    statistic = result["bundle"]["pipeline"].named_steps["imputer"].statistics_[list(FEATURES).index("ambient_temp_c")]
    assert statistic != 1e9
    assert statistic == pytest.approx(_frame().query("dataset_split == 'train'").ambient_temp_c.median())


@pytest.mark.parametrize(("target", "classification"), [("peel_strength_n_mm", False), ("appearance_ng", True)])
def test_baselines_rf_hgb_and_metrics_are_reproducible(target, classification, tmp_path):
    frame = _frame(classification)
    manifest = _manifest()
    manifest["split_roll_ids"] = {split: sorted(frame.loc[frame.dataset_split.eq(split), "root_roll_id"].unique()) for split in ("train", "validation", "test")}
    config = TrainingConfig(rf_estimators=12, hgb_max_iter=12)
    first = train_target(frame, target, manifest, config)
    second = train_target(frame, target, manifest, config)
    metric = "pr_auc" if classification else "mae"
    assert first["metrics"]["models"]["random_forest"]["test"][metric] == pytest.approx(
        second["metrics"]["models"]["random_forest"]["test"][metric], abs=1e-12
    )
    assert set(first["metrics"]["models"]) == ({"prevalence", "logistic", "random_forest", "hist_gradient_boosting"} if classification else {"mean", "linear", "random_forest", "hist_gradient_boosting"})
    prediction = first["bundle"]["pipeline"].predict(frame[list(FEATURES)].iloc[:5])
    bundle_path = tmp_path / "bundle.joblib"
    joblib.dump(first["bundle"], bundle_path)
    roundtrip = joblib.load(bundle_path)["pipeline"].predict(frame[list(FEATURES)].iloc[:5])
    np.testing.assert_allclose(prediction, roundtrip, rtol=0, atol=1e-12)
    assert len(prediction) == 5
    if classification:
        assert 1 in first["bundle"]["class_labels"]


def test_bundle_uses_declared_feature_order_and_preserves_batch_index():
    frame = _frame().set_index("aligned_sample_id", drop=False)
    result = train_target(frame.reset_index(drop=True), "peel_strength_n_mm", _manifest(), TrainingConfig(rf_estimators=8, hgb_max_iter=8))
    rows = frame.iloc[:7][list(reversed(FEATURES))]
    predicted = predict_bundle(result["bundle"], rows)
    assert predicted.index.equals(rows.index)
    assert len(predicted) == 7


def test_single_metric_never_auto_promotes_challenger():
    decision = promotion_decision({"mae": 2.0, "r2": 0.9}, {"mae": 1.0, "r2": -10.0}, False)
    assert decision["challenger_primary_better"] is True
    assert decision["promote"] is False


def test_model_version_changes_with_data_or_config():
    base = _manifest()
    assert model_version(base, TrainingConfig()) != model_version({**base, "dataset_version": "other"}, TrainingConfig())
    assert model_version(base, TrainingConfig()) != model_version(base, TrainingConfig(seed=7))


def test_classification_metric_reports_missing_class():
    frame = _frame(True)
    manifest = _manifest()
    manifest["split_roll_ids"] = {split: sorted(frame.loc[frame.dataset_split.eq(split), "root_roll_id"].unique()) for split in ("train", "validation", "test")}
    result = train_target(frame, "appearance_ng", manifest, TrainingConfig(rf_estimators=8, hgb_max_iter=8))
    X = frame.loc[frame.dataset_split.eq("test"), list(FEATURES)]
    y = pd.Series(np.zeros(len(X), dtype=int))
    metrics = evaluate_model(result["bundle"]["pipeline"], X, y, True)
    assert metrics == {"available": False, "reason": "CLASS_MISSING:[0]", "row_count": len(X)}


def test_loader_rejects_traversal_missing_manifest_and_hash_tamper(tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        load_registry(tmp_path, "../registry.json")
    with pytest.raises(FileNotFoundError):
        load_target_bundle(tmp_path, {"manifest": "missing.json", "manifest_sha256": "x"})
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="MANIFEST_HASH_MISMATCH"):
        load_target_bundle(tmp_path, {"manifest": "manifest.json", "manifest_sha256": "bad"})

