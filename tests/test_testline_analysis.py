from pathlib import Path

import pandas as pd
import pytest

from fccl_testline.analysis import HeatmapService, WhatIfService
from fccl_testline.generation import TARGETS


ROOT=Path(__file__).resolve().parents[1]


def test_reference_heatmap_is_one_segment_per_row_and_cached() -> None:
    rows=pd.read_csv(ROOT/"generated_data/v3/stable_reference.csv"); service=HeatmapService()
    first=service.calculate(rows,source="v3_reference",version="v1",cutoff="500")
    second=service.calculate(rows,source="v3_reference",version="v1",cutoff="500")
    assert first is second and first["segments"]==500
    assert first["correlation"].shape==(13,4)


def test_current_heatmap_rejects_short_or_duplicate_quality() -> None:
    candidates=pd.read_csv(ROOT/"generated_data/v3/canonical_v3.csv").head(2)
    predictions=[{"segment_id":row.segment_id,"target":target,"prediction":float(row[target])} for _,row in candidates.iterrows() for target in TARGETS]
    service=HeatmapService(); rows=service.current_rows(candidates,predictions)
    assert len(rows)==2
    with pytest.raises(ValueError,match="INSUFFICIENT_COMPLETED_SEGMENTS"): service.calculate(rows,source="current_run",version="R",cutoff="1")
    with pytest.raises(ValueError,match="DUPLICATE_QUALITY_PREDICTION"): service.current_rows(candidates,predictions+[predictions[0]])


def test_whatif_is_isolated_four_target_comparison() -> None:
    row=pd.read_csv(ROOT/"generated_data/v3/canonical_v3.csv").iloc[0]
    service=WhatIfService(ROOT/"artifacts/synthetic_v3/quality-v3.0")
    result=service.compare(row,{"line_speed_m_min":float(row.line_speed_actual_m_min)})
    assert set(result["targets"])==set(TARGETS) and result["non_causal"] is True
    assert all(abs(v["delta"])<1e-12 for v in result["targets"].values())
