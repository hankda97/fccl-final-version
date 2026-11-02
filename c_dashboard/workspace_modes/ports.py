"""Optional C-internal simulation port. No data generation or storage I/O."""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import math
import pandas as pd

from c_dashboard.data.schema import FEATURE_UNITS
from c_dashboard.workspace_modes.types import ModeIssue

SCHEMA_VERSION = "c-simulation-envelope-v1"
CHANNELS = ("events", "process", "raw_signal", "processed_signal", "measurement", "truth", "prediction")


@dataclass(frozen=True)
class Capability:
    mode_id: str
    available: bool = False
    provider_version: str = "unavailable"
    schema_version: str = SCHEMA_VERSION
    actions: tuple = ()
    reason: str = "獨立模擬後端尚未交付；不產生或回寫資料。"


@dataclass(frozen=True)
class ActionResult:
    available: bool = False
    reason: str = "unavailable：此模擬動作尚未實作，沒有已執行事件。"


class SimulationBackendPort(Protocol):
    def describe(self) -> Capability: ...
    def start_run(self, context) -> ActionResult: ...
    def apply_confirmed_event(self, context, event) -> ActionResult: ...
    def advance(self, context, cutoff) -> ActionResult: ...
    def reset(self, context) -> ActionResult: ...


class UnavailableProvider:
    def __init__(self, mode):
        self.mode = mode

    def describe(self):
        return Capability(self.mode)

    def start_run(self, context):
        return ActionResult()

    def apply_confirmed_event(self, context, event):
        return ActionResult()

    def advance(self, context, cutoff):
        return ActionResult()

    def reset(self, context):
        return ActionResult()


class ProviderRegistry:
    def __init__(self):
        self._providers = {m: UnavailableProvider(m) for m in ("testline", "production")}

    def register(self, mode, provider):
        if mode not in self._providers or provider.describe().mode_id != mode:
            raise ValueError("PROVIDER_MODE_MISMATCH")
        if provider.describe().schema_version != SCHEMA_VERSION:
            raise ValueError("PROVIDER_SCHEMA_MISMATCH")
        self._providers[mode] = provider

    def get(self, mode):
        if mode not in self._providers:
            raise ValueError("UNKNOWN_SIMULATION_MODE")
        return self._providers[mode]


