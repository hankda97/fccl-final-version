from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import SCHEMA_VERSION


CSV_FILES = {
    "process_signals": "process_signals.csv",
    "material_segments": "material_segments.csv",
    "parameter_events": "parameter_events.csv",
    "spc_events": "spc_events.csv",
    "quality_predictions": "quality_predictions.csv",
}
RUN_STATES = frozenset(("running", "completed", "interrupted", "error"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class RunStore:
    runtime_root: Path

    @property
    def runs_root(self) -> Path:
        return self.runtime_root.resolve() / "testline_runs"

    def run_dir(self, run_id: str) -> Path:
        if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
            raise ValueError("INVALID_RUN_ID")
        path = (self.runs_root / run_id).resolve()
        if self.runs_root not in path.parents:
            raise ValueError("RUN_PATH_ESCAPE")
        return path

    def create(self, run_id: str, *, seed: int, scenario: str) -> dict[str, Any]:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=False)
        manifest = {
            "schema_version": SCHEMA_VERSION, "run_id": run_id,
            "product_id": "FCCL-DEMO-001", "recipe_id": "SIM-RECIPE-3.0",
            "seed": seed, "scenario": scenario, "status": "running",
            "started_at": utc_now(), "checkpoint_at": utc_now(),
            "ended_at": None, "synthetic_only": True,
            "training_eligible": False, "files": {},
        }
        for name in CSV_FILES.values():
            (path / name).touch()
        self._write_manifest(path, manifest)
        return manifest

    def checkpoint(self, run_id: str, tables: Mapping[str, Iterable[Mapping[str, Any]]], *, cutoff_sequence: int) -> dict[str, Any]:
        path = self.run_dir(run_id)
        manifest = self.load_manifest(run_id)
        if manifest["status"] != "running":
            raise ValueError("RUN_NOT_WRITABLE")
        metadata: dict[str, Any] = {}; prepared: list[tuple[Path, Path]] = []
        try:
            for table, filename in CSV_FILES.items():
                rows = [dict(row) for row in tables.get(table, [])]
                destination = path / filename; temp = destination.with_suffix(".checkpoint.tmp")
                fields = list(rows[0]) if rows else []
                with temp.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    if fields: writer.writeheader(); writer.writerows(rows)
                metadata[filename] = {"rows": len(rows), "sha256": sha256_file(temp)}
                prepared.append((temp, destination))
            for temp, destination in prepared: temp.replace(destination)
        except Exception:
            for temp, _ in prepared: temp.unlink(missing_ok=True)
            raise
        manifest.update({"checkpoint_at": utc_now(), "checkpoint_sequence": cutoff_sequence, "files": metadata})
        self._write_manifest(path, manifest)
        return manifest

    def mark_unfinished_interrupted(self) -> list[str]:
        changed: list[str] = []
        if not self.runs_root.exists(): return changed
        for path in self.runs_root.iterdir():
            if not path.is_dir() or not (path / "manifest.json").exists(): continue
            manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("status") == "running":
                manifest.update({"status": "interrupted", "ended_at": utc_now(), "read_only": True})
                self._write_manifest(path, manifest); changed.append(str(manifest["run_id"]))
        return changed

    def read_table(self, run_id: str, table: str) -> list[dict[str, str]]:
        if table not in CSV_FILES: raise ValueError("UNKNOWN_RUN_TABLE")
        with (self.run_dir(run_id) / CSV_FILES[table]).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def finalize(self, run_id: str, *, status: str = "completed") -> dict[str, Any]:
        if status not in {"completed", "interrupted", "error"}:
            raise ValueError("INVALID_FINAL_STATUS")
        path = self.run_dir(run_id); manifest = self.load_manifest(run_id)
        manifest.update({"status": status, "ended_at": utc_now()})
        for filename in CSV_FILES.values():
            file_meta = manifest["files"].setdefault(filename, {})
            file_meta["sha256"] = sha256_file(path / filename)
        self._write_manifest(path, manifest)
        return manifest

    def load_manifest(self, run_id: str) -> dict[str, Any]:
        return json.loads((self.run_dir(run_id) / "manifest.json").read_text(encoding="utf-8"))

    @staticmethod
    def _write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
        temp = path / "manifest.tmp"
        temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(path / "manifest.json")
