from pathlib import Path

import pandas as pd
import pytest

from fccl_testline.dataset import write_model_dataset
from fccl_testline.generation import GenerationConfig, TARGETS, generate_v3
from fccl_testline.modeling import TrainingConfig, load_trusted_bundle, predict_bundle, train_all, train_target


def test_four_targets_compare_same_three_models_and_metrics(tmp_path: Path) -> None:
    frame, _ = generate_v3(GenerationConfig(seed=123, rolls=15, segments_per_roll=12))
    for target in TARGETS:
        projection = frame[["root_roll_id", "segment_id", "split", "quality_available_at", *bundle_features(), target]]
        bundle, report = train_target(projection, target, TrainingConfig(rf_estimators=8, rf_max_depth=5, hgb_iterations=15), drift_rolls=set(projection.root_roll_id.iloc[::2]))
        assert set(report["models"]) == {"baseline", "random_forest", "hist_gradient_boosting"}
        assert set(report["models"]["random_forest"]["test"]) >= {"mae", "rmse", "r2", "baseline_rmse_improvement_pct"}
        assert report["champion"] == "random_forest" and report["challenger"] == "hist_gradient_boosting"
        assert set(report["models"]["random_forest"]["cohorts"]) == {"stable", "drift"}


def bundle_features():
    from fccl_testline.dataset import FEATURE_ALLOWLIST
    return list(FEATURE_ALLOWLIST)


def test_bundle_registry_hash_support_and_trusted_loading(tmp_path: Path) -> None:
    canonical, _ = generate_v3(GenerationConfig(seed=456, rolls=15, segments_per_roll=10))
    source = tmp_path / "canonical.csv"; canonical.to_csv(source, index=False)
    dataset = tmp_path / "dataset"; write_model_dataset(source, dataset)
    artifacts = tmp_path / "artifacts"; registry = train_all(dataset, artifacts, TrainingConfig(rf_estimators=6, rf_max_depth=4, hgb_iterations=10))
    assert set(registry["targets"]) == set(TARGETS) and registry["appearance_included"] is False
    for target in TARGETS:
        target_dir = artifacts / target
        manifest = __import__("json").loads((target_dir / "manifest.json").read_text())
        assert manifest["support_range_source"] == "train_manifest"
        assert len(manifest["bundle_sha256"]) == 64
        bundle = load_trusted_bundle(target_dir / "bundle.joblib", artifacts)
        assert len(predict_bundle(bundle, canonical.head(2))) == 2
    with pytest.raises(ValueError, match="UNTRUSTED_MODEL_PATH"):
        load_trusted_bundle(artifacts / next(iter(TARGETS)) / "bundle.joblib", tmp_path / "other")
