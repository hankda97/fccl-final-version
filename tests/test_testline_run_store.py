import csv
from pathlib import Path

import pytest

from fccl_testline.run_store import CSV_FILES, RunStore


def test_run_contract_is_isolated_and_hashes_five_csv(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runtime_data")
    manifest = store.create("RUN-001", seed=42, scenario="stable")
    run_dir = store.run_dir("RUN-001")
    assert set(p.name for p in run_dir.iterdir()) == {"manifest.json", *CSV_FILES.values()}
    assert manifest["training_eligible"] is False
    tables = {name: [{"run_id": "RUN-001", "tick_sequence": 1}] for name in CSV_FILES}
    checkpoint = store.checkpoint("RUN-001", tables, cutoff_sequence=1)
    assert checkpoint["checkpoint_sequence"] == 1
    completed = store.finalize("RUN-001")
    assert completed["status"] == "completed"
    assert all(len(meta["sha256"]) == 64 for meta in completed["files"].values())
    assert not (tmp_path / "raw data").exists()
    assert not (tmp_path / "generated_data").exists()
    assert not (tmp_path / "artifacts").exists()


def test_run_path_and_lifecycle_reject_escape_or_completed_write(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runtime_data")
    with pytest.raises(ValueError, match="INVALID_RUN_ID"):
        store.create("../raw data", seed=1, scenario="stable")
    store.create("RUN-002", seed=1, scenario="stable")
    store.checkpoint("RUN-002", {}, cutoff_sequence=0)
    store.finalize("RUN-002", status="interrupted")
    with pytest.raises(ValueError, match="RUN_NOT_WRITABLE"):
        store.checkpoint("RUN-002", {}, cutoff_sequence=1)


def test_gitignore_excludes_runtime_data() -> None:
    root = Path(__file__).resolve().parents[1]
    assert "runtime_data/" in (root / ".gitignore").read_text(encoding="utf-8")
