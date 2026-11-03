from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from fccl_testline.generation import TARGETS
from fccl_testline.inference import QualityInferenceService


ROOT = Path(__file__).resolve().parents[1]


def test_inference_uses_only_quality_ready_segments_every_30_seconds_without_duplicates() -> None:
    candidates = pd.read_csv(ROOT / "generated_data/v3/canonical_v3.csv").head(2)
    now = datetime(2027,1,1,tzinfo=timezone.utc)
    candidates.loc[candidates.index[0], "quality_available_at"] = (now - timedelta(seconds=1)).isoformat()
    candidates.loc[candidates.index[1], "quality_available_at"] = (now + timedelta(seconds=1)).isoformat()
    service = QualityInferenceService(ROOT / "artifacts/synthetic_v3/quality-v3.0")
    assert service.update(candidates, now=now, simulated_seconds=0) == []
    records = service.update(candidates, now=now, simulated_seconds=30)
    assert len(records) == 4 and {r["target"] for r in records} == set(TARGETS)
    assert not any("appearance" in r["target"] or "yield" in r["target"] for r in records)
    assert service.update(candidates, now=now, simulated_seconds=60) == []
    later = service.update(candidates, now=now+timedelta(seconds=2), simulated_seconds=90)
    assert len(later) == 4 and {r["segment_id"] for r in later} == {str(candidates.iloc[1].segment_id)}


def test_parameter_event_can_trigger_new_ready_material_but_not_copy_old() -> None:
    candidate = pd.read_csv(ROOT / "generated_data/v3/canonical_v3.csv").head(1)
    now = datetime(2027,1,1,tzinfo=timezone.utc); candidate["quality_available_at"] = now.isoformat()
    service = QualityInferenceService(ROOT / "artifacts/synthetic_v3/quality-v3.0")
    assert len(service.update(candidate, now=now, simulated_seconds=1, force_for_parameter_event=True)) == 4
    assert service.update(candidate, now=now, simulated_seconds=2, force_for_parameter_event=True) == []
