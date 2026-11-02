"""Explicit state for an unconfigured formal model; separate from the C Mock."""

from collections.abc import Sequence

from c_dashboard.adapters.base import AdapterInfo, PredictionInput, PredictionResult


class UnavailableAdapter:
    def describe(self) -> AdapterInfo:
        return AdapterInfo(
            source="未接入",
            version=None,
            available=False,
            supports_shap=False,
            message="目前未設定正式模型 Adapter；C 專用示範 Mock 是獨立 Adapter。",
        )

    def predict(self, samples: Sequence[PredictionInput]) -> PredictionResult:
        return PredictionResult(info=self.describe())
