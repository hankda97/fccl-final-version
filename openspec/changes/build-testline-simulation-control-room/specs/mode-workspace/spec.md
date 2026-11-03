# Spec Delta

## ADDED Requirements

### Requirement: MW-06 單一測試線控制台入口

系統 SHALL 以 Mode B「測試線模擬控制台」作為唯一一般使用者入口，不顯示 A／B／C 模式選擇；原 A 的模型、What-if、Heatmap、資料與 SPC 服務可由新控制台重用，但其狀態與 Run MUST 明確隔離，C 能力不得出現在一般導覽。

#### Scenario: 開啟應用
- **WHEN** 一般使用者啟動 Streamlit 應用
- **THEN** 直接進入測試線控制台，不需選模式且不顯示未交付 A／C 入口

#### Scenario: 重用既有服務
- **WHEN** 控制台呼叫既有正式模型、What-if 或 Heatmap 能力
- **THEN** 結果標示目前 Run、v3 資料與模型來源，不讀寫舊 A 工作階段或把 v2／C Mock 靜默補入

#### Scenario: 舊 artifact 保留
- **WHEN** 新控制台交付
- **THEN** v2 模型及舊程式可保留供回退與測試，但不在正常使用路徑宣稱為目前控制台結果

## REMOVED Requirements

### Requirement: MW-01 三模式定位與成熟度導航

**Reason**: 使用者已確認正式產品面只需要 Mode B；三模式導覽增加認知與狀態混用風險。

**Migration**: 以 MW-06 單一測試線控制台入口取代；可重用的 A 服務保留為內部元件，C 不進一般導覽。
