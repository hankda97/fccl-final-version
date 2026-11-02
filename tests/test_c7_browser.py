"""Real Chromium timer evidence; distinct from Streamlit AppTest."""
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


def test_real_browser_play_pause_step_restart_speed_and_end(tmp_path):
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    log=tmp_path/'server.log'
    with log.open('w',encoding='utf-8') as out:
        server=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.headless=true',
                '--server.address=127.0.0.1',f'--server.port={port}','--browser.gatherUsageStats=false'],
                cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1'})
        try:
            opener=build_opener(ProxyHandler({}))
            for _ in range(200):
                try:
                    if opener.open(f'http://127.0.0.1:{port}/_stcore/health',timeout=1).status==200:break
                except OSError:time.sleep(.1)
            else:raise AssertionError(log.read_text(encoding='utf-8'))
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
                page=browser.new_page(viewport={'width':1600,'height':1100})
                page.goto(f'http://127.0.0.1:{port}')
                page.get_by_text('上傳 CSV',exact=True).click()
                page.locator('input[type=file]').set_input_files(ROOT/'tests/fixtures/c_replay/delayed.csv')
                page.get_by_role('button',name='載入上傳 CSV',exact=True).click()
                page.get_by_text('歷史時間映射（C 來源轉接設定）',exact=True).click()
                page.get_by_label('時間 profile JSON（空白恢復來源預設）').fill((ROOT/'tests/fixtures/c_replay/profile.json').read_text(encoding='utf-8'))
                page.get_by_role('button',name='套用時間設定',exact=True).click()
                expect(page.get_by_text('已套用時間設定：c7-delayed-v1',exact=True)).to_be_visible(timeout=20000)
                page.get_by_text('CSV 定時回放',exact=True).click()
                progress=page.get_by_text(re.compile(r'^已釋出 \d+／15 列 · 事件群'))
                expect(progress).to_contain_text('事件群 0／9',timeout=20000)
                page.get_by_role('button',name='單步前進',exact=True).click()
                expect(progress).to_contain_text('事件群 1／9')
                page.get_by_role('button',name='重新開始',exact=True).click()
                expect(progress).to_contain_text('事件群 0／9')
                page.get_by_role('button',name='播放／暫停',exact=True).click()
                expect(progress).not_to_contain_text('事件群 0／9',timeout=15000)
                page.get_by_role('button',name='播放／暫停',exact=True).click()
                expect(page.get_by_text(re.compile(r'^回放時間：.* · 暫停$'))).to_be_visible()
                paused=progress.inner_text();page.wait_for_timeout(1100)
                assert progress.inner_text()==paused
                page.get_by_role('button',name='重新開始',exact=True).click()
                expect(progress).to_contain_text('事件群 0／9')
                page.get_by_role('combobox',name='回放速度',exact=True).click()
                page.get_by_role('option',name='4x',exact=True).click()
                page.get_by_role('button',name='播放／暫停',exact=True).click()
                expect(progress).to_contain_text('事件群 9／9',timeout=25000)
                expect(page.get_by_text(re.compile(r'^回放時間：.* · 完成$'))).to_be_visible()
                assert '已釋出 15／15' in progress.inner_text()
                assert not page.locator('[data-testid="stException"]').count()
                evidence=Path(os.environ.get('FCCL_BROWSER_EVIDENCE_DIR',ROOT/'docs/evidence'))
                evidence.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(evidence/'C7_BROWSER.png'),full_page=True)
                (evidence/'C7_BROWSER.json').write_text(json.dumps({'browser':browser.version,'headless':True,
                    'engine':'Chrome via Playwright','checks':['single step','restart','automatic timer',
                    'pause retains progress for 1100ms','4x playback','automatic stop at end','15 unique source rows'],
                    'final_progress':progress.inner_text(),'timestamp':time.strftime('%Y-%m-%d %H:%M:%S %z'),
                    'source':'C7 synthetic delayed fixture, not real plant data'},ensure_ascii=False,indent=2),encoding='utf-8')
                browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
