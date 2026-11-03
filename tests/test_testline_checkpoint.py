from pathlib import Path

import pytest

from fccl_testline.run_store import CSV_FILES, RunStore


def rows(n: int):
    return {name: [{"run_id": "RUN-CP", "tick_sequence": i} for i in range(1, n + 1)] for name in CSV_FILES}


def test_checkpoint_rewrite_is_idempotent_and_sixty_second_cutoff(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runtime_data"); store.create("RUN-CP", seed=42, scenario="stable")
    first = store.checkpoint("RUN-CP", rows(12), cutoff_sequence=12)
    second = store.checkpoint("RUN-CP", rows(12), cutoff_sequence=12)
    assert first["files"] == second["files"]
    assert all(len(store.read_table("RUN-CP", name)) == 12 for name in CSV_FILES)
    assert second["checkpoint_sequence"] * 5 == 60


def test_failed_checkpoint_never_advances_manifest(monkeypatch, tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runtime_data"); store.create("RUN-CP", seed=42, scenario="stable")
    store.checkpoint("RUN-CP", rows(1), cutoff_sequence=1); before = store.load_manifest("RUN-CP")
    original = Path.open; calls = {"count": 0}
    def failing_open(self, *args, **kwargs):
        if self.name.endswith(".checkpoint.tmp"):
            calls["count"] += 1
            if calls["count"] == 3: raise OSError("injected")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="injected"): store.checkpoint("RUN-CP", rows(2), cutoff_sequence=2)
    assert store.load_manifest("RUN-CP")["checkpoint_sequence"] == before["checkpoint_sequence"]
    assert store.load_manifest("RUN-CP")["status"] == "running"


def test_restart_marks_running_interrupted_read_only_and_cannot_resume(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runtime_data"); store.create("RUN-CP", seed=42, scenario="stable")
    store.checkpoint("RUN-CP", rows(1), cutoff_sequence=1)
    assert store.mark_unfinished_interrupted() == ["RUN-CP"]
    manifest = store.load_manifest("RUN-CP")
    assert manifest["status"] == "interrupted" and manifest["read_only"] is True
    with pytest.raises(ValueError, match="RUN_NOT_WRITABLE"): store.checkpoint("RUN-CP", rows(2), cutoff_sequence=2)
