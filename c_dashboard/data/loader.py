"""Strict CSV parsing and per-function input eligibility, without imputation."""

import csv
from dataclasses import dataclass, field
from hashlib import sha256
from io import StringIO

import numpy as np
import pandas as pd

from c_dashboard.data.schema import (
    CONTINUOUS_TARGETS, FEATURE_UNITS, KNOWN_FIELDS, MappingProfile, TARGET_UNITS,
    UNITS, unit_conversion,
)


@dataclass(frozen=True)
class DataIssue:
    code: str
    field: str | None
    row: int | None
    message: str
    severity: str = "warning"


@dataclass
class LoadResult:
    source_name: str
    source_kind: str
    profile: MappingProfile
    source_id: str
    content: bytes
    frame: pd.DataFrame = field(default_factory=pd.DataFrame)
    raw_frame: pd.DataFrame = field(default_factory=pd.DataFrame)
    issues: list[DataIssue] = field(default_factory=list)
    parsed: bool = False
    accepted: bool = False
    metadata: dict = field(default_factory=dict)
    settings: dict = field(default_factory=dict)


def _timestamp(value: str, zone: str | None) -> pd.Timestamp:
    result = pd.Timestamp(value)
    if pd.isna(result):
        raise ValueError("empty timestamp")
    if result.tzinfo is None:
        if zone is None:
            raise ValueError("timestamp has no timezone; configure timezone explicitly")
        result = result.tz_localize(zone, ambiguous="raise", nonexistent="raise")
    return result.tz_convert("Asia/Taipei")


