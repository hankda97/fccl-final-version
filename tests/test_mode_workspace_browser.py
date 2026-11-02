"""Real Chrome routing + original C7 timer; not a replacement for unit tests."""
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
from c_dashboard.workspace_modes.types import LABELS

ROOT=Path(__file__).resolve().parents[1]


def test_real_browser_navigation_preserves_c7_timer_controls_and_isolation(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    with (tmp_path/'server.log').open('w',encoding='utf-8') as out:
        server=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.headless=true',
            '--server.address=127.0.0.1',f'--server.port={port}','--browser.gatherUsageStats=false'],
            cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1'})
        try:
            opener=build_opener(ProxyHandler({}))
            for _ in range(200):
                try:
                    if opener.open(f'http://127.0.0.1:{port}/_stcore/health',timeout=1).status==200:break
                except OSError:time.sleep(.1)
            else:raise AssertionError((tmp_path/'server.log').read_text(encoding='utf-8'))
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
                for _ in range(2):
                    page.get_by_role('button',name='單步前進',exact=True).click()
                expect(progress).to_contain_text('事件群 2／9')
                page.get_by_role('button',name='播放／暫停',exact=True).click()
                expect(page.get_by_text(re.compile(r'^回放時間：.* · 播放中$'))).to_be_visible()
                page.get_by_text(LABELS['testline'],exact=True).click()
                expect(page.get_by_role('button',name='投入模擬測試批次',exact=True)).to_be_disabled()
                assert not page.get_by_text(re.compile(r'^已釋出')).count()
                evidence=ROOT/'docs/evidence/three-mode';evidence.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(evidence/'MODE_B_UNAVAILABLE.png'),full_page=True)
                page.wait_for_timeout(1200)
                page.get_by_text(LABELS['analysis'],exact=True).click()
                expect(page.get_by_text(re.compile(r'^回放時間：.* · 暫停$'))).to_be_visible()
                paused=progress.inner_text();page.wait_for_timeout(1200)
                assert progress.inner_text()==paused and '事件群 0／9' not in paused
                page.get_by_text(LABELS['production'],exact=True).click()
                expect(page.get_by_role('button',name='確認模擬線速補償',exact=True)).to_be_disabled()
                page.get_by_text(LABELS['analysis'],exact=True).click()
                expect(progress).to_have_text(paused)
                page.get_by_role('button',name='單步前進',exact=True).click()
                old_cursor=int(re.search(r'事件群 (\d+)',paused).group(1))
                expect(progress).to_contain_text(f'事件群 {old_cursor+1}／9')
                page.get_by_role('button',name='重新開始',exact=True).click()
                expect(progress).to_contain_text('事件群 0／9')
                page.get_by_role('combobox',name='回放速度',exact=True).click()
                page.get_by_role('option',name='4x',exact=True).click()
                page.get_by_role('button',name='播放／暫停',exact=True).click()
                expect(progress).to_contain_text('事件群 9／9',timeout=25000)
                expect(page.get_by_text(re.compile(r'^回放時間：.* · 完成$'))).to_be_visible()
                page.get_by_text(LABELS['testline'],exact=True).click()
                page.get_by_text(LABELS['analysis'],exact=True).click()
                expect(progress).to_contain_text('已釋出 15／15 列 · 事件群 9／9')
                assert not page.locator('[data-testid="stException"]').count()
                page.screenshot(path=str(evidence/'MODE_A_C7_COMPLETE.png'),full_page=True)
                (evidence/'BROWSER.json').write_text(json.dumps(dict(browser=browser.version,
                    timestamp=time.strftime('%Y-%m-%d %H:%M:%S %z'),source='Synthetic C7 fixture, not plant measurement',
                    final_progress=progress.inner_text(),checks=['play before navigation','leave pauses',
                        'return does not autoplay','cursor stable 1200ms','B and C unavailable',
                        'step after return','restart','4x automatic timer','end retains progress after navigation']),
                    ensure_ascii=False,indent=2),encoding='utf-8')
                browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
