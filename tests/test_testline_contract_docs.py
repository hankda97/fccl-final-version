from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gate1_contract_documents_are_aligned() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    dictionary = (ROOT / "docs" / "TESTLINE_V3_DATA_DICTIONARY.md").read_text(encoding="utf-8")
    spec_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(
            (ROOT / "openspec" / "changes" / "build-testline-simulation-control-room" / "specs").rglob("*.md")
        )
    )

    for token in ("FCCL-DEMO-001", "SIM-RECIPE-3.0", "runtime_data/testline_runs"):
        assert token in agents
        assert token in skill
        assert token in spec_text
    for target in (
        "peel_strength_n_mm",
        "dimensional_stability_md_pct",
        "dimensional_stability_td_pct",
        "heat_resistance_c",
    ):
        assert target in dictionary
    assert "單一 Mode B" in agents
    assert "五份 Run CSV" in dictionary
    assert "外觀 v2 artifact 保留" in skill
