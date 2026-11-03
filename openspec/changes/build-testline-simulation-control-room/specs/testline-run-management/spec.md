# Spec Delta

## Purpose

定義每次本機測試線 Run 的隔離儲存、checkpoint、完成與中斷生命週期，使模擬過程可追溯、可檢視且不會自動污染正式訓練資料或版本控制。

## ADDED Requirements

### Requirement: TRM-01 Run 隔離目錄與檔案契約

每個 Run MUST 儲存在 `runtime_data/testline_runs/<run_id>/`，並包含 manifest JSON 與 process signals、material segments、parameter events、SPC events、quality predictions 五類 CSV；不同 Run 不得共用可變檔案。

#### Scenario: 建立新 Run
- **WHEN** 使用者開始一個新 Run
- **THEN** 系統建立唯一 run_id 與隔離目錄，manifest 記錄產品、配方、版本、seed、情境、開始時間及檔案狀態

#### Scenario: Git 邊界
- **WHEN** Run 產生 checkpoint 或完成檔案
- **THEN** runtime_data 保持於版本控制排除範圍，不改寫 raw data、generated_data 或模型 artifact

### Requirement: TRM-02 記憶體執行與週期 checkpoint

運轉中的 Run SHALL 以記憶體狀態服務 UI，並每 60 模擬秒建立一致 checkpoint；checkpoint MUST 只包含已提交 tick，且重複寫入不得產生重複列。

#### Scenario: 正常 checkpoint
- **WHEN** Run 到達下一個 60 模擬秒邊界
- **THEN** 五類資料與 manifest 的 checkpoint 截止一致，已寫序號唯一且可由檔案重建該截止的檢視狀態

#### Scenario: checkpoint 寫入失敗
- **WHEN** 任一檔案無法安全寫入
- **THEN** Run 顯示儲存錯誤並暫停或停止後續提交，不把部分 checkpoint 標為完整

### Requirement: TRM-03 完成、中斷與唯讀檢視

正常停止 SHALL 完整落盤並記錄每個輸出 hash；非正常中斷的 Run MUST 標示 interrupted 且可唯讀檢視已完成 checkpoint，初版不得提供中斷續跑。

#### Scenario: 正常完成
- **WHEN** 使用者停止 Run 且最終寫入成功
- **THEN** manifest 標示 completed、結束時間、列數與 hash，Run 紀錄可重開檢視

#### Scenario: 發現未完成 Run
- **WHEN** 應用啟動時找到沒有完成標記但有有效 checkpoint 的 Run
- **THEN** 系統將其標示 interrupted 並允許唯讀檢視，不從最後 tick 繼續執行

### Requirement: TRM-04 訓練資料隔離

任何 Run 資料 MUST NOT 自動加入模型訓練、baseline 或正式 synthetic reference；納入後續改善循環前 SHALL 經人工審查與新的 OpenSpec 變更或既定升版流程。

#### Scenario: Run 完成
- **WHEN** Run 變為 completed
- **THEN** 系統只更新 Run 紀錄，不觸發模型訓練、模型升版、baseline 重估或 generated_data 寫入

#### Scenario: 使用者下載或檢視
- **WHEN** 使用者檢視或匯出某 Run
- **THEN** 匯出內容保留 Synthetic／Mock、產品、配方、版本及非真實產線限制，不改變其訓練資格
