# Tasks

## 1. 契約校正與 ML 環境

- [x] 1.1 將既有七表 integration design 的 v2 coverage 預設與 metadata／SKILL 校正為 0.98，並以 OpenSpec validate 與文件比對確認無 0.98／0.99 雙重契約
- [x] 1.2 建立隔離的 ML 依賴來源與鎖檔，納入相容版本的 scikit-learn、joblib、shap 及測試工具，並在全新 venv 驗證安裝與 import 成功
- [x] 1.3 建立 ML pipeline、設定與 artifact 目錄邊界，加入可信路徑及輸出路徑測試，確認不改寫 `generated_data/v2` 或 `raw data`
- [x] 1.4 更新本階段資料／模型來源與執行指南，明示 Synthetic 限制及 C Mock 隔離，並人工核對 AGENTS／SKILL／OpenSpec 狀態不再宣稱已完成或尚未授權的錯誤階段

## 2. Canonical model dataset

- [x] 2.1 實作七表與 metadata 的 schema、唯一鍵、外鍵、hash、時間、區間及版本驗證，並以有效 v2 與逐項破壞 fixture 測試結構化錯誤
- [x] 2.2 實作 synthetic profile 的 lamination 錨點與三站 `[start,end)` MD 重疊聚合，並以手算跨界案例驗證 coverage、加權值、來源 IDs 及 20,000 個唯一 `aligned_sample_id`
- [x] 2.3 實作 simulated-inspection profile 的區段錨點、規格有效期／pivot、逐目標 availability、外觀衝突與重測有效性選取，並以 valid／superseded／ambiguous fixtures 驗證 lineage 與排除 code
- [x] 2.4 建立五個逐目標 projection、lineage、排除摘要與 dataset manifest，並驗證 synthetic 與 inspection profile 不混列、不混分母且所有輸出可由來源 hash 追溯
- [x] 2.5 驗證 train／validation／test 為 120／40／40 個互斥完整卷、時間順序一致且任一卷跨 split 時必定失敗，不允許 random-row fallback
- [x] 2.6 建立 feature allowlist 與 leakage audit，使用目標、pass flag、spec、availability、識別及 drift 欄位的參數化測試確認全部被拒絕
- [x] 2.7 為 builder 提供可重跑 CLI／Python API 與資料字典，執行相同輸入兩次並比對 projection 結構、manifest、lineage 與 hash 一致

## 3. 逐目標模型訓練與評估

- [x] 3.1 實作只在 train 擬合的逐目標前處理與共同訓練設定，並以 validation／test 極端值 fixture 驗證不影響 train 統計量
- [x] 3.2 為四個迴歸目標建立 mean／linear 基準，為外觀建立 prevalence／Logistic 基準，並驗證五目標皆輸出可重現的 validation／test 基準 metrics
- [x] 3.3 為五目標訓練 Random Forest 初版 Champion，驗證固定 seed、輸入欄位順序、分類 `classes_` 含標籤 1 及批次預測索引保持
- [x] 3.4 為五目標訓練 HistGradientBoosting Challenger，使用與 RF 完全相同的 projection、split 與評估函式，並以比較測試確認沒有獨立重切資料
- [x] 3.5 實作迴歸 MAE／RMSE／R²及分類 PR-AUC／precision／recall／F1／confusion matrix／類別比例／校準評估，並驗證 split 與穩定／漂移 sidecar 分層不會進入模型特徵
- [x] 3.6 實作 validation 超參數／分類門檻選擇、Champion／Challenger 比較與升版拒絕理由，並以「只改善單一指標」案例驗證 RF 不被自動取代
- [x] 3.7 輸出每目標 bundle、registry、manifest、metrics、背景資料索引與 SHA-256，並以 JSON schema／必要欄位／相對路徑測試驗證 artifact 完整性
- [x] 3.8 驗證序列化前後預測一致、相同 seed 重跑的分割／設定／預測／指標在容差內一致，以及資料或設定 hash 改變時產生不同 model version
- [x] 3.9 實作可信 artifact loader，使用路徑穿越、UI 上傳、缺 manifest、hash 竄改及套件不相容案例驗證拒絕反序列化與安全降級
- [x] 3.10 產生 synthetic-ground-truth 與 simulated-inspection 分離的模型報告與限制說明，核對 UI 可選 registry 不將兩種來源混稱或混訓