def aware(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("可靠且具時區的時間為必填")
    return stamp


def validate_payload(payload, context):
    """Reject the whole incompatible envelope; never fill missing measurements."""
    issues = []
    def problem(field, message, code="INVALID_ENVELOPE"):
        issues.append(ModeIssue(code, field, message))
    if not isinstance(payload, dict):
        return (ModeIssue("INVALID_ENVELOPE", "payload", "需提供明確 envelope"),)
    required = ("mode_id", "workspace_id", "run_id", "generation", "schema_version", "source_kind",
                "source_id", "simulator_id", "simulator_version", "seed", "config_version", "store_id")
    for field in required:
        if payload.get(field) is None or payload.get(field) == "":
            problem(field, "缺少必要來源或版本欄位")
    if context.mode_id not in ("testline", "production") or not context.run_id:
        problem("run_id", "必須先有獨立模擬 run")
    for field, expected in (("mode_id", context.mode_id), ("workspace_id", context.workspace_id),
                            ("run_id", context.run_id), ("generation", context.generation)):
        if payload.get(field) != expected:
            problem(field, "來源與目的工作區不匹配", "CONTEXT_MISMATCH")
    if payload.get("schema_version") != SCHEMA_VERSION:
        problem("schema_version", "未知 schema")
    if payload.get("source_kind") not in ("Synthetic", "Mock"):
        problem("source_kind", "模擬來源須明示 Synthetic／Mock")
    # Resolve the optional future store descriptor, but do not create/open it.
    destination = payload.get("destination")
    if destination:
        protected = (Path(__file__).resolve().parents[2] / "generated_data" / "v2").resolve()
        normalized = str(destination).replace("\\", "/")
        path = Path(normalized).resolve()
        if path == protected or protected in path.parents or "generated_data/v2" in normalized.casefold():
            problem("destination", "禁止將七表當輸出目的地", "PROTECTED_SOURCE")
    for channel in CHANNELS:
        records = payload.get(channel, [])
        if not isinstance(records, list):
            problem(channel, "通道需為紀錄清單")
            continue
        seen = set()
        for i, row in enumerate(records):
            field = f"{channel}[{i}]"
            if not isinstance(row, dict):
                problem(field, "紀錄型別無效")
                continue
            for name in ("record_id", "station", "product_batch", "root_roll_id", "timestamp",
                         "available_at", "material_md_start_m", "material_md_end_m"):
                if row.get(name) is None or row.get(name) == "":
                    problem(f"{field}.{name}", "缺少追溯欄位")
            if row.get("record_id") in seen:
                problem(field, "重複紀錄 ID；不可任意平均")
            seen.add(row.get("record_id"))
            try:
                start, end = float(row["material_md_start_m"]), float(row["material_md_end_m"])
                if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
                    raise ValueError()
            except (KeyError, TypeError, ValueError):
                problem(field, "MD 必須是有效半開區間")
            try:
                observed, available = aware(row["timestamp"]), aware(row["available_at"])
                if available < observed:
                    raise ValueError()
            except (KeyError, TypeError, ValueError):
                problem(field, "時間缺失、無時區或可得時間早於觀測")
            if channel == "events":
                if row.get("confirmed") is not True or not row.get("event_type") or not row.get("parameter_diff"):
                    problem(field, "事件須明示人工確認、類型與參數差異；候選不是已執行事件")
                values = row.get("parameter_diff", {})
            else:
                values = row.get("values", {})
            if not isinstance(values, dict) or not values:
                problem(field, "缺少明確數值")
                continue
            units, times, availability = row.get("units", {}), row.get("field_available_at", {}), row.get("availability", {})
            if not all(isinstance(v, dict) for v in (units, times, availability)):
                problem(field, "單位／可得性映射型別無效")
                continue
            for name, value in values.items():
                try:
                    if not math.isfinite(float(value)):
                        raise ValueError()
                except (ValueError, TypeError):
                    problem(f"{field}.{name}", "數值必須有限")
                if not units.get(name) or (channel == "process" and name in FEATURE_UNITS and units[name] != FEATURE_UNITS[name]):
                    problem(f"{field}.{name}", "單位缺失或與已知特徵不符")
                try:
                    if aware(times[name]) < aware(row["timestamp"]):
                        raise ValueError()
                except (KeyError, TypeError, ValueError):
                    problem(f"{field}.{name}", "缺少可信逐欄位可得時間")
                if availability.get(name) not in (True, False, 0, 1):
                    problem(f"{field}.{name}", "缺少逐欄位／目標 availability")
    return tuple(issues)


def visible_payload(payload, context, cutoff):
    issues = validate_payload(payload, context)
    if issues:
        return None, issues
    try:
        now = aware(cutoff)
    except (TypeError, ValueError):
        return None, (ModeIssue("INVALID_CUTOFF", "cutoff", "需提供可信截止時間"),)
    result = {key: deepcopy(payload[key]) for key in ("source_id", "source_kind", "simulator_id",
        "simulator_version", "config_version", "schema_version", "mode_id", "run_id")}
    for channel in CHANNELS:
        result[channel] = []
        if channel == "truth":
            continue  # Latent truth/noise causes never enter operational views.
        for row in payload.get(channel, []):
            if aware(row["available_at"]) > now:
                continue
            copy = {k: deepcopy(row[k]) for k in ("record_id", "station", "product_batch", "root_roll_id",
                    "timestamp", "available_at", "material_md_start_m", "material_md_end_m",
                    "confirmed", "event_type") if k in row}
            name = "parameter_diff" if channel == "events" else "values"
            copy[name] = {k: v for k, v in row[name].items()
                          if row["availability"][k] and aware(row["field_available_at"][k]) <= now}
            copy["units"] = {k: row["units"][k] for k in copy[name]}
            copy["field_available_at"] = {k: row["field_available_at"][k] for k in copy[name]}
            copy["availability"] = {k: True for k in copy[name]}
            if copy[name]:
                result[channel].append(copy)
    return result, ()


def model_features(visible, supported_features):
    """Only declared process features; never measurement/truth/prediction channels."""
    result = {}
    for row in visible.get("process", []):
        for name, value in row["values"].items():
            if name in FEATURE_UNITS and name in supported_features and row["units"][name] == FEATURE_UNITS[name]:
                result[name] = value
    return result


def predict_visible(adapter, visible, supported_features, sample_id):
    from c_dashboard.quality.prediction import predict_one
    return predict_one(adapter, sample_id, model_features(visible, supported_features))


def submit_payload(registry, mode, expected, payload, cutoff):
    from c_dashboard.workspace_modes.controller import accept_response, record_event
    workspace = registry.workspaces.get(mode)
    if workspace is None:
        return None, (ModeIssue("UNKNOWN_MODE", "mode_id", "未知模式"),)
    visible, issues = visible_payload(payload, workspace.mode_context, cutoff)
    if issues:
        registry.errors[mode].extend(issues)
        return None, issues
    if not accept_response(registry, mode, expected, expected.request_key):
        return None, (ModeIssue("STALE_CONTEXT", "context", "拒收過期回應"),)
    # Interface-only visible event index, not a persistent simulation store.
    for event in visible["events"]:
        record_event(registry, mode, visible["source_id"], event["event_type"], event["record_id"], event)
    return visible, ()
