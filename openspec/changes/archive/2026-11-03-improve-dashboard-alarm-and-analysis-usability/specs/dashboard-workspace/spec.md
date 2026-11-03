# Spec Delta

## ADDED Requirements

### Requirement: WS-07 可操作的資料與分析就緒導引

系統 SHALL 明確區分資料來源已選取、資料已成功載入、模型已就緒及 What-if／Heatmap／SHAP 各自可用狀態；不可用功能 MUST 顯示阻塞原因與可執行下一步。主要功能分頁 MUST 位於固定且可尋得的位置，不得被歷史 Alarm 明細推離主要操作區。

#### Scenario: 只選來源尚未載入
- **WHEN** 使用者選取 Canonical Synthetic projection 但尚未執行或完成載入
- **THEN** 畫面顯示「已選取、尚未載入」，What-if、Heatmap 與 SHAP 分別提示按下 Canonical 載入動作，不以暗色控制項或「尚未載入 CSV」模糊帶過

#### Scenario: 資料已載入但仍選 Mock
- **WHEN** Canonical 資料已成功載入且模型來源仍為 C 公式 Mock
- **THEN** 就緒摘要顯示資料與 Heatmap 可用、Mock What-if 可用及真正 SHAP 不可用，並提示使用者若要正式 Synthetic SHAP 須主動選擇 Synthetic 正式 artifact

#### Scenario: Canonical 與正式模型均就緒
- **WHEN** Canonical 資料、Synthetic 正式 artifact 及相容 manifest 均通過驗證
- **THEN** 就緒摘要顯示 What-if、Heatmap 與 SHAP 可用，三個功能入口保持可見且來源／版本一致

#### Scenario: 大量歷史 Alarm 存在
- **WHEN** 目前範圍包含大量 SPC 原始事件或事件群
- **THEN** Overview 僅顯示有界摘要，SPC／What-if／AI 圖表／資料檢查分頁仍位於主要工作區可直接操作，不需捲過全部歷史事件

#### Scenario: 停用元件與計算狀態
- **WHEN** 功能因缺資料、缺模型、無能力或正在計算而不可操作
- **THEN** 其區域以正常可讀對比顯示狀態、原因與下一步，停用外觀不得被誤認為已完成但沒有結果
