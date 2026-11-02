"""Versioned descriptive chart settings, not plant sampling requirements."""

from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS
from c_dashboard.quality.config import TARGET_LABELS

VISUALIZATION_VERSION = "c-visualization-v1"
EXPLANATION_SCHEMA_VERSION = "c-explanation-v1"
MINIMUM_PAIRS = 3
SHAP_KINDS = ("SHAP Summary Plot", "SHAP Dependence Plot")
TEST_NOTICE = "介面測試資料，非真正 SHAP"
FEATURE_LABELS = {
    "ambient_temp_c": "環境溫度", "ambient_rh_pct": "環境相對濕度",
    "line_speed_m_min": "線速", "coating_temp_c": "塗佈溫度",
    "coating_gap_um": "塗佈間隙", "coating_viscosity_mpa_s": "塗液黏度",
    "curing_temp_c": "熟化溫度", "curing_time_min": "熟化時間",
    "lamination_temp_c": "壓合溫度", "lamination_pressure_mpa": "壓合壓力",
    "lamination_time_s": "壓合時間",
}


def label(name: str) -> str:
    unit = {**FEATURE_UNITS, **TARGET_UNITS}.get(name)
    text = {**FEATURE_LABELS, **TARGET_LABELS}.get(name, name)
    return f"{text} [{unit}]" if unit else text
