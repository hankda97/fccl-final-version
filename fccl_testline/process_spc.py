from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np


A2_N5 = .577
D3_N5 = 0.0
D4_N5 = 2.114
D2_MR2 = 1.128


@dataclass(frozen=True)
class ControlLimits:
    chart_type: str
    center: float
    ucl: float
    lcl: float
    secondary_center: float | None = None
    secondary_ucl: float | None = None
    secondary_lcl: float | None = None
    baseline_version: str = "SIM-RECIPE-3.0-STABLE-1"


def xbar_r_limits(subgroups: Sequence[Sequence[float]]) -> ControlLimits:
    if len(subgroups) < 25 or any(len(group) != 5 for group in subgroups):
        raise ValueError("INSUFFICIENT_XBAR_R_BASELINE")
    means = np.array([np.mean(g) for g in subgroups], dtype=float); ranges = np.array([np.ptp(g) for g in subgroups], dtype=float)
    center, rbar = float(means.mean()), float(ranges.mean())
    if rbar <= 0: raise ValueError("DEGENERATE_XBAR_R_BASELINE")
    return ControlLimits("XBAR_R", center, center + A2_N5*rbar, center - A2_N5*rbar, rbar, D4_N5*rbar, D3_N5*rbar)


def imr_limits(values: Sequence[float], *, chart_type: str = "I-MR") -> ControlLimits:
    if len(values) < 25: raise ValueError("INSUFFICIENT_IMR_BASELINE")
    array = np.asarray(values, dtype=float); mr = np.abs(np.diff(array)); mrbar = float(mr.mean())
    if mrbar <= 0: raise ValueError("DEGENERATE_IMR_BASELINE")
    center = float(array.mean()); sigma = mrbar / D2_MR2
    return ControlLimits(chart_type, center, center + 3*sigma, center - 3*sigma, mrbar, 3.267*mrbar, 0.0)


@dataclass
class IncrementalSPC:
    limits: ControlLimits
    ewma_lambda: float = .2
    values: list[float] = field(default_factory=list)
    secondary: list[float] = field(default_factory=list)

    def update_individual(self, value: float) -> dict[str, float | str | bool]:
        previous = self.values[-1] if self.values else None; self.values.append(float(value))
        mr = abs(value - previous) if previous is not None else float("nan")
        self.secondary.append(mr)
        if self.limits.chart_type == "EWMA":
            plotted = self.limits.center if len(self.values) == 1 else self.ewma_lambda*value + (1-self.ewma_lambda)*float(self.latest_plotted)
        else: plotted = float(value)
        self.latest_plotted = plotted
        return {"plotted": plotted, "actual": float(value), "moving_range": mr, "beyond_limit": plotted > self.limits.ucl or plotted < self.limits.lcl}

    def update_subgroup(self, points: Sequence[float]) -> dict[str, float | bool]:
        if len(points) != 5 or not np.isfinite(points).all(): raise ValueError("INCOMPLETE_THICKNESS_SUBGROUP")
        mean, span = float(np.mean(points)), float(np.ptp(points)); self.values.append(mean); self.secondary.append(span)
        return {"xbar": mean, "range": span, "xbar_beyond_limit": mean > self.limits.ucl or mean < self.limits.lcl, "range_beyond_limit": span > float(self.limits.secondary_ucl)}

    def recent(self, limit: int = 60) -> list[float]:
        return self.values[-limit:]
