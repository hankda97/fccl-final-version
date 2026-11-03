"""Real-Chrome acceptance for the formal single Mode-B control room."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

from playwright.sync_api import sync_playwright, expect


ROOT=Path(__file__).resolve().parents[1]


def test_real_browser_single_mode_runtime_spc_analysis_and_runs(tmp_path):
    with socket.socket() as sock: sock.bind(("127.0.0.1",0)); port=sock.getsockname()[1]
    log=tmp_path/"server.log"
    with log.open("w",encoding="utf-8") as out:
        server=subprocess.Popen([sys.executable,"-m","streamlit","run","app.py","--server.headless=true","--server.address=127.0.0.1",f"--server.port={port}","--browser.gatherUsageStats=false"],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,env={**os.environ,"PYTHONUTF8":"1"})
        try:
            opener=build_opener(ProxyHandler({}))
            for _ in range(200):
                try:
                    if opener.open(f"http://127.0.0.1:{port}/_stcore/health",timeout=1).status==200: break
                except OSError: time.sleep(.1)
            else: raise AssertionError(log.read_text(encoding="utf-8"))
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
                page=browser.new_page(viewport={"width":1600,"height":1100}); page.goto(f"http://127.0.0.1:{port}")
                expect(page.get_by_text("3L FCCL 測試線模擬控制台",exact=True)).to_be_visible(timeout=30000)
                assert not page.get_by_text(re.compile(r"模式 [AC]")).count()
                for _ in range(2): page.get_by_role("button",name="前進 12 點（60 秒）").click()
                expect(page.get_by_text("抗剝離度",exact=True)).to_be_visible(timeout=30000)
                page.get_by_role("button",name=re.compile("SPC 詳細監控")).click()
                for title in ("乾膠厚度 X-bar／R","熟化溫度 I-MR","排風量 EWMA","線速 I-MR","壓合壓力 I-MR"): expect(page.get_by_text(title,exact=True).first).to_be_visible()
                page.get_by_role("button",name=re.compile("What-if／Heatmap")).click(); page.get_by_role("tab",name="Heatmap").click()
                page.get_by_role("button",name="重新計算 Heatmap").click(); expect(page.get_by_text(re.compile("500 個完成區段"))).to_be_visible(timeout=30000)
                page.get_by_role("button",name=re.compile("Run 紀錄")).click(); expect(page.get_by_text(re.compile("不會觸發訓練"))).to_be_visible()
                assert not page.locator('[data-testid="stException"]').count()
                evidence=ROOT/"docs/evidence/formal-control-room"; evidence.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(evidence/"formal-run-record.png"),full_page=True)
                (evidence/"BROWSER.json").write_text(json.dumps({"browser":browser.version,"timestamp":time.strftime("%Y-%m-%d %H:%M:%S %z"),"source":"Synthetic v3 local runtime","checks":["single Mode B","24 ticks","four predictions","five SPC charts","reference heatmap","Run records","no Streamlit exception"]},ensure_ascii=False,indent=2),encoding="utf-8")
                browser.close()
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=5)
