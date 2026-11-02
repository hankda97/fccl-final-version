"""Pairwise measured-data Pearson analysis with explicit eligibility counts."""

from hashlib import sha256
import json

import numpy as np
import pandas as pd

from c_dashboard.data.schema import FEATURE_UNITS, TARGET_UNITS
from c_dashboard.visualization.config import MINIMUM_PAIRS, VISUALIZATION_VERSION
from c_dashboard.visualization.types import ChartSource, HeatmapCell, HeatmapResult
from c_dashboard.visualization.sources import infer_profile, metadata_columns, source_context, label_eligibility


def content_digest(rows: pd.DataFrame, columns) -> str:
    names = list(dict.fromkeys(name for name in columns if name in rows))
    # Explicit columns prevent predictions or fixture truth becoming hidden inputs.
    content = rows[names].to_json(orient="split", date_format="iso", default_handler=str)
    return sha256(content.encode("utf-8")).hexdigest()


def source_for(rows: pd.DataFrame, *, source_id: str, mapping_version: str,
               source_kind: str, batch=None, time_start=None, time_end=None,
               columns=None, profile=None) -> ChartSource:
    columns = columns if columns is not None else (*FEATURE_UNITS, *TARGET_UNITS)
    identity = ("sample_id", "timestamp", "available_at", "identity_valid", "duplicate_record")
    times = rows["available_at"].dropna() if "available_at" in rows else pd.Series(dtype=object)
    cutoff = str(times.max()) if not times.empty else None
    return ChartSource(source_id, mapping_version, source_kind, batch, time_start,
                       time_end, cutoff, content_digest(rows, (*identity, *columns, *metadata_columns(rows))),
                       profile or infer_profile(rows, source_kind), source_context(rows))


def eligible_rows(rows: pd.DataFrame) -> pd.DataFrame:
    valid = rows.get("identity_valid", pd.Series(False, index=rows.index)).fillna(False).eq(True)
    duplicate = rows.get("duplicate_record", pd.Series(False, index=rows.index)).fillna(True)
    valid = valid & ~duplicate.astype(bool)
    if "sample_id" in rows:
        valid = valid & rows.sample_id.notna() & ~rows.sample_id.duplicated(keep=False)
    return rows.loc[valid].copy()


def numeric_values(rows: pd.DataFrame, name: str) -> pd.Series:
    values = pd.to_numeric(rows[name], errors="coerce").astype(float)
    values = values.where(np.isfinite(values))
    if name == "appearance_ng":
        values = values.where(values.isin([0, 1]))
    elif name == "ambient_rh_pct":
        values = values.where(values.between(0, 100))
    elif name in {"line_speed_m_min", "coating_gap_um", "coating_viscosity_mpa_s",
                  "curing_time_min", "lamination_pressure_mpa", "lamination_time_s"}:
        values = values.where(values > 0)
    elif name == "peel_strength_n_mm":
        values = values.where(values >= 0)
    elif {**FEATURE_UNITS, **TARGET_UNITS}.get(name) == "°C":
        values = values.where(values >= -273.15)
    return values


def compute_heatmap(rows: pd.DataFrame, source: ChartSource, features, targets,
                    *, minimum_pairs: int = MINIMUM_PAIRS) -> HeatmapResult:
    if not isinstance(minimum_pairs, int) or isinstance(minimum_pairs, bool) or minimum_pairs < 3:
        raise ValueError("最低有效配對數須為至少 3 的 C 顯示測試設定。")
    if any(name not in FEATURE_UNITS for name in features):
        raise ValueError("Heatmap 特徵不在製程／環境 allowlist。")
    if any(name not in TARGET_UNITS for name in targets):
        raise ValueError("Heatmap 目標不在實測品質 allowlist。")
    valid = eligible_rows(rows)
    cells = []
    for feature in dict.fromkeys(features):
        for target in dict.fromkeys(targets):
            reason = None
            number = None
            n = 0
            label_mask, exclusions = label_eligibility(valid, target, source.profile)
            if feature not in valid or target not in valid:
                reason = "缺少欄位：" + "、".join(name for name in (feature, target) if name not in valid)
            else:
                x, y = numeric_values(valid, feature), numeric_values(valid, target)
                paired = x.notna() & y.notna() & label_mask
                x, y = x[paired], y[paired]
                n = len(x)
                if n < minimum_pairs:
                    reason = f"有效配對不足：n={n}，最低 {minimum_pairs}（C 顯示測試設定）"
                    if exclusions:
                        reason += "；" + "；".join(code for code, _ in exclusions)
                elif x.nunique() < 2 or y.nunique() < 2:
                    reason = "欄位無變異／常數" if target != "appearance_ng" or y.nunique() > 1 else "外觀僅單一類別／無變異"
                else:
                    number = float(x.corr(y, method="pearson"))
                    if not np.isfinite(number):
                        reason, number = "數值計算不可用", None
            cells.append(HeatmapCell(feature, target, number, n, len(rows) - n, reason, exclusions))
    return HeatmapResult(source, tuple(cells), len(rows), len(valid), len(rows) - len(valid),
                         minimum_pairs, VISUALIZATION_VERSION)
