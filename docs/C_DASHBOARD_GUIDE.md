# 成員 C 儀表板操作與開發指南

目前階段：**C3 快照 SPC 品質監控與實測警報**。C1＋C2 的載入、映射、篩選與資料檢查保留；C4～C9 尚未實作。以下來源欄位、子組與基準設定僅是 C 的可配置接點，不是 A／B 正式契約。

## 環境與啟動

本次驗證環境：Windows、Python **3.11.17**、Streamlit **1.66.1**、pytest **9.2.0**。`requirements.txt` 鎖定本階段 39 個直接／間接依賴，來源為 `requirements.in`；沒有安裝或訓練 Random Forest／SHAP 模型。

在專案根目錄執行下列 PowerShell 命令。使用 uv 建立 Python 3.11 環境，不依賴系統預設 Python；首次建立需要下載 Python／套件：

```powershell
Set-Location 'C:\python\FCCL final'
uv venv --python 3.11 .venv
uv pip sync --python .venv/Scripts/python.exe requirements.txt
```

已建立環境後直接啟動，不需要 Activate.ps1：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

瀏覽器開啟 `http://127.0.0.1:8501`，以 Ctrl+C 停止。若 8501 已使用，可在啟動命令加上 `--server.port=8502`，並改用該網址。本機檢查不代表部署；測試自啟的臨時 server 會自行停止。

## 畫面及目前可用範圍

| 區域 | C1～C3 已提供 | 尚未實作 |
|---|---|---|
| 主畫面 | FCCL 標題、寬版布局、C3 狀態提示與原四個 Tabs | 模型分析結果 |
| 側邊欄 | Mock／上傳載入、批次／時間篩選、來源／產品／材料及最新篩選列的環境值 | 正式規格交接與正式模型整合 |
| 上方監控 | 四連續目標最新組實測均值、全目標實測 SPC Alarm／限制 | 回放控制停用，外觀預測風險與模型 Alarm 未實作 |
| SPC Tab | X-bar／原始點、CL／UCL／LCL、逐目標適用性、子組及事件追溯 | 正式產線 SPC 適用性與回放 |
| What-if Tab | 固定區段資訊位置、參數比較與具體建議區、停用解鎖按鈕 | 滑桿、解鎖及比較邏輯待 C4；預測／建議待 C5 |
| AI 圖表 Tab | Heatmap、SHAP Summary Plot、SHAP Dependence Plot 三個占位區 | 沒有相關係數／SHAP／模型解釋結果 |
| 資料檢查 Tab | 原來源、預覽、驗證問題與候選輸入完整度；SPC 判定另在 SPC Tab | 正式品質允收與模型判定 |

上方四連續指標標明「實測子組平均」及時間；最新組無效時為「—」，不拿較早有效組冒充最新。外觀風險仍為「—」，不是零風險。側欄環境值沿用最新篩選有效識別列，缺值不補。AI Alarm 區只顯示實測 SPC 事件及限制，模型未接入仍有提示；目前沒有預測或具體調參建議。

## 載入、映射與篩選

1. 選「C 專用 Mock」，選擇情境後按「載入 Mock 資料」；來源／示範設定清楚標為非真實產線。完整情境見 [fixture 說明](../tests/fixtures/c_mock/README.md)。C3 另讀獨立歷史，只有通過適用性與穩定性才建立固定界限。
2. 或選「上傳 CSV」，選取 UTF-8／UTF-8 BOM CSV，確認映射後按「載入上傳 CSV」。只改來源選項／檔案但未按載入，不覆蓋已載入資料。上傳資料不自動套用 Mock 示範品質數值。
3. 側欄可選批號及含起訖的時間範圍（Asia/Taipei）；資料預覽、材料位置及環境值隨篩選更新。交集為空會顯示無資料，不補造列。試片的區段長度不累加成總產量。
4. 資料檢查顯示正規化預覽（前 200 列）、整份匯入的問題及原始值；篩選和輸入完整度使用完整篩選資料，不只預覽。來源列號與本地樣本 ID 保留排序前追溯。

預設來源配置明確採 [schema.py](../c_dashboard/data/schema.py) 的 C 欄名與單位：例如 timestamp、product_batch、length_m、ambient_temp_c、ambient_rh_pct、line_speed_m_min 及原 SKILL.md 的製程／五個品質欄位。若來源不同，請在映射展開區提供 JSON，例如：

```json
{
  "name": "來源示範映射",
  "version": "mapping-v1",
  "timezone": "Asia/Taipei",
  "columns": {
    "timestamp": {"column": "時間"},
    "product_batch": {"column": "批號"},
    "line_speed_m_min": {"column": "速度", "unit": "mm/s"},
    "ambient_temp_c": {"column": "溫度", "unit": "°F"}
  }
}
```

未列出的欄位仍用明確的 C 標準名稱／單位；改名的數值欄必須提供來源單位。支援同單位及 °F→°C、mm→m、mm/s 或 m/s→m/min、kPa→MPa、s↔min、N/cm→N/mm、fraction→%／%RH、cP→mPa·s 等明確轉換；不支援的單位要回報，不猜測。未帶時區的時間只有在映射明確提供 timezone 時才本地化。

