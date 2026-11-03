import numpy as np
import pytest

from fccl_testline.generation import SCENARIOS
from fccl_testline.simulation import TestlineSimulator


def run(scenario: str):
    sim = TestlineSimulator(seed=9001, scenario=scenario); sim.advance(100); return sim


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_scenarios_are_reproducible_and_truth_is_not_a_signal(scenario: str) -> None:
    first, second = run(scenario), run(scenario)
    assert first.snapshot_hash() == second.snapshot_hash()
    assert all("scenario" not in record and "drift" not in record for record in first.signals)


def test_each_drift_has_expected_statistical_direction() -> None:
    stable = run("stable"); tail = slice(-20, None)
    mean = lambda sim, field: float(np.mean([x[field] for x in sim.signals[tail]]))
    assert mean(run("thickness_increase"), "dry_thickness_mean_um") > mean(stable, "dry_thickness_mean_um") + 1
    assert mean(run("thickness_decrease"), "dry_thickness_mean_um") < mean(stable, "dry_thickness_mean_um") - 1
    assert mean(run("temperature_drop"), "curing_temp_c") < mean(stable, "curing_temp_c") - 3
    assert mean(run("airflow_decay"), "exhaust_airflow_m3_h") < mean(stable, "exhaust_airflow_m3_h") - 200
    assert mean(run("pressure_drift"), "lamination_pressure_mpa") < mean(stable, "lamination_pressure_mpa") - .15
    compound = run("compound_drift")
    assert mean(compound, "dry_thickness_mean_um") > mean(stable, "dry_thickness_mean_um") + .5
    assert mean(compound, "curing_temp_c") < mean(stable, "curing_temp_c") - 1.5
