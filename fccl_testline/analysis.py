from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .dataset import FEATURE_ALLOWLIST
from .generation import TARGETS
from .modeling import load_trusted_bundle, predict_bundle
from .types import validate_model_support


PARAMETER_TO_FEATURE = {
    "line_speed_m_min": "line_speed_actual_m_min", "coating_gap_um": "coating_gap_actual_um",
    "curing_temp_c": "curing_temp_actual_c", "exhaust_airflow_m3_h": "exhaust_airflow_actual_m3_h",
    "curing_time_min": "curing_time_actual_min", "lamination_temp_c": "lamination_temp_actual_c",
    "lamination_pressure_mpa": "lamination_pressure_actual_mpa", "coating_temp_c": "coating_temp_actual_c",
    "coating_viscosity_mpa_s": "coating_viscosity_actual_mpa_s", "lamination_time_min": "lamination_time_actual_min",
}


class HeatmapService:
    def __init__(self) -> None: self._cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def current_rows(candidates: pd.DataFrame, predictions: list[Mapping[str, Any]]) -> pd.DataFrame:
        pred = pd.DataFrame(predictions)
        if pred.empty: return pd.DataFrame()
        if pred.duplicated(["segment_id", "target"]).any(): raise ValueError("DUPLICATE_QUALITY_PREDICTION")
        wide = pred.pivot(index="segment_id", columns="target", values="prediction").reset_index()
        required = ["segment_id", *FEATURE_ALLOWLIST]
        missing = set(required) - set(candidates)
        if missing: raise ValueError("MISSING_HEATMAP_FEATURES:" + ",".join(sorted(missing)))
        rows = candidates.loc[:, required].drop_duplicates("segment_id").merge(wide, on="segment_id", how="inner", validate="one_to_one")
        return rows.dropna(subset=list(TARGETS))

    def calculate(self, rows: pd.DataFrame, *, source: str, version: str, cutoff: str, minimum: int = 30) -> dict[str, Any]:
        if source not in {"v3_reference", "current_run"}: raise ValueError("UNKNOWN_HEATMAP_SOURCE")
        if len(rows) < minimum: raise ValueError(f"INSUFFICIENT_COMPLETED_SEGMENTS:{minimum-len(rows)}")
        columns=[c for c in FEATURE_ALLOWLIST if c in rows] + list(TARGETS)
        key=hashlib.sha256((source+version+cutoff+rows.loc[:,columns].to_csv(index=False)).encode()).hexdigest()
        if key in self._cache: return self._cache[key]
        correlation=rows.loc[:,columns].corr(method="pearson").loc[list(FEATURE_ALLOWLIST),list(TARGETS)]
        result={"source":source,"version":version,"cutoff":cutoff,"segments":len(rows),"correlation":correlation,"cache_key":key,"method":"Pearson; one completed segment per row; correlation is not causation"}
        self._cache[key]=result; return result


class WhatIfService:
    def __init__(self, artifact_root: Path) -> None:
        self.root=artifact_root.resolve(); self.bundles={}; self.manifests={}
        for target in TARGETS:
            path=self.root/target; self.bundles[target]=load_trusted_bundle(path/"bundle.joblib",self.root)
            self.manifests[target]=json.loads((path/"manifest.json").read_text(encoding="utf-8"))

    def compare(self, row: Mapping[str, Any], candidate: Mapping[str, float]) -> dict[str, Any]:
        base=pd.DataFrame([{name:float(row[name]) for name in FEATURE_ALLOWLIST}]); changed=base.copy()
        for parameter,value in candidate.items():
            if parameter not in PARAMETER_TO_FEATURE: raise ValueError(f"UNSUPPORTED_WHATIF_PARAMETER:{parameter}")
            changed.loc[0,PARAMETER_TO_FEATURE[parameter]]=float(value)
        output={"segment_id":str(row["segment_id"]),"candidate":dict(candidate),"targets":{},"non_causal":True}
        for target in TARGETS:
            support=validate_model_support({name:float(changed.loc[0,name]) for name in FEATURE_ALLOWLIST},self.manifests[target])
            if "extrapolation" in support.values(): raise ValueError(f"MODEL_EXTRAPOLATION:{target}")
            before=float(predict_bundle(self.bundles[target],base)[0]); after=float(predict_bundle(self.bundles[target],changed)[0])
            output["targets"][target]={"before":before,"after":after,"delta":after-before}
        return output