缺 timestamp／product_batch 或沒有有效識別列時，載入不生效，上一份有效資料與篩選仍保留，錯誤另標其來源。缺製程／品質欄位不必讓所有資料檢視停用：報告用途缺欄，僅顯示有資料的欄位。缺品質欄不建立假的目標欄；現有欄位的壞值／缺值在正規化資料中為缺值，並保留原始值及明確問題紀錄。

主要問題代碼：CSV_PARSE、FILE_TYPE、MAPPING_CONFIG／MAPPING_COLLISION、MISSING_COLUMN、INVALID_TIME／INVALID_AVAILABILITY、INVALID_NUMBER、OUT_OF_RANGE、MISSING_VALUE／MISSING_ID、DUPLICATE_RECORD、UNIT_MISMATCH、NO_VALID_ROWS。COLUMN_MAPPED、UNIT_CONVERTED、TIME_SORTED、HEADER_NORMALIZED、VALUE_TRIMMED 為可追溯處理資訊；LOCAL_SEGMENT_ID／AVAILABILITY_ASSUMED 表示本地識別／時間假設，正式語意仍待整合。

重複紀錄保留供檢查，不能當額外有效樣本；沒有原生材料區段時使用來源列本地 ID，不能宣稱已完成實體區段對齊。子組大小／識別只供 C fixtures；無子組來源仍可檢視，不將連續五列湊成組。功能輸入完整度只代表 C 預設輸入候選，不代表 SPC 合理性、品質合格、模型已執行或 B 的正式特徵清單。

## 模組與狀態邊界

- [app.py](../app.py)：只設定頁面並組合入口。
- [state.py](../c_dashboard/state.py)：`fccl_workspace` 保存資料來源、原始 CSV 接點、批號、回放、模型版本及 What-if；重跑只在狀態不存在時建立，不覆寫已有工作。
- [data/loader.py](../c_dashboard/data/loader.py)、[data/schema.py](../c_dashboard/data/schema.py)：CSV 解析、顯式映射／單位、驗證、穩定識別、篩選及用途輸入檢查；不計算 SPC 或預測。
- [data/session.py](../c_dashboard/data/session.py)、[data/fixtures.py](../c_dashboard/data/fixtures.py)：載入結果的原子提交、來源／篩選狀態重設及讀取 C fixtures。
- [ui/data_inspection.py](../c_dashboard/ui/data_inspection.py)：資料預覽、問題清單與輸入完整度呈現。
- [adapters/base.py](../c_dashboard/adapters/base.py)：C 內部型別與 Protocol，提供能力、識別、預測結果的接點，並非要求 B 採用的新 API。
- [adapters/unavailable.py](../c_dashboard/adapters/unavailable.py)：C1 使用的未接入 Adapter；不讀模型、不做公式預測、不回傳虛構值。它不是 C5 的確定性 Mock Adapter。
- [ui/layout.py](../c_dashboard/ui/layout.py)、[ui/sidebar.py](../c_dashboard/ui/sidebar.py)、[ui/overview.py](../c_dashboard/ui/overview.py)、[ui/tabs.py](../c_dashboard/ui/tabs.py)：分別負責組合、側欄、監控區、四 Tabs。

原始區段快照以不可變型別保存；候選參數使用獨立容器，其他 Session 不共用。成功切換不同內容／來源／映射版本時重設相依游標、選取、參數及解鎖；篩選改變也清除舊情境。相同來源重新載入或一般分頁／重跑保留工作；失敗匯入不改有效資料。C2 尚未實作 What-if 選取或回放狀態機，重設接點不代表這些功能完成。

原生 Tabs 可切換；AppTest 已驗證原生上傳、Mock 載入、篩選及分頁／重跑的狀態。這不是 C8 的真實瀏覽器或定時回放整合驗收；C2 公開介面仍只有快照資料工作，不提供回放。重新整理瀏覽器造成新 Session 的持久化不在本階段實作範圍。

## C1／C2 驗證方式