def load_csv(content: bytes, source_name: str, *, source_kind="upload", profile=None) -> LoadResult:
    profile = profile or MappingProfile()
    fingerprint = sha256(content + (source_kind + source_name + profile.signature()).encode()).hexdigest()
    result = LoadResult(source_name, source_kind, profile, fingerprint, content)

    def issue(code, field_name, row, message, severity="warning"):
        result.issues.append(DataIssue(code, field_name, row, message, severity))

    if not source_name.lower().endswith(".csv"):
        issue("FILE_TYPE", None, None, "請提供 .csv 檔案。", "error")
        return result
    try:
        text = content.decode("utf-8-sig")
        if not text.strip() or "\x00" in text:
            raise ValueError("檔案為空或含不支援的 NUL 字元。")
        reader = csv.reader(StringIO(text), strict=True)
        original_header = next(reader)
        header = [name.strip() for name in original_header]
        if not header or any(not name for name in header) or len(set(header)) != len(header):
            raise ValueError("表頭為空或包含重複欄名。")
        if header != original_header:
            issue("HEADER_NORMALIZED", None, None, "表頭前後空白已明確正規化。", "info")
        rows, source_rows = [], []
        while True:
            line = reader.line_num + 1
            try:
                values = next(reader)
            except StopIteration:
                break
            if not values:
                continue
            if len(values) != len(header):
                raise ValueError(f"來源列 {line} 的欄位數與表頭不一致。")
            rows.append(values)
            source_rows.append(line)
        if not rows:
            raise ValueError("CSV 只有表頭，沒有資料列。")
    except (UnicodeDecodeError, csv.Error, ValueError, StopIteration) as exc:
        issue("CSV_PARSE", None, None, f"無法解析 CSV：{exc}", "error")
        return result

    raw = pd.DataFrame(rows, columns=header)
    result.raw_frame = raw.copy()
    result.raw_frame.index = pd.Index(source_rows, name="source_row")
    frame = pd.DataFrame(index=raw.index)
    frame["source_row"] = source_rows
    used_sources = set()
    for name in KNOWN_FIELDS:
        mapping = profile.entry(name)
        if mapping.column not in raw:
            continue
        if mapping.column in used_sources:
            issue("MAPPING_COLLISION", name, None, "多個目標映射到相同來源欄位。", "error")
            return result
        used_sources.add(mapping.column)
        original = raw[mapping.column].astype("string")
        frame[name] = original.str.strip()
        for idx in frame.index[original.ne(frame[name])]:
            issue("VALUE_TRIMMED", name, source_rows[idx], "已移除欄值前後空白；原始值另保留。", "info")
        if mapping.column != name:
            issue("COLUMN_MAPPED", name, None, f"來源 {mapping.column} → C 顯示欄位 {name}。", "info")
    result.parsed = True
    for name in ("timestamp", "product_batch", "length_m", *FEATURE_UNITS, *TARGET_UNITS):
        if name not in frame:
            severity = "warning" if name in TARGET_UNITS else "error"
            issue("MISSING_COLUMN", name, None, f"缺少 {name}；僅停用相依用途，不補造量測。", severity)
    if any(name not in frame for name in ("timestamp", "product_batch")):
        result.frame = frame
        return result

    for name in ("timestamp", "available_at"):
        if name not in frame:
            continue
        converted = []
        for idx, value in frame[name].items():
            try:
                converted.append(_timestamp(value, profile.timezone))
            except (ValueError, TypeError, OverflowError):
                converted.append(pd.NaT)
                issue("INVALID_TIME", name, source_rows[idx], "時間無效或未帶時區；不猜測時區。", "error")
        frame[name] = pd.Series(converted, dtype="datetime64[ns, Asia/Taipei]")
    if "available_at" not in frame:
        frame["available_at"] = frame["timestamp"]
        issue("AVAILABILITY_ASSUMED", "available_at", None,
              "C 本地顯示暫用 timestamp 作可得時間；正式時間語意待跨組確認。")
    before_observation = frame.available_at.notna() & frame.timestamp.notna() & (frame.available_at < frame.timestamp)
    for idx in frame.index[before_observation]:
        issue("INVALID_AVAILABILITY", "available_at", source_rows[idx], "可得時間早於觀測時間。", "error")
        frame.loc[idx, "available_at"] = pd.NaT

    for name in UNITS:
        if name not in frame:
            continue
        values = frame[name]
        missing = values.isna() | values.eq("")
        try:
            scale, offset = unit_conversion(name, profile.entry(name).unit)
        except ValueError as exc:
            issue("UNIT_MISMATCH", name, None, str(exc), "error")
            frame[name] = np.nan
            continue
        numbers = pd.to_numeric(values, errors="coerce").astype(float) * scale + offset
        invalid = ~missing & ~np.isfinite(numbers)
        bad_range = pd.Series(False, index=frame.index)
        if name == "ambient_rh_pct":
            bad_range = numbers.notna() & ~numbers.between(0, 100)
        elif name == "appearance_ng":
            bad_range = numbers.notna() & ~numbers.isin([0, 1])
        elif name in ("length_m", "line_speed_m_min", "coating_gap_um", "coating_viscosity_mpa_s",
                      "curing_time_min", "lamination_pressure_mpa", "lamination_time_s"):
            bad_range = numbers.notna() & (numbers <= 0)
        elif name in ("position_m", "peel_strength_n_mm"):
            bad_range = numbers.notna() & (numbers < 0)
        elif UNITS[name] == "°C":
            bad_range = numbers.notna() & (numbers < -273.15)
        for mask, code, message in (
            (missing, "MISSING_VALUE", "缺失值；未補值。"),
            (invalid, "INVALID_NUMBER", "不是有效有限數值。"),
            (bad_range & ~invalid, "OUT_OF_RANGE", "超出物理範圍／標籤範圍；不是品質允收判定。"),
        ):
            for idx in frame.index[mask]:
                issue(code, name, source_rows[idx], message, "error" if code != "MISSING_VALUE" else "warning")
        numbers[missing | invalid | bad_range] = np.nan
        frame[name] = numbers
        if scale != 1 or offset != 0:
            issue("UNIT_CONVERTED", name, None,
                  f"明確轉換 {profile.entry(name).unit} → {UNITS[name]}。", "info")

    duplicate = raw.duplicated(keep=False)
    if "specimen_id" in frame:
        has_id = frame.specimen_id.fillna("").ne("")
        duplicate |= has_id & frame.duplicated(["product_batch", "specimen_id"], keep=False)
    frame["duplicate_record"] = duplicate
    for idx in frame.index[duplicate]:
        issue("DUPLICATE_RECORD", "specimen_id", source_rows[idx], "疑似重複紀錄／試片；保留供檢查，不計為可分析列。")
    batch_ok = frame.product_batch.fillna("").ne("")
    for idx in frame.index[~batch_ok]:
        issue("MISSING_ID", "product_batch", source_rows[idx], "批號不可空白。", "error")
    frame["identity_valid"] = batch_ok & frame.timestamp.notna() & frame.available_at.notna() & ~duplicate
    for name in ("segment_id", "subgroup_id", "specimen_id"):
        if name in frame:
            for idx in frame.index[frame[name].fillna("").eq("")]:
                issue("MISSING_ID", name, source_rows[idx], f"{name} 為空；相依用途受限。")
    if "segment_id" not in frame:
        frame["segment_id"] = ""
    missing_segment = frame.segment_id.fillna("").eq("")
    frame.loc[missing_segment, "segment_id"] = frame.loc[missing_segment, "source_row"].map(lambda n: f"local-row-{n}")
    frame["local_segment_id"] = missing_segment
    if missing_segment.any():
        issue("LOCAL_SEGMENT_ID", "segment_id", None, "缺區段識別，使用可追溯本地列識別；不推定正式材料對齊。")
    frame["sample_id"] = frame.source_row.map(lambda n: f"{fingerprint[:16]}:{n}")
    if not frame.available_at.dropna().is_monotonic_increasing:
        issue("TIME_SORTED", "available_at", None, "依可得時間及來源列穩定排序；來源列號不變。", "info")
    result.frame = frame.sort_values(["available_at", "source_row"], kind="stable", na_position="last").reset_index(drop=True)
    result.accepted = bool(frame.identity_valid.any())
    if not result.accepted:
        issue("NO_VALID_ROWS", None, None, "沒有具有效時間、批號及非重複識別的資料列。", "error")
    return result


