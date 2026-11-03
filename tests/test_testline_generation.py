from pathlib import Path

import pandas as pd
import pytest

from fccl_testline.generation import DEMO_SEEDS, GenerationConfig, SCENARIOS, dataframe_sha256, generate_v3, stable_reference, write_v3


def test_small_generation_is_reproducible_and_has_v3_contract() -> None:
    cfg = GenerationConfig(seed=123, rolls=10, segments_per_roll=12)
    first, truth1 = generate_v3(cfg); second, truth2 = generate_v3(cfg)
    assert dataframe_sha256(first) == dataframe_sha256(second)
    assert dataframe_sha256(truth1) == dataframe_sha256(truth2)
    required = {"line_speed_setpoint_m_min", "line_speed_actual_m_min", "dry_thickness_1_um", "dry_thickness_5_um", "exhaust_airflow_actual_m3_h", "quality_available_at", "peel_label_available", "heat_resistance_c"}
    assert required <= set(first)
    assert (pd.to_datetime(first.coating_available_at) < pd.to_datetime(first.curing_available_at)).all()
    assert (pd.to_datetime(first.curing_available_at) < pd.to_datetime(first.lamination_available_at)).all()
    assert (pd.to_datetime(first.lamination_available_at) < pd.to_datetime(first.quality_available_at)).all()


def test_demo_seed_is_forbidden_and_reference_is_stable() -> None:
    with pytest.raises(ValueError, match="DEMO_SEED_FORBIDDEN"):
        generate_v3(GenerationConfig(seed=DEMO_SEEDS[0], rolls=1, segments_per_roll=1))
    ref = stable_reference(100)
    assert len(ref) == 100
    assert ref.dry_thickness_mean_um.std() < .5


def test_full_write_contract(tmp_path: Path) -> None:
    manifest = write_v3(tmp_path / "v3")
    assert manifest["rolls"] == 200 and manifest["segments"] == 20_000
    assert manifest["split_rolls"] == {"test": 40, "train": 120, "validation": 40}
    assert manifest["appearance_included"] is False
    assert manifest["runtime_data_included"] is False and manifest["v2_included"] is False
    assert set(manifest["files"]) == {"canonical_v3.csv", "drift_ground_truth.csv", "stable_reference.csv"}
    canonical = pd.read_csv(tmp_path / "v3" / "canonical_v3.csv")
    assert not canonical.groupby("root_roll_id").split.nunique().gt(1).any()
    truth = pd.read_csv(tmp_path / "v3" / "drift_ground_truth.csv")
    assert set(truth.scenario) == set(SCENARIOS) - {"stable"}
