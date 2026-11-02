"""Explicitly bind registered C test bytes to their sampling evidence."""

from hashlib import sha256
import json
from pathlib import Path

from c_dashboard.spc.config import profile_from_dict

SPC_FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "c_spc"


def load_c_profile():
    return profile_from_dict(json.loads((SPC_FIXTURES / "profile.json").read_text(encoding="utf-8")))


def profile_for_dataset(dataset):
    if dataset is None or dataset.source_kind != "mock":
        return None
    profile = load_c_profile()
    if dict(profile.monitoring_hashes).get(dataset.source_name) != sha256(dataset.content).hexdigest():
        return None
    return profile
