from dataclasses import FrozenInstanceError, replace

import pytest

from c_dashboard.spc.config import CONSTANTS, SpcProfile, profile_from_dict
from c_dashboard.spc.types import TargetBaseline


def test_profile_size_units_sampling_and_versions_are_explicit():
    p = SpcProfile(conditions=(("line_speed_m_min", 2.0),))
    assert not p.issues()
    assert not replace(p, n=3).issues()
    assert CONSTANTS[3][0] == 1.023 and CONSTANTS[5][0] == .577
    for changed, code in [({"n": 1}, "UNSUPPORTED_SUBGROUP_SIZE"),
                          ({"n": 11}, "UNSUPPORTED_SUBGROUP_SIZE"),
                          ({"independent_specimens": False}, "MISSING_SAMPLING_EVIDENCE"),
                          ({"conditions": ()}, "MISSING_SAMPLING_EVIDENCE"),
                          ({"monitoring_origin": "2026-11-01"}, "INVALID_MONITORING_ORIGIN"),
                          ({"units": ()}, "UNIT_MISMATCH"),
                          ({"constants_version": "other"}, "UNSUPPORTED_POLICY_VERSION"),
                          ({"interval_seconds": 0}, "INVALID_INTERVAL")]:
        assert code in replace(p, **changed).issues()
    assert p.signature() != replace(p, n=3).signature()
    assert profile_from_dict({"conditions": [["line_speed_m_min", 2.0]]}) == p


def test_profile_and_baseline_values_are_immutable():
    with pytest.raises(FrozenInstanceError):
        SpcProfile().n = 3
    with pytest.raises(FrozenInstanceError):
        TargetBaseline("test", "unit").cl = 10
