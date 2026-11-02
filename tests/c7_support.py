"""C7 fixed release-time fixtures, isolated from A's generator."""
import json
from pathlib import Path
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.data.loader import load_csv
from c_dashboard.data.session import commit_dataset
from c_dashboard.state import WorkspaceState
from c_dashboard.replay.controller import set_mode, operate, snapshot_for

FIXTURES = Path(__file__).parent / "fixtures/c_replay"
CONFIG = json.loads((FIXTURES / "profile.json").read_text(encoding="utf-8"))


def delayed_workspace(raw=None):
    result = load_csv(raw if raw is not None else (FIXTURES / "delayed.csv").read_bytes(),
                      "c7-delayed.csv", source_kind="mock")
    old = load_mock_fixture("normal")
    result.settings, result.metadata = old.settings, old.metadata
    w = WorkspaceState()
    commit_dataset(w, result)
    w.data.temporal_config = CONFIG
    set_mode(w, "replay")
    return w


def through(w, time):
    import pandas as pd
    from c_dashboard.replay.controller import timeline_for
    timeline = timeline_for(w)
    while w.replay.cursor < len(timeline.groups) and timeline.groups[w.replay.cursor][0].available_at <= pd.Timestamp(time):
        operate(w, "step", 0)
    return snapshot_for(w)
