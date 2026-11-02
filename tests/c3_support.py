"""Explicit hand-computable SPC samples, not a process data generator."""

from dataclasses import replace
import json

import pandas as pd

from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.spc.sources import SPC_FIXTURES, load_c_profile

PEEL = "peel_strength_n_mm"
MD = "dimensional_stability_md_pct"
TD = "dimensional_stability_td_pct"
HEAT = "heat_resistance_c"


def hand_history(n=5, groups=25):
    cases = json.loads((SPC_FIXTURES / "cases.json").read_text(encoding="utf-8"))
    values = cases[f"formula_n{n}"]["values"]
    template = load_mock_fixture("normal").frame.iloc[0].to_dict()
    rows = []
    for group in range(groups):
        for specimen, value in enumerate(values):
            row = dict(template)
            t = pd.Timestamp("2026-10-31T08:00:00+08:00") + pd.Timedelta(minutes=group)
            row.update(timestamp=t, available_at=t, product_batch="H-HAND", subgroup_id=f"G{group}",
                       segment_id=f"S{group}", specimen_id=f"H{group}-{specimen}", source_row=len(rows) + 2,
                       sample_id=f"hand-{group}-{specimen}", identity_valid=True, duplicate_record=False,
                       local_segment_id=False)
            row[PEEL] = value
            row[MD] = -.02 + (specimen - (n-1)/2) * .002
            row[TD] = -.01 + (specimen - (n-1)/2) * .002
            row[HEAT] = 290.0 + specimen - (n-1)/2
            rows.append(row)
    return pd.DataFrame(rows), replace(load_c_profile(), n=n, history_hash="", monitoring_hashes=())


def monitoring(means, target=PEEL, n=5):
    rows, profile = hand_history(n, len(means))
    rows["timestamp"] += pd.Timedelta(days=1)
    rows["available_at"] += pd.Timedelta(days=1)
    rows["product_batch"] = "M-HAND"
    rows["specimen_id"] = "M-" + rows.specimen_id
    for group, mean in enumerate(means):
        indexes = rows.index[group*n:(group+1)*n]
        rows.loc[indexes, target] = [mean + (j-(n-1)/2)*.001 for j in range(n)]
    return rows, profile
