from pathlib import Path

import pytest

from fccl_ml.config import PipelineConfig
from fccl_ml.paths import UnsafePathError, assert_output_separated, resolve_within


def test_default_paths_keep_sources_outputs_and_artifacts_separate(tmp_path: Path):
    config = PipelineConfig.default(tmp_path)
    assert config.source_dir == tmp_path / "generated_data" / "v2"
    assert config.dataset_dir == tmp_path / "generated_data" / "model_dataset_v2"
    assert config.artifact_dir == tmp_path / "artifacts" / "synthetic_v2"
    assert_output_separated(config.dataset_dir, (config.source_dir, tmp_path / "raw data"))
    assert_output_separated(config.artifact_dir, (config.source_dir, tmp_path / "raw data"))


def test_trusted_path_rejects_traversal(tmp_path: Path):
    trusted = tmp_path / "artifacts"
    trusted.mkdir()
    with pytest.raises(UnsafePathError):
        resolve_within("../outside.joblib", trusted)


@pytest.mark.parametrize("source", ("generated_data/v2", "raw data"))
def test_output_cannot_overlap_readonly_sources(tmp_path: Path, source: str):
    with pytest.raises(UnsafePathError):
        assert_output_separated(tmp_path / source / "output", (tmp_path / source,))