def filter_rows(frame: pd.DataFrame, batch=None, start=None, end=None) -> pd.DataFrame:
    if frame.empty or "timestamp" not in frame or "product_batch" not in frame:
        return frame.iloc[0:0].copy()
    mask = frame.timestamp.notna() & frame.product_batch.fillna("").ne("")
    if batch is not None:
        mask &= frame.product_batch.eq(batch)
    if start is not None:
        mask &= frame.timestamp >= pd.Timestamp(start)
    if end is not None:
        mask &= frame.timestamp <= pd.Timestamp(end)
    return frame.loc[mask].copy()


def input_eligibility(frame: pd.DataFrame) -> dict:
    """Input availability only. No SPC verdict, model inference or policy."""
    valid = frame.get("identity_valid", pd.Series(False, index=frame.index)).fillna(False)
    feature_columns = list(FEATURE_UNITS)
    prediction = valid & frame[feature_columns].notna().all(axis=1) if set(feature_columns) <= set(frame) else valid & False
    group_ok = valid.copy()
    for name in ("subgroup_id", "specimen_id"):
        group_ok &= frame[name].fillna("").ne("") if name in frame else False
    quality = {name: int((valid & frame[name].notna()).sum()) if name in frame else 0 for name in TARGET_UNITS}
    return {
        "view_rows": int(valid.sum()), "prediction_input_rows": int(prediction.sum()),
        "quality_rows": quality,
        "grouped_quality_rows": {
            name: int((group_ok & frame[name].notna()).sum()) if name in frame else 0
            for name in CONTINUOUS_TARGETS
        },
    }
