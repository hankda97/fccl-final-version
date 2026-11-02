"""Internal mode context, independent of A/B's formal contracts."""
from dataclasses import dataclass, field
from uuid import uuid4

MODES = ("analysis", "testline", "production")
LABELS = {"analysis": "A｜AI 品質預測與關鍵因子分析",
          "testline": "B｜測試線動態參數實驗",
          "production": "C｜現場產線波動與動態線速補償"}
REGISTRY_VERSION = "c-modes-v1"


@dataclass
class RunContext:
    mode_id: str
    workspace_id: str = field(default_factory=lambda: uuid4().hex)
    run_id: str | None = None
    generation: int = 0
    activation_epoch: int = 0
    settings_version: str = "unavailable"
    simulator_version: str = "unavailable"
    source_kind: str = "unavailable"
    cutoff: str | None = None
    spc_profile: object | None = None


@dataclass
class UiPreferences:
    values: dict = field(default_factory=dict)


@dataclass
class ModeRegistry:
    workspaces: dict
    version: str = REGISTRY_VERSION
    active_mode: str = "analysis"
    preferences: dict = field(default_factory=lambda: {m: UiPreferences() for m in MODES})
    # Append-only per-run/channel event indexes; reset never deletes past runs.
    events: dict = field(default_factory=lambda: {m: {} for m in MODES})
    errors: dict = field(default_factory=lambda: {m: [] for m in MODES})


@dataclass(frozen=True)
class ContextToken:
    content: tuple
    activation_epoch: int
    request_key: str


@dataclass(frozen=True)
class ModeIssue:
    code: str
    field: str
    message: str
