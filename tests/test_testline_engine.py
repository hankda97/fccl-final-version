from pathlib import Path
import time

from fccl_testline.config import load_product_recipe
from fccl_testline.engine import TestlineEngine
from fccl_testline.generation import TARGETS


ROOT = Path(__file__).resolve().parents[1]


def defaults():
    return {k: v["default"] for k,v in load_product_recipe()["recipe"]["parameters"].items() if not v.get("advanced")}


def test_integrated_long_run_has_no_gaps_bounded_alarm_and_valid_checkpoint(tmp_path: Path) -> None:
    # Link immutable generated/model inputs while keeping runtime writes in tmp root.
    (tmp_path / "generated_data/v3").mkdir(parents=True); (tmp_path / "artifacts/synthetic_v3").mkdir(parents=True)
    import shutil
    shutil.copy(ROOT / "generated_data/v3/stable_reference.csv", tmp_path / "generated_data/v3/stable_reference.csv")
    shutil.copytree(ROOT / "artifacts/synthetic_v3/quality-v3.0", tmp_path / "artifacts/synthetic_v3/quality-v3.0")
    engine = TestlineEngine(project_root=tmp_path, run_id="RUN-LONG", seed=9001, scenario="compound_drift")
    begun = time.perf_counter(); engine.step(300); elapsed = time.perf_counter() - begun
    values = defaults(); values["curing_temp_c"] = 173; engine.apply_parameters(values); engine.step(20)
    manifest = engine.stop()
    assert engine.simulator.clock.sequence == 320
    assert sorted({r["tick_sequence"] for r in engine.tables["process_signals"]}) == list(range(1,321))
    assert len(engine.alarms.summary()) <= 5
    assert manifest["status"] == "completed" and manifest["checkpoint_sequence"] == 320
    assert engine.tables["quality_predictions"]
    assert {r["target"] for r in engine.tables["quality_predictions"]} == set(TARGETS)
    assert not any("appearance" in r["target"] or "yield" in r["target"] for r in engine.tables["quality_predictions"])
    assert elapsed < 15
