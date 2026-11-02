"""Read checked-in C-only samples. This does not generate A's data."""

import json
from pathlib import Path

from c_dashboard.data.loader import load_csv
from c_dashboard.data.schema import MappingProfile

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "c_mock"
MOCK_CHOICES = {
    "正常模擬資料": "normal",
    "部分品質欄位缺失": "partial_quality",
    "無品質量測": "no_quality",
    "無子組識別": "ungrouped",
    "無效值與重複紀錄": "invalid_values",
    "缺少必要識別欄位": "missing_columns",
    "單點品質偏移情境": "out_of_control",
    "上升趨勢情境": "trend",
    "同側偏移情境": "same_side",
}


def load_mock_fixture(name: str):
    if name not in MOCK_CHOICES.values():
        raise ValueError("未知 C Mock 情境。")
    metadata = json.loads((FIXTURE_DIR / "metadata.json").read_text(encoding="utf-8"))
    result = load_csv(
        (FIXTURE_DIR / f"{name}.csv").read_bytes(), f"{name}.csv", source_kind="mock",
        profile=MappingProfile("C 專用模擬資料", metadata["version"]),
    )
    result.metadata = metadata
    result.settings = json.loads((FIXTURE_DIR / "settings.json").read_text(encoding="utf-8"))
    return result


def load_spc_history():
    """Separate historical input, deliberately absent from MOCK_CHOICES."""
    return load_csv((FIXTURE_DIR / "history.csv").read_bytes(), "history.csv",
                    source_kind="mock-history", profile=MappingProfile("C 獨立歷史", "c-fixtures-v1"))
