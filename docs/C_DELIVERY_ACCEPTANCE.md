# 成員 C 第一批交付驗收摘要

本批為已完成 C1～C7 及三模式導航／隔離的選擇性交付，非 C8／C9 或完整模擬器驗收。

| 能力 | 已交付範圍與限制 |
|---|---|
| 資料與介面 | CSV／Mock、映射、驗證、篩選、四 Tabs、Session State；正式七表整合未交付 |
| SPC | 合理子組 C Mock、固定歷史基準、X-bar、超界／六點趨勢／九點同側、SPC Alarm；不強加 A 取樣契約 |
| What-if／AI | 固定區段、線速及進階解鎖、確定性公式 Mock、五目標比較／風險／建議；非正式 B 模型或因果保證 |
| 圖表 | Pearson Heatmap、Summary／Dependence 呈現接點與來源／manifest 驗證；真正 SHAP 計算仍待 C9 |
| C7 | 單一游標、可信逐欄位／目標可得時間、播放控制、未來資料防護、情境與圖表失效管理 |
| 三模式 | A 核心保留、B／C unavailable、獨立狀態／run／事件／基準／快取、epoch 拒收晚到回應；無完整 B／C 模擬器 |

原始 Roadmap **29／39**；三模式擴充 **20／20、28／28 情境**，分開計數。原 C8／C9 共十項未完成。

來源專案先前完整驗收為 pytest 296、AppTest 43、Chrome 2（後兩者含於總數）。本次隔離整合的實際重測結果另列根目錄 `INTEGRATION_TEST_REPORT.md`；不得以歷史結果代替此次結果，也不宣稱真實產線已驗證。

六個完整 Archive：

- `2026-11-01-fccl-streamlit-dashboard`
- `2026-11-01-fccl-spc-monitoring`
- `2026-11-02-fccl-what-if-mock-ai`
- `2026-11-02-fccl-quality-visualization`
- `2026-11-02-fccl-csv-replay`
- `2026-11-02-fccl-three-mode-workspace`

所有 Python、fixtures、主規格及 Archive 由已完成的 C 來源逐檔加入；不覆蓋組長既有四十個追蹤檔案。共用規範及三份日誌維持遠端版本，不將兩套相同 ADR／DEV ID 合併成同一事件。原始七表唯讀；完整 B／C 與正式模型介接不因交付 Git 檔案而變成已完成。

本批只做 Dry-run。候選清單、每檔 SHA-256、受保護檔案、排除項與待確認事項見根目錄 `GITHUB_C_DELIVERY_MANIFEST.md`／`.json`。三份根目錄報告是本機審閱產物，不自動納入首批交付；沒有 Git add／Commit／Push。

Archive 中未加前綴的 ADR／DEV 引用屬原始 `C-local` 命名空間，不可解讀成遠端共用日誌中相同編號。原 C 日誌仍保留在來源專案，本批沒有冒充已移轉全文；後續如需集中查閱，應另建帶來源的追加式索引，不覆蓋組長原有紀錄。
