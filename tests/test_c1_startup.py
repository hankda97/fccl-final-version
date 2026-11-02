"""Import and localhost server smoke checks; no deployment or machine access."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]


def test_modules_import_without_running_the_ui():
    completed = subprocess.run(
        [
            sys.executable, "-c",
            "import app; import c_dashboard.state; import c_dashboard.adapters.base; "
            "import c_dashboard.adapters.unavailable; import c_dashboard.ui.layout; "
            "import c_dashboard.data.loader; import c_dashboard.data.session; "
            "import streamlit; print('IMPORT_OK', streamlit.__version__)",
        ],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "IMPORT_OK" in completed.stdout


def test_streamlit_starts_and_serves_local_health_and_page(tmp_path):
    with socket.socket() as address:
        address.bind(("127.0.0.1", 0))
        port = address.getsockname()[1]
    log_path = tmp_path / "startup.log"
    env = dict(os.environ, PYTHONUTF8="1")
    opener = build_opener(ProxyHandler({}))
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py",
             "--server.headless=true", "--server.address=127.0.0.1",
             f"--server.port={port}", "--browser.gatherUsageStats=false"],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text(encoding="utf-8"))
                try:
                    with opener.open(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            assert response.read().strip() == b"ok"
                            break
                except (URLError, TimeoutError):
                    pass
                time.sleep(0.1)
            else:
                raise AssertionError("Streamlit startup timed out: " + log_path.read_text(encoding="utf-8"))
            with opener.open(f"http://127.0.0.1:{port}/", timeout=5) as response:
                assert response.status == 200
                assert b"<html" in response.read().lower()
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