## 4. 正式 Model Adapter 與 Streamlit 情境整合

- [x] 4.1 實作正式 Model Adapter，沿用既有 `describe/predict` 協定並提供版本化 manifest hook，以現有 C Adapter 測試加正式五目標 fixture 驗證相容性
- [x] 4.2 實作 canonical projection source profile 與模型相容性檢查，驗證 schema／feature order／單位／label／spec／dataset 不符時只停用受影響正式模型功能
- [x] 4.3 在 Streamlit 加入明確模型來源選擇與資源快取，驗證 Synthetic 正式 artifact、C 公式 Mock、未接入三種狀態不共享結果或錯誤標示
- [x] 4.4 將正式模型接入目前監控、固定區段 What-if 與預測 Alarm，使用支援範圍內／外候選測試驗證五目標差值、規格狀態、外觀風險、拒絕外推及不新增預測良率
- [x] 4.5 實作逐目標 artifact 缺失、hash 不符與推論錯誤的降級，驗證不以零、舊結果或 Mock 冒充正式預測，且有效 SPC／資料預覽保持可用
- [x] 4.6 更新模型操作與回退指南，依文件從乾淨啟動載入 registry、切換 Mock、停用正式來源，確認命令及畫面標示與實際行為一致

## 5. 正式 SHAP Provider

- [x] 5.1 實作從已驗證 Champion bundle 建立的 Tree SHAP Provider，使用固定 train 背景抽樣、樣本上限與 cache key，並驗證 Provider 不回讀全域 CSV
- [x] 5.2 對四個迴歸目標輸出與請求樣本／特徵對齊的 contributions／base values／單位／尺度，並以手算形狀與加總關係測試驗證 envelope
- [x] 5.3 對外觀模型依 manifest 與 `classes_` 選擇標籤 1，使用反轉類別順序 fixture 驗證不固定取第二類且 probability／raw margin／log-odds 標示正確
- [x] 5.4 接入既有 SHAP Summary／Dependence UI，使用模型／manifest／來源／選項切換與延遲舊回應測試驗證失效、錯誤隔離、重試及資源釋放
- [x] 5.5 更新 SHAP 操作與限制文件，人工核對正式解釋、render-test、公式 Mock 不可用三種來源在畫面及文件中可清楚區分

## 6. 端到端整合驗證

- [x] 6.1 從唯讀 v2 七表執行 builder → 五目標訓練 → artifact 載入 → Streamlit 推論／What-if／SHAP，保存實際命令、版本、耗時、metrics 與產物 hash 作驗證證據
- [x] 6.2 執行 ML 單元／整合測試及既有完整 C1～C7、回放、三模式回歸測試，確認正式模型新增功能沒有改變 Mock、SPC、回放或 workspace 隔離
- [x] 6.3 執行缺表、缺欄、錯誤單位、重測歧義、單一分類、artifact 竄改、模型部分缺失及 SHAP 失敗情境，確認結構化錯誤與逐目標降級符合 specs
- [x] 6.4 更新 OpenSpec tasks、開發／決策／團隊紀錄與已知限制，逐項連結實際測試證據並確認未驗證項目不標完成

## Workflow follow-up

- 所有 tasks 與驗證完成並經使用者審查後，再同步 delta specs 或 archive；本 Propose 不執行 archive。
- 真實產線資料接入、模型再訓練批准及設備控制須建立後續 Change，不由本 Synthetic pipeline 自動延伸。
