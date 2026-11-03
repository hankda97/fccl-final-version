# Design：七表整合

## D1：來源層與模型層

七份 CSV 為不可覆寫的來源層；後續 `build_model_dataset` 產生 canonical model table。C1～C3 仍可使用既有單 CSV／Mock，不將七表直接要求施加於歷史驗收。

## D2：對齊錨點

- inspection-supervised 模式以有效品質檢驗事件作錨點。
- synthetic 模式以最終 lamination canonical segment 作錨點。
- 對齊鍵為 `root_roll_id` 與材料 MD 區間。
- 區間採 `[start, end)`；最後區段可含卷尾。
- v2 預設 coverage threshold 為 0.98，與 `metadata.json` 及 `SKILL.md` 一致；實際值寫入 integration manifest。其他資料版本若調整門檻，必須由該版本 metadata 與 manifest 明確宣告，不沿用隱含預設。

## D3：欄位聚合

數值製程特徵依材料重疊長度加權平均；類別欄位必須唯一。每列保留三站來源 segment IDs、coverage、mapping confidence、feature timestamp 與 label timestamp，這些追溯欄位預設不作模型特徵。

## D4：正式標籤

| canonical target | inspection 欄位 | 適用來源 |
|---|---|---|
| peel_strength_n_mm | peel_strength_n_per_mm | 5_minute_lab_sample、lamination |
| dimensional_stability_md_pct | md_dimensional_change_pct | 5_minute_lab_sample、lamination |
| dimensional_stability_td_pct | td_dimensional_change_pct | 5_minute_lab_sample、lamination |
| heat_resistance_c | heat_resistance_c | 5_minute_lab_sample、lamination |
| appearance_ng | appearance_ng_flag | online、lamination |

synthetic ground truth 可提供完整目標供演算法開發，但 manifest 必須標示來源，不能與 inspection 結果混稱。

## D5：規格與外觀

規格 pivot 使用 `spec_<canonical_target>_<attribute>` 命名。`appearance_ng` 的產品允收為 0；預測 NG 機率門檻屬模型／Alarm 設定，不存成產品品質規格。

## D6：重複與 availability

預定技術 replicate 的連續值使用中位數並記錄 count／std／min／max；重測不覆蓋初次有效結果。來源 metadata 不足時拒絕自動選取。availability 由非空、型別、單位、測試方法、有效性、粒度、對齊及衝突共同決定。
