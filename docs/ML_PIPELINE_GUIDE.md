# FCCL Synthetic ML Pipeline Guide

本流程只使用 `generated_data/v2/` 合成資料驗證 canonical dataset、模型訓練、正式 Adapter 與 SHAP 串接。結果不是產線效能、因果改善或設備控制依據。

## 環境邊界

- `requirements-ml.in` 是可讀依賴來源，`requirements-ml.txt` 是 Python 3.11／3.12 的固定版本鎖檔。
- ML 環境與 `requirements-c.*` 分離；C 公式 Mock 不需要載入 scikit-learn、joblib 或 SHAP。
- 七份來源表與 `raw data/` 永遠唯讀。canonical projection 寫入 `generated_data/model_dataset_v2/`，模型寫入 `artifacts/synthetic_v2/`。
- 只有專案可信 artifact 目錄且 manifest/hash 驗證成功的 joblib 可載入；CSV 上傳不是模型上傳入口。

## 執行順序

```powershell
python -m venv .venv-ml
.venv-ml\Scripts\python.exe -m pip install -r requirements-ml-app.in
.venv-ml\Scripts\python.exe -m fccl_ml.cli build --profile synthetic-ground-truth-v2
.venv-ml\Scripts\python.exe -m fccl_ml.cli train --profile synthetic-ground-truth-v2
streamlit run app.py
```

## 模型來源、回退與停用

1. 先在資料來源選擇 `Canonical Synthetic projection`，再選取與資料 manifest 相同的 profile。
2. 在模型來源選擇 `Synthetic 正式 artifact`。系統只會載入專案內 registry 指向、且 manifest 與 hash 驗證通過的模型；不接受上傳的 joblib。
3. 若單一目標 artifact 缺失、hash 不符、版本或資料契約不相容，該目標會標成不可用；不會以 0、舊結果或 Mock 冒充正式推論。資料預覽與可用的 SPC 功能仍可使用。
4. 需要明確回退時，手動切換為 `C 公式 Mock`；這是公式示範來源，不是正式模型，也不是正式模型失敗時的自動 fallback。
5. 需要完全停用推論時，選擇 `未接入`。切換來源會清除目前監控、What-if 與解釋快取，避免跨來源共用結果。

What-if 僅在模型訓練支援範圍及介面版本化調整範圍內推論；超出範圍會拒絕外推。畫面顯示五項品質目標、規格狀態、外觀 NG 風險與警報，不提供「預測良率」。所有 Synthetic What-if 結果只代表關聯模型推論，不是因果改善保證。

## SHAP 解釋來源與限制

- `Synthetic 正式 artifact` 使用已通過 manifest／hash 驗證的 Random Forest Champion、固定 train 背景資料與 Tree SHAP。畫面會顯示模型版本、前處理版本、輸出尺度、背景 hash 身分及請求 key。
- 每次解釋最多使用 200 筆合格可追溯樣本；超過時按載入後穩定順序取前 200 筆。Provider 只讀取各目標 artifact 的 `background.csv`，不回讀七表或全域 canonical CSV。
- 四個連續目標以原迴歸輸出單位呈現；外觀模型明確依 `classes_` 與 manifest 找標籤 `1`，輸出尺度標示為 probability，不假設固定欄位位置。
- `render-test` 只用於介面測試，畫面標示「介面測試資料，非真正 SHAP」；`C 公式 Mock` 沒有 SHAP，會顯示不可用，不產生假解釋。
- SHAP 說明模型在合成資料上的關聯貢獻，不代表因果效果、製程調整保證或真實產線驗證。

正式模型來源、C 公式 Mock、未接入是三種獨立狀態。正式 artifact 失敗時不會靜默改用 Mock；使用者必須在畫面主動切換。回退方式是選擇 C 公式 Mock 或未接入，或將 registry 指回先前已驗證 Champion。

在側欄先載入與模型相同 profile 的 `Canonical Synthetic projection`，再選擇 `Synthetic 正式 artifact`。若使用一般上傳 CSV、C Mock、不同 profile、不同 dataset version 或超出訓練支援範圍，正式模型會逐目標顯示不可用原因；資料預覽與有效 SPC 不會因此停用。

