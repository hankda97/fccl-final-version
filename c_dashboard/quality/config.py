"""Versioned, explicitly illustrative C settings; never official quality policy."""

from dataclasses import dataclass

from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS

FEATURE_ALLOWLIST = tuple(FEATURE_UNITS)
PROCESS_FEATURES = tuple(name for name in FEATURE_ALLOWLIST if not name.startswith("ambient_"))
ENVIRONMENT_FEATURES = tuple(name for name in FEATURE_ALLOWLIST if name.startswith("ambient_"))
TARGET_NAMES = tuple(TARGET_UNITS)
TARGET_LABELS = {
    "peel_strength_n_mm": "抗剝離度",
    "dimensional_stability_md_pct": "尺寸安定性 MD",
    "dimensional_stability_td_pct": "尺寸安定性 TD",
    "heat_resistance_c": "耐熱度",
    "appearance_ng": "外觀 NG",
}


@dataclass(frozen=True)
class ParameterControl:
    parameter: str
    unit: str
    baseline_fraction: float
    step: float
    advanced: bool = False


# These relative ranges are a UI demonstration envelope, not equipment limits.
CONTROL_VERSION = "c-whatif-controls-v1"
PARAMETER_CONTROLS = {
    "line_speed_m_min": ParameterControl("line_speed_m_min", "m/min", 0.20, 0.10),
    "curing_temp_c": ParameterControl("curing_temp_c", "°C", 0.08, 1.0, True),
    "curing_time_min": ParameterControl("curing_time_min", "min", 0.20, 0.1, True),
    "lamination_temp_c": ParameterControl("lamination_temp_c", "°C", 0.06, 1.0, True),
    "lamination_pressure_mpa": ParameterControl("lamination_pressure_mpa", "MPa", 0.20, 0.05, True),
    "lamination_time_s": ParameterControl("lamination_time_s", "s", 0.20, 1.0, True),
}

FORMULA_VERSION = "c-formula-mock-v1"
RISK_POLICY_VERSION = "c-demo-risk-v1"
RECOMMENDATION_POLICY_VERSION = "c-demo-focus-candidate-v1"
DEMO_SOURCE = "C 確定性公式 Mock（示範用途）"

# A single explicitly configured focus target is only a test scenario. It does
# not define the team's official multi-target trade-off policy (TCP-004).
RECOMMENDATION_FOCUS_TARGET = "peel_strength_n_mm"
RECOMMENDATION_CANDIDATES = (("line_speed_m_min", -0.2),)
RECOMMENDATION_MIN_EFFECT = 1e-9


def parameter_bounds(parameter: str, baseline: float) -> tuple[float, float, float]:
    control = PARAMETER_CONTROLS[parameter]
    radius = max(abs(baseline) * control.baseline_fraction, control.step)
    low = max(control.step, baseline - radius) if parameter in {
        "line_speed_m_min", "curing_time_min", "lamination_pressure_mpa", "lamination_time_s"
    } else baseline - radius
    high = baseline + radius
    return float(low), float(high), float(control.step)
