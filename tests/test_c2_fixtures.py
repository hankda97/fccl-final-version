"""C fixtures are repeatable, historical and independent of A's generator."""

from pathlib import Path
import runpy

import pandas as pd

FIXTURES = Path(__file__).parent / "fixtures" / "c_mock"
BUILDER = runpy.run_path(str(FIXTURES / "build.py"))


def test_checked_in_fixtures_are_reproducible(tmp_path):
    BUILDER["write_fixtures"](tmp_path)
    for path in tmp_path.iterdir():
        assert path.read_bytes() == (FIXTURES / path.name).read_bytes()


def test_history_is_prior_disjoint_and_has_independent_specimens():
    history = pd.read_csv(FIXTURES / "history.csv")
    normal = pd.read_csv(FIXTURES / "normal.csv")
    assert pd.to_datetime(history.available_at).max() < pd.to_datetime(normal.available_at).min()
    assert set(history.specimen_id).isdisjoint(normal.specimen_id)
    assert history.groupby("subgroup_id").size().eq(5).all()
    assert history.subgroup_id.nunique() == 25
    assert history.specimen_id.is_unique
    assert history.peel_strength_n_mm.nunique() > 25


def test_fixture_group_size_is_configurable_and_scenarios_have_known_values():
    variants = BUILDER["build_rows"](subgroup_size=3, history_groups=26)
    assert len(variants["history"]) == 78
    assert len(variants["normal"]) == 90
    trend = pd.DataFrame(variants["trend"]).groupby("subgroup_id").peel_strength_n_mm.mean()
    assert trend.loc["M-G003":"M-G008"].diff().dropna().gt(0).all()
    assert "heat_resistance_c" not in variants["partial_quality"][0]
    assert "subgroup_id" not in variants["ungrouped"][0]
