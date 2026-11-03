from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT=Path(__file__).resolve().parents[1]


def test_run_page_shows_manifest_exports_and_no_training_action() -> None:
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=45).run(); assert not app.exception
    engine=app.session_state.testline_engine; engine.step(12); engine.stop()
    app.button(key="testline_nav_Run 紀錄").click().run(); assert not app.exception
    labels=[button.label for button in app.get("download_button")]
    assert "下載 manifest.json" in labels and any(label.startswith("下載 process_signals.csv") for label in labels)
    body="\n".join(str(x.value) for group in (app.caption,app.warning,app.info,app.markdown) for x in group)
    assert "不會觸發訓練" in body and "續跑" not in " ".join(b.label for b in app.button)
