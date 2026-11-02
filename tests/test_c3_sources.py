from hashlib import sha256
import json

from c_dashboard.data.fixtures import FIXTURE_DIR, MOCK_CHOICES, load_mock_fixture, load_spc_history
from c_dashboard.spc.sources import SPC_FIXTURES, load_c_profile, profile_for_dataset


def test_registered_history_and_monitoring_bytes_are_reproducible_and_separate():
    p = load_c_profile()
    assert not p.issues()
    h = load_spc_history()
    assert h.accepted and len(h.frame) == 125
    assert sha256(h.content).hexdigest() == p.history_hash
    assert "history" not in MOCK_CHOICES.values()
    assert profile_for_dataset(load_mock_fixture("normal")) == p
    assert load_spc_history().content == h.content
    for name, digest in p.monitoring_hashes:
        assert sha256((FIXTURE_DIR / name).read_bytes()).hexdigest() == digest
    cases = json.loads((SPC_FIXTURES / "cases.json").read_text(encoding="utf-8"))
    assert cases["formula_n3"]["ucl"] == 1.27046


def test_unregistered_upload_and_tampered_mock_have_no_automatic_sampling_evidence():
    data = load_mock_fixture("normal")
    data.source_kind = "upload"
    assert profile_for_dataset(data) is None
    data.source_kind = "mock"
    data.content += b"\n"
    assert profile_for_dataset(data) is None
