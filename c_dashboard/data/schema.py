"""Explicit C view units and configurable source mappings, not A/B contracts."""

from dataclasses import dataclass, field
import json

TARGET_UNITS = {
    "peel_strength_n_mm": "N/mm", "dimensional_stability_md_pct": "%",
    "dimensional_stability_td_pct": "%", "heat_resistance_c": "°C",
    "appearance_ng": "0/1",
}
FEATURE_UNITS = {
    "ambient_temp_c": "°C", "ambient_rh_pct": "%RH", "line_speed_m_min": "m/min",
    "coating_temp_c": "°C", "coating_gap_um": "μm", "coating_viscosity_mpa_s": "mPa·s",
    "curing_temp_c": "°C", "curing_time_min": "min", "lamination_temp_c": "°C",
    "lamination_pressure_mpa": "MPa", "lamination_time_s": "s",
}
UNITS = {"length_m": "m", "position_m": "m", **FEATURE_UNITS, **TARGET_UNITS}
TEXT_FIELDS = (
    "timestamp", "available_at", "product_batch", "segment_id", "subgroup_id",
    "specimen_id", "product_id", "recipe_id",
)
KNOWN_FIELDS = (*TEXT_FIELDS, *UNITS)
CONTINUOUS_TARGETS = tuple(name for name in TARGET_UNITS if name != "appearance_ng")


@dataclass(frozen=True)
class ColumnMapping:
    column: str
    unit: str | None = None


@dataclass(frozen=True)
class MappingProfile:
    name: str = "C 標準欄名／單位"
    version: str = "c-view-v1"
    columns: dict[str, ColumnMapping] = field(default_factory=dict)
    timezone: str | None = None

    def entry(self, name: str) -> ColumnMapping:
        return self.columns.get(name, ColumnMapping(name, UNITS.get(name)))

    def signature(self) -> str:
        return json.dumps(
            {"name": self.name, "version": self.version, "timezone": self.timezone,
             "columns": {name: vars(value) for name, value in sorted(self.columns.items())}},
            sort_keys=True, ensure_ascii=False,
        )


def parse_mapping(text: str) -> MappingProfile:
    """Custom renamed numeric columns require explicit units, never guessing."""
    if not text.strip():
        return MappingProfile()
    value = json.loads(text)
    if not isinstance(value, dict) or set(value) - {"name", "version", "timezone", "columns"}:
        raise ValueError("映射須為含 name/version/timezone/columns 的 JSON 物件。")
    columns = value.get("columns", {})
    if not isinstance(columns, dict):
        raise ValueError("columns 須為物件：C欄名 → {column, unit}。")
    mapped = {}
    for target, config in columns.items():
        if target not in KNOWN_FIELDS or not isinstance(config, dict) or set(config) - {"column", "unit"}:
            raise ValueError(f"不支援的映射欄位或設定：{target}")
        source = config.get("column")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"{target} 需要明確來源欄名。")
        unit = config.get("unit", UNITS.get(target) if source == target else None)
        if target in UNITS and (not isinstance(unit, str) or not unit):
            raise ValueError(f"{target} 需要明確來源單位。")
        mapped[target] = ColumnMapping(source.strip(), unit)
    for name in ("name", "version"):
        if name in value and (not isinstance(value[name], str) or not value[name].strip()):
            raise ValueError(f"{name} 須為非空字串。")
    zone = value.get("timezone")
    if zone is not None:
        from zoneinfo import ZoneInfo
        if not isinstance(zone, str):
            raise ValueError("timezone 須為明確時區字串。")
        ZoneInfo(zone)
    return MappingProfile(value.get("name", "自訂映射"), value.get("version", "custom-v1"), mapped, zone)


def unit_conversion(field_name: str, source_unit: str) -> tuple[float, float]:
    target = UNITS[field_name]
    if source_unit == target:
        return 1.0, 0.0
    supported = {
        ("°C", "°F"): (5 / 9, -32 * 5 / 9),
        ("m", "mm"): (0.001, 0.0), ("m/min", "mm/s"): (0.06, 0.0),
        ("m/min", "m/s"): (60.0, 0.0), ("MPa", "kPa"): (0.001, 0.0),
        ("min", "s"): (1 / 60, 0.0), ("s", "min"): (60.0, 0.0),
        ("N/mm", "N/cm"): (0.1, 0.0), ("%", "fraction"): (100.0, 0.0),
        ("%RH", "fraction"): (100.0, 0.0), ("mPa·s", "cP"): (1.0, 0.0),
    }
    if (target, source_unit) not in supported:
        raise ValueError(f"{field_name}：不支援 {source_unit} → {target}，請確認單位。")
    return supported[(target, source_unit)]
