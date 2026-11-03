# Gate 0 驗收證據

時間：2026-11-03 06:45:19 +08:00 (Asia/Taipei)

## 啟動與瀏覽器驗收

```powershell
.\.venv-ml\Scripts\python.exe -m streamlit run testline_prototype.py --server.headless true --server.port 8510 --browser.gatherUsageStats false
Invoke-WebRequest -UseBasicParsing http://localhost:8510/_stcore/health
```

- Health：HTTP 200，內容 `ok`。
- Playwright Chromium：1600 × 1000，成功找到「3L FCCL 測試線模擬控制台」「Gate 0 靜態 UI 原型」與「生產控制台」。
- 截圖：[testline-control-room-prototype.png](testline-control-room-prototype.png)。
- 初次瀏覽器驗收因本機缺少 Playwright Chromium executable 失敗；執行 `.\.venv-ml\Scripts\python.exe -m playwright install chromium` 後重測通過。這只安裝測試瀏覽器，不是應用執行依賴。

## 自動測試

```powershell
.\.venv-ml\Scripts\python.exe -m pytest -q tests/test_testline_prototype_ui.py
```

結果：`6 passed`。

```powershell
.\.venv-ml\Scripts\python.exe -m pytest -q tests/test_testline_prototype_ui.py tests/test_c1_ui.py tests/test_mode_workspace_ui.py
```

結果：`14 passed`。

```powershell
openspec validate build-testline-simulation-control-room --strict
git diff --check
```

- OpenSpec：valid。
- Git diff：無內容錯誤；只有既有 `TEAM_CHANGE_PROPOSALS.md` CRLF→LF 提示。
- `app.py`、v2 CSV 及模型 artifact 未由 Gate 0 修改；Gate 0 使用獨立 `testline_prototype.py`。

## 限制

Gate 0 僅為可操作靜態 fixture。尚未接入模擬時鐘、Synthetic v3、正式模型、Run Store 或設備。

## 06:55 淺色主題驗收修正

使用者回報深色 host theme 造成導航白字、配方表與參數區黑底。原型現已在自身範圍強制採淺色元件與深色文字，並將固定資料表改為可預測的淺色 HTML table，不修改全專案 Streamlit theme。

- `testline-control-room-light-theme.png`：以瀏覽器 `color_scheme=dark` 啟動，導航文字實測 `rgb(21, 34, 56)`、背景 `rgb(255, 255, 255)`。
- `testline-parameter-panel-light-theme.png`：參數 input 文字實測 `rgb(21, 34, 56)`、背景 `rgb(255, 255, 255)`。
- 專屬 AppTest 重跑：`6 passed`。

## 07:03 全頁配色與 SPC 全訊號修正

- 首頁與詳細頁的所有 SPC 圖改為固定白底、深色座標、淺灰格線、藍色 actual、藍色中心／目標線及紅色上下限／警戒線。
- SPC 詳細頁移除黑色下拉選單，改為同頁顯示乾膠厚度、熟化溫度、排風量、線速、壓合壓力共 5 張圖；首頁維持 3 張摘要圖。
- Tabs、提示框、按鈕、技術明細、固定 Heatmap 與 Run table 皆加入淺色樣式。
- `testline-spc-all-signals-light-theme.png`：深色瀏覽器偏好下，實測同頁 5 張可見圖。
- `testline-whatif-light-theme.png`、`testline-run-record-light-theme.png`：What-if 與 Run 頁淺色驗收；Run table cell 背景為 `rgb(255, 255, 255)`。
- 專屬＋既有 UI 回歸：`14 passed`。

## 07:12 面板停止與紅色 Error 修復

- 根因：使用者以系統 Streamlit 1.36.0 執行，原型曾使用 1.66.1 新增的 `width="stretch"` 參數；1.36 渲染到表單時拋出 `TypeError`。Streamlit 熱更新未重新載入 imported UI module，使 traceback 行號一度指向已變動的 radio 行。
- 修正：移除跨版本不相容的 `width`／寬度參數，寬度改由既有版面與 CSS 控制；必須完整停止舊 server 後再啟動。
- 系統 Streamlit 1.36 瀏覽器驗證：四頁連續切換無 `stException`；生產控制台 3 圖、SPC 詳細頁 5 圖、What-if／Run 0 圖均符合預期；參數表單提交及 What-if 計算成功。
- `.venv-ml` Streamlit 1.66 AppTest 與既有 UI 回歸：`14 passed`。
- `system-streamlit-136-fixed.png` 保存 1.36 修復後畫面；`system-streamlit-136-error.png` 保存修復前相容性問題證據。

## 07:18 緊湊參數面板與導航停滯修正

- 完全移除 `st.radio` 頁面導航，改為四個固定按鈕及明確 session page state；使用者截圖中的 radio TypeError 執行路徑已不存在。
- 入口檔每次 Streamlit rerun 都重新載入 Gate 0 UI module，避免 imported module 保留舊 callback／函式。
- 主要參數改為真正的逐列三欄配置：第一列線速／塗佈間隙／熟化溫度，第二列排風量／熟化時間／壓合溫度，第三列壓合壓力；CSS 在 800px 視窗仍維持三欄，避免長直向頁面與欄序錯亂。
- `testline-compact-parameter-grid-800px.png`：800px 視窗下前三項與次三項各自同列。
- `testline-spc-navigation-fixed.png`：按鈕進入 SPC 後同頁 5 圖且無 exception。
- 系統 Streamlit 1.36：四頁往返、參數與圖表檢查通過；`.venv-ml` 回歸 `14 passed`。

## 07:36 追蹤區段、五圖總覽與警報流程修正

- 產線示意改為同時顯示塗佈 SEG-019、熟化 SEG-018、壓合 SEG-017、完成 SEG-016；熟化藍框明示「目前追蹤區段」，不再暗示其他站沒有材料。
- 完成材料品質狀態改用語意色 chip：符合規格／高於下限為綠色，並預留黃色接近界限、紅色超規、灰色不可判定。
- 生產控制台改為全部 5 張小型 SPC 圖，排列為 3＋2；SPC 詳細頁保留完整 5 圖與事件資訊。
- 首頁只保留「異常警報摘要」及前往明細按鈕；SPC 詳細頁新增「異常警報中心」，分開 SPC 製程警報與品質預測警示，並可返回生產控制台調整參數。
- Playwright 驗證首頁 5 圖、品質綠色 `rgb(13, 107, 71)`、警報明細往返與零 exception；自動測試 `15 passed`。
