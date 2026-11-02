from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.adapters.unavailable import UnavailableAdapter
from c_dashboard.adapters.base import AdapterInfo, PredictionInput, PredictionRecord, PredictionResult
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.quality.config import FEATURE_ALLOWLIST, TARGET_NAMES
from c_dashboard.quality.controller import features_from_row
from c_dashboard.quality.prediction import predict_one


def _features():
    frame = load_mock_fixture("normal").frame
    return features_from_row(frame.iloc[0])


def test_formula_mock_is_repeatable_batch_order_independent_and_has_all_targets():
    adapter = DeterministicMockAdapter()
    features = _features()
    one, error = predict_one(adapter, "sample-1", features)
    assert error is None and set(one.targets) == set(TARGET_NAMES)
    assert one.targets["appearance_ng"] in (0, 1)
    assert one.appearance_ng_risk is not None and 0 <= one.appearance_ng_risk <= 1
    again, error = predict_one(adapter, "sample-1", features)
    assert error is None and again == one
    result = adapter.predict([
        __import__("c_dashboard.adapters.base", fromlist=["PredictionInput"]).PredictionInput("sample-2", features),
        __import__("c_dashboard.adapters.base", fromlist=["PredictionInput"]).PredictionInput("sample-1", features),
    ])
    assert [r.sample_id for r in result.records] == ["sample-2", "sample-1"]
    assert result.records[1] == one
    assert result.info.version and not result.info.supports_shap
    assert set(result.info.supports_targets) == set(TARGET_NAMES)
    assert set(one.target_units) == set(TARGET_NAMES)


def test_prediction_uses_only_allowlisted_process_environment_not_quality_truth():
    frame = load_mock_fixture("normal").frame
    row = frame.iloc[0]
    adapter = DeterministicMockAdapter()
    features = features_from_row(row)
    first, _ = predict_one(adapter, row.sample_id, features)
    altered = row.copy()
    for target in ("peel_strength_n_mm", "dimensional_stability_md_pct",
                   "dimensional_stability_td_pct", "heat_resistance_c", "appearance_ng"):
        if target in altered:
            altered[target] = 999999
    second, _ = predict_one(adapter, row.sample_id, features_from_row(altered))
    assert second == first
    assert set(features) == set(FEATURE_ALLOWLIST)


def test_missing_or_invalid_features_and_formal_unavailable_model_are_explicit():
    adapter = DeterministicMockAdapter()
    invalid, reason = predict_one(adapter, "sample", {"line_speed_m_min": float("nan")})
    assert invalid is None and "缺少必要特徵" in reason
    no_model, reason = predict_one(UnavailableAdapter(), "sample", _features())
    assert no_model is None and "正式模型" in reason


def test_adapter_output_missing_or_mismatched_units_is_rejected():
    class WrongUnitAdapter:
        def describe(self):
            return AdapterInfo("test", "test-v1", True, False, "test", TARGET_NAMES)

        def predict(self, samples):
            record = DeterministicMockAdapter().predict(samples).records[0]
            units = dict(record.target_units)
            units["peel_strength_n_mm"] = "MPa"
            return PredictionResult(self.describe(), (PredictionRecord(
                record.sample_id, record.targets, record.appearance_ng_risk,
                record.unavailable_targets, units,
            ),))

    result, reason = predict_one(WrongUnitAdapter(), "sample", _features())
    assert result is None and "目標單位缺失或不符" in reason


def test_adapter_can_report_target_specific_unavailable_outputs():
    class PartialAdapter:
        def describe(self):
            supported = ("peel_strength_n_mm",)
            return AdapterInfo("partial-test", "partial-v1", True, False,
                               "部分目標能力", supported)

        def predict(self, samples):
            records = tuple(PredictionRecord(
                sample.sample_id,
                {"peel_strength_n_mm": 1.2},
                None,
                {name: "此 Adapter 未支援" for name in TARGET_NAMES if name != "peel_strength_n_mm"},
                {"peel_strength_n_mm": "N/mm"},
            ) for sample in samples)
            return PredictionResult(self.describe(), records)

    record, reason = predict_one(PartialAdapter(), "sample", _features())
    assert reason is None
    assert record.targets == {"peel_strength_n_mm": 1.2}
    assert len(record.unavailable_targets) == len(TARGET_NAMES) - 1
