from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .dataset import FEATURE_ALLOWLIST
from .generation import TARGETS
from .modeling import load_trusted_bundle, predict_bundle
from .types import validate_model_support


class QualityInferenceService:
    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root.resolve(); self.bundles: dict[str, dict[str, Any]] = {}; self.manifests: dict[str, dict[str, Any]] = {}
        for target in TARGETS:
            target_dir = self.artifact_root / target
            self.bundles[target] = load_trusted_bundle(target_dir / "bundle.joblib", self.artifact_root)
            self.manifests[target] = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
        self.predicted_segments: set[str] = set(); self.last_update_seconds = 0

    def update(self, candidates: pd.DataFrame, *, now: datetime, simulated_seconds: int, force_for_parameter_event: bool = False) -> list[dict[str, Any]]:
        if simulated_seconds - self.last_update_seconds < 30 and not force_for_parameter_event: return []
        self.last_update_seconds = simulated_seconds
        if candidates.empty: return []
        available = candidates[pd.to_datetime(candidates.quality_available_at, utc=True) <= pd.Timestamp(now)]
        available = available[~available.segment_id.astype(str).isin(self.predicted_segments)]
        records: list[dict[str, Any]] = []
        for _, row in available.sort_values("quality_available_at").iterrows():
            segment_id = str(row.segment_id); input_frame = pd.DataFrame([{name: row[name] for name in FEATURE_ALLOWLIST}])
            for target in TARGETS:
                support = validate_model_support({name: float(row[name]) for name in FEATURE_ALLOWLIST}, self.manifests[target])
                records.append({"segment_id": segment_id, "target": target, "prediction": float(predict_bundle(self.bundles[target], input_frame)[0]), "model_version": self.manifests[target]["bundle_version"], "input_cutoff_at": row.quality_available_at, "support_status": "extrapolation" if "extrapolation" in support.values() else "in_range"})
            self.predicted_segments.add(segment_id)
        return records
