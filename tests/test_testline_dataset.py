from pathlib import Path

import pandas as pd
import pytest

from fccl_testline.dataset import FEATURE_ALLOWLIST, build_target_dataset, validate_allowlist, write_model_dataset
from fccl_testline.generation import GenerationConfig, TARGETS, generate_v3


def test_allowlist_has_process_features_and_no_leakage() -> None:
    validate_allowlist()
    assert "dry_thickness_mean_um" in FEATURE_ALLOWLIST
    assert "exhaust_airflow_actual_m3_h" in FEATURE_ALLOWLIST
    assert not set(TARGETS) & set(FEATURE_ALLOWLIST)
    with pytest.raises(ValueError, match="LEAKAGE_FEATURE"):
        validate_allowlist(FEATURE_ALLOWLIST + ("drift_scenario",))


def test_each_target_has_independent_projection_and_complete_rows(tmp_path: Path) -> None:
    canonical, _ = generate_v3(GenerationConfig(seed=123, rolls=4, segments_per_roll=10))
    source = tmp_path / "canonical.csv"; canonical.to_csv(source, index=False)
    manifest = write_model_dataset(source, tmp_path / "model")
    assert set(manifest["target_rows"]) == set(TARGETS)
    assert set(manifest["target_rows"].values()) == {40}
    for target in TARGETS:
        frame = pd.read_csv(tmp_path / "model/projections" / f"{target}.csv")
        assert list(frame.columns) == ["root_roll_id", "segment_id", "split", "quality_available_at", *FEATURE_ALLOWLIST, target]
        assert not frame.isna().any().any()