```powershell
.\.venv\Scripts\python.exe -X utf8 -m compileall -q app.py c_dashboard tests
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

C1＋C2 原有 40 個測試持續回歸；C3 測試另見 [C3 驗收矩陣](C3_SPC_ACCEPTANCE.md)。原有測試範圍：

- `tests/test_c1_state.py`：重跑保留、Session 隔離、不可變快照、不可用 Adapter 與 C 內部替身接點。
- `tests/test_c1_ui.py`：四 Tabs／原功能占位／無資料狀態、分頁狀態及重跑保留。沒有把替身資料當已驗證 CSV。
- `tests/test_c1_startup.py`：不依賴 A／B 的模組匯入；以本機臨時連接埠啟動 Streamlit，驗證健康端點及首頁 HTTP 200，結束後停止該子程序。
- `tests/test_c2_fixtures.py`：fixture 位元組重現、歷史時間與獨立樣本、配置化子組及情境值。
- `tests/test_c2_loader.py`：CSV／編碼／欄位／時間／數值／重複／映射／缺值與用途輸入完整度。
- `tests/test_c2_session.py`：載入成功／失敗／相同來源／映射切換及篩選狀態，原始資料不被預覽修改。
- `tests/test_c2_ui.py`：以 Streamlit 原生 AppTest file_uploader 上傳 CSV，驗證 Mock／上傳／映射／錯誤／篩選與來源切換。

AppTest 是後端模擬 UI；HTTP 首頁檢查是啟動檢查，均不等於 C8 真實瀏覽器／C7 timer 或正式模型驗收。C3 以圖表 payload、事件識別及原生紅色訊息驗證快照呈現。

## 成熟度與下一階段

資料來源：C 專用 Mock 或上傳；上傳不等於正式產線。C3 快照 SPC／實測 Alarm 已提供；公式 Mock、模型預測、What-if、Heatmap／SHAP 及回放仍未實作；正式模型與真正 SHAP 未整合，真實產線未驗證，沒有機台控制。

本輪 C3 Apply 完成後停止，不自動 Archive 或進入 C4＋C5。C 的測試假設不要求 A／B 採用，正式品質及交接仍依 [TEAM_CHANGE_PROPOSALS.md](TEAM_CHANGE_PROPOSALS.md) 記錄；下方歷史管理事件保留當時狀態，現況以上述 C3 成熟度為準。

## Change 範圍調整（2026-11-01）

`fccl-streamlit-dashboard` 現僅對應已驗收的 C1＋C2（8／8）；全案仍是原 8／39、31 項未完成。這是管理拆分，程式／測試／fixtures 與啟動操作不變。本次尚未 Archive 或同步正式 specs。

後續順序為 C3 SPC、C4＋C5 What-if／Mock AI、C6 圖表、C7 回放、C8 整體交付、C9 正式整合；六案尚未建立 active Change。完整原始規劃、28 需求／47 情境／39 任務歸屬見 [CHANGE_ROADMAP.md](CHANGE_ROADMAP.md)，本階段測試對照見 [C_BASE_ACCEPTANCE.md](C_BASE_ACCEPTANCE.md)。各案須自帶測試／文件並獨立驗收，C9 交接等待不阻擋前案歸檔。


## 基礎 Change 已歸檔（2026-11-01）

C1＋C2 的 [fccl-streamlit-dashboard](../openspec/changes/archive/2026-11-01-fccl-streamlit-dashboard/proposal.md) 已於 2026-11-01 22:28:30 +08:00 歸檔，八項任務完成，兩份已交付基礎主規格已同步。原啟動指令與程式不變；上節尚未歸檔為拆分當時狀態。

C3～C9 仍由 Roadmap／六份 change-plans／完整原始快照保留，尚未建立下一個正式 Change。本次沒有 Propose／Apply、Python 改動或 Git Commit／Push；紀錄見 DEV-20261101-015。

## C3 的 SPC 適用性

C3 在 CSV 預覽之外獨立檢查合理子組；C2 的「功能輸入完整度」仍是載入檢查，不是統計判定。只有明確 C 取樣設定、同次獨立試片、完整 n 與有效品質目標才能形成均值；一個目標缺量測不讓其他完整目標停用。部分組、重複或跨條件組不靠刪列湊組，並中斷連續規則。

未知上傳來源仍可載入、映射、篩選及預覽，不因欄名相同就套用 C Mock 基準。沒有取樣證據時 SPC 顯示無法判定。詳見 [C3 SPC 設定與問題碼](C3_SPC_TECHNICAL.md)；C Mock 設定不是 A 的正式 CSV 契約。

### C3 操作及警報判讀

載入正常 Mock 後到 SPC Tab，選四個連續品質目標；灰點為原始量測、藍線為完整子組均值，CL／UCL／LCL 固定。切換「單點品質偏移」「上升趨勢」「同側偏移」可查看紅色事件；主畫面與 SPC Tab 共用同一結果，切目標不會遮蔽其他目標警報。

側欄批號／時間篩選會重算範圍內事件，但不重新估計歷史基準。最新組無效顯示無法判定；較早事件另標為範圍內歷史異常。未出現事件只表示未偵測啟用的 SPC 規則，不代表產品符合允收。外觀只顯示實測有效標籤／NG 計數，不建立 X-bar 或模型風險。

「SPC 基準來源與適用條件」「子組完整性與原始列追溯」「SPC 事件識別與規則序列」可展開查證。基準無效可看原始點，沒有完整組時不畫有效控制線；原因不因模型未接入而被遮蔽。正式允收規格與管制界限不同，不以原始試片點越過均值界限當作單件不合格。


## C3 已歸檔（2026-11-01）

[fccl-spc-monitoring](../openspec/changes/archive/2026-11-01-fccl-spc-monitoring/proposal.md) 已於 2026-11-01 23:22:59 +08:00 歸檔。三份主規格已完成新增／修改合併，功能及啟動指令不變；本次沒有 Python 改動或新功能。C4～C9 的五份後續計畫仍未實作，沒有自動建立下一個 Change；詳細進度見 [Roadmap](CHANGE_ROADMAP.md) 與 DEV-20261101-018。

