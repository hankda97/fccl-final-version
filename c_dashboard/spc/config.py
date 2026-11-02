"""Explicit C-only sampling profile, not the formal contract of A or B."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math

import pandas as pd

from c_dashboard.data.schema import CONTINUOUS_TARGETS, TARGET_UNITS

# One consistent table, NIST e-Handbook pmc321 (A2, D3, D4).
CONSTANTS_VERSION = "nist-pmc321-v1"
CONSTANTS_SOURCE = "https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm"
CONSTANTS = {
    2: (1.880, 0, 3.267), 3: (1.023, 0, 2.575), 4: (0.729, 0, 2.282),
    5: (0.577, 0, 2.115), 6: (0.483, 0, 2.004), 7: (0.419, .076, 1.924),
    8: (.373, .136, 1.864), 9: (.337, .184, 1.816), 10: (.308, .223, 1.777),
}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             default=str, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class RuleConfig:
    version: str = "c-spc-rules-v1"


@dataclass(frozen=True)
class SpcProfile:
    profile_id: str = "c-mock-independent-specimens"
    version: str = "c-spc-profile-v1"
    product: str = "C-DEMO-01"
    recipe: str = "C-MOCK-v1"
    n: int = 5
    minimum_history_groups: int = 25
    independent_specimens: bool = True
    monitoring_origin: str = "2026-11-01T08:00:00+08:00"
    interval_seconds: float | None = 60.0
    conditions: tuple[tuple[str, float], ...] = ()
    condition_tolerance: float = 0.0
    environment_ranges: tuple[tuple[str, float, float], ...] = ()
    units: tuple[tuple[str, str], ...] = tuple((k, TARGET_UNITS[k]) for k in CONTINUOUS_TARGETS)
    constants_version: str = CONSTANTS_VERSION
    stability_version: str = "c-spc-stability-v1"
    history_hash: str = ""
    monitoring_hashes: tuple[tuple[str, str], ...] = ()

    def issues(self, target=None):
        errors = []
        if type(self.n) is not int or self.n not in CONSTANTS:
            errors.append("UNSUPPORTED_SUBGROUP_SIZE")
        if not self.independent_specimens or not self.conditions or not self.product or not self.recipe:
            errors.append("MISSING_SAMPLING_EVIDENCE")
        if type(self.minimum_history_groups) is not int or self.minimum_history_groups < 2:
            errors.append("INVALID_HISTORY_MINIMUM")
        if self.constants_version != CONSTANTS_VERSION or self.stability_version != "c-spc-stability-v1":
            errors.append("UNSUPPORTED_POLICY_VERSION")
        if (not math.isfinite(self.condition_tolerance) or self.condition_tolerance < 0
                or any(not math.isfinite(v) for _, v in self.conditions)):
            errors.append("INVALID_CONDITIONS")
        if self.interval_seconds is not None and (not math.isfinite(self.interval_seconds) or self.interval_seconds <= 0):
            errors.append("INVALID_INTERVAL")
        if any(not math.isfinite(lo) or not math.isfinite(hi) or lo > hi
               for _, lo, hi in self.environment_ranges):
            errors.append("INVALID_ENVIRONMENT_RANGE")
        try:
            origin = pd.Timestamp(self.monitoring_origin)
            if pd.isna(origin) or origin.tzinfo is None:
                errors.append("INVALID_MONITORING_ORIGIN")
        except (ValueError, TypeError):
            errors.append("INVALID_MONITORING_ORIGIN")
        unit_map = dict(self.units)
        if ((target is None and unit_map != {k: TARGET_UNITS[k] for k in CONTINUOUS_TARGETS})
                or (target is not None and unit_map.get(target) != TARGET_UNITS[target])):
            errors.append("UNIT_MISMATCH")
        return tuple(dict.fromkeys(errors))

    def signature(self):
        return digest(asdict(self))


def profile_from_dict(value):
    data = dict(value)
    for key in ("conditions", "environment_ranges", "units", "monitoring_hashes"):
        if key in data:
            data[key] = tuple(tuple(item) for item in data[key])
    return SpcProfile(**data)
