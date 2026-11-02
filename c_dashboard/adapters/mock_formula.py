"""Deterministic C-only formula adapter for UI and logic demonstration."""

from collections.abc import Sequence
import math

from c_dashboard.adapters.base import (
    AdapterInfo,
    PredictionInput,
    PredictionRecord,
    PredictionResult,
)
from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.quality.config import FEATURE_ALLOWLIST, FORMULA_VERSION, TARGET_NAMES


class DeterministicMockAdapter:
    """Illustrative equations only; not a trained model or process-causal model."""

    def describe(self) -> AdapterInfo:
        return AdapterInfo(
            source="C 確定性公式 Mock（示範用途）",
            version=FORMULA_VERSION,
            available=True,
            supports_shap=False,
            message="確定性公式示範；非正式模型、未校準 NG 機率或製程因果保證。",
            supports_targets=TARGET_NAMES,
        )

    def predict(self, samples: Sequence[PredictionInput]) -> PredictionResult:
        info = self.describe()
        records = []
        for sample in samples:
            missing = [name for name in FEATURE_ALLOWLIST if name not in sample.features]
            invalid = []
            features = {}
            for name in FEATURE_ALLOWLIST:
                if name not in sample.features:
                    continue
                try:
                    value = float(sample.features[name])
                except (TypeError, ValueError):
                    invalid.append(name)
                    continue
                if not math.isfinite(value):
                    invalid.append(name)
                    continue
                features[name] = value
            unavailable = {}
            if missing or invalid:
                parts = []
                if missing:
                    parts.append("缺少必要特徵：" + "、".join(missing))
                if invalid:
                    parts.append("特徵不是有限數值：" + "、".join(invalid))
                reason = "；".join(parts)
                unavailable = {target: reason for target in TARGET_NAMES}
                records.append(PredictionRecord(sample.sample_id, {}, None, unavailable))
                continue

            speed = features["line_speed_m_min"]
            humidity = features["ambient_rh_pct"]
            cure_temp = features["curing_temp_c"]
            cure_time = features["curing_time_min"]
            lam_temp = features["lamination_temp_c"]
            pressure = features["lamination_pressure_mpa"]
            lam_time = features["lamination_time_s"]

            # Coefficients are versioned for repeatable UI scenarios only.
            peel = (1.25 + 0.01 * (cure_temp - 170.0) + 0.012 * (cure_time - 15.0)
                    - 0.04 * (speed - 2.0) + 0.002 * (pressure - 2.0)
                    - 0.0005 * (humidity - 48.0))
            md = (-0.02 + 0.0003 * (lam_temp - 195.0) + 0.008 * (speed - 2.0)
                  - 0.001 * (pressure - 2.0) + 0.00005 * (lam_time - 60.0))
            td = (0.01 + 0.0002 * (lam_temp - 195.0) - 0.007 * (speed - 2.0)
                  - 0.0005 * (humidity - 48.0) + 0.00004 * (lam_time - 60.0))
            heat = (275.0 + 0.2 * (lam_temp - 195.0) + 0.4 * (cure_temp - 170.0)
                    + 0.2 * (cure_time - 15.0) + 0.02 * (lam_time - 60.0))
            risk = min(1.0, max(0.0, 0.1 + 0.1 * abs(speed - 2.0)
                                + 0.01 * abs(humidity - 48.0)
                                + 0.08 * abs(pressure - 2.0)))
            targets = {
                "peel_strength_n_mm": peel,
                "dimensional_stability_md_pct": md,
                "dimensional_stability_td_pct": td,
                "heat_resistance_c": heat,
                "appearance_ng": int(risk >= 0.5),
            }
            records.append(PredictionRecord(sample.sample_id, targets, risk, {}, TARGET_UNITS.copy()))
        return PredictionResult(info, tuple(records))
