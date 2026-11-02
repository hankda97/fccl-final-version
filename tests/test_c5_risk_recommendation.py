from c_dashboard.adapters.base import PredictionRecord
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.quality.assessment import assess_record
from c_dashboard.quality.controller import ensure_what_if_selection, evaluate_what_if
from c_dashboard.quality.recommend import choose_recommendation
from c_dashboard.data.session import commit_dataset, selected_rows
from c_dashboard.state import ensure_workspace


def test_configured_quality_limit_and_appearance_risk_create_distinct_deterministic_alarms():
    record = PredictionRecord("S-1", {
        "peel_strength_n_mm": 0.5, "dimensional_stability_md_pct": 0.0,
        "dimensional_stability_td_pct": 0.0, "heat_resistance_c": 275,
        "appearance_ng": 1,
    }, appearance_ng_risk=0.8)
    settings = load_mock_fixture("normal").settings
    kwargs = dict(source_id="source", sample_id="S-1", batch_id="B-1", segment_id="M-1",
                  timestamp="2026-11-01T08:00:00+08:00", scenario="current",
                  quality_specs=settings["quality_specs"],
                  appearance_threshold=settings["appearance_ng_risk_threshold"], model_version="v1")
    alarms, _ = assess_record(record, **kwargs)
    repeat, _ = assess_record(record, **kwargs)
    assert {a.target for a in alarms} == {"peel_strength_n_mm", "appearance_ng"}
    assert alarms == repeat and len({a.alarm_id for a in alarms}) == 2


def test_missing_spec_or_features_are_indeterminate_not_silent_normal():
    record = PredictionRecord("S-1", {"peel_strength_n_mm": 1.2}, appearance_ng_risk=None,
                              unavailable_targets={"heat_resistance_c": "feature missing"})
    alarms, unknown = assess_record(record, source_id="s", sample_id="S-1", batch_id="B",
                                    segment_id="M", timestamp="t", scenario="current",
                                    quality_specs={}, appearance_threshold=None, model_version="v1")
    assert not alarms
    assert any("沒有已配置" in reason for reason in unknown)
    assert any("無法預測" in reason for reason in unknown)
    assert any("不推定為 0" in reason for reason in unknown)


def test_configured_line_speed_minus_point_two_is_only_demo_candidate_and_no_candidate_status():
    workspace = ensure_workspace({})
    assert commit_dataset(workspace, load_mock_fixture("normal"))
    rows = selected_rows(workspace)
    options = ensure_what_if_selection(workspace, rows)
    from c_dashboard.quality.controller import snapshot_features
    baseline = snapshot_features(options[-1])
    adapter = DeterministicMockAdapter()
    before = adapter.predict([__import__("c_dashboard.adapters.base", fromlist=["PredictionInput"]).PredictionInput(
        options[-1].sample_id, baseline)]).records[0]
    settings = workspace.data.dataset.settings["quality_specs"]
    candidate = choose_recommendation(options[-1], baseline, before, adapter, settings,
                                     candidates=(("line_speed_m_min", -0.2),))
    assert candidate.status == "suggested"
    assert candidate.parameter == "line_speed_m_min" and candidate.delta == -0.2
    assert candidate.unit == "m/min"
    assert "不是正式多目標" in candidate.reason
    none = choose_recommendation(options[-1], baseline, before, adapter, settings,
                                 candidates=(("line_speed_m_min", 0.2),))
    assert none.status == "none"
    missing = choose_recommendation(options[-1], baseline, before, adapter, None)
    assert missing.status == "unavailable"


def test_changed_demo_quality_configuration_invalidates_cached_recommendation():
    workspace = ensure_workspace({})
    assert commit_dataset(workspace, load_mock_fixture("normal"))
    ensure_what_if_selection(workspace, selected_rows(workspace))
    adapter = DeterministicMockAdapter()
    _, recommendation = evaluate_what_if(workspace, adapter)
    assert recommendation.status == "suggested"
    workspace.data.dataset.settings["quality_specs"].pop("peel_strength_n_mm")
    _, recommendation = evaluate_what_if(workspace, adapter)
    assert recommendation.status == "unavailable"
    assert "缺少此測試情境" in recommendation.reason
