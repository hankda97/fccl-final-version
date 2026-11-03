"""Traditional-Chinese SPC reason presentation while preserving raw audit codes."""

REASON_LABELS = {
    "MISSING_SAMPLING_EVIDENCE": "缺少可驗證的取樣證據",
    "BASELINE_UNAVAILABLE": "無可用的穩定歷史基準",
    "UNSUPPORTED_SUBGROUP_SIZE": "不支援此子組大小",
    "INVALID_HISTORY_MINIMUM": "歷史子組最低數設定無效",
    "UNSUPPORTED_POLICY_VERSION": "不支援此 SPC 政策版本",
    "INVALID_CONDITIONS": "取樣條件設定無效",
    "INVALID_INTERVAL": "子組時間間隔設定無效",
    "INVALID_ENVIRONMENT_RANGE": "環境條件範圍無效",
    "INVALID_MONITORING_ORIGIN": "監控起點無效",
    "UNIT_MISMATCH": "品質單位不相容",
    "HISTORY_CONTENT_MISMATCH": "歷史內容與登錄指紋不符",
    "HISTORY_NOT_PRIOR": "歷史資料並非全部早於監控起點",
    "HISTORY_SAMPLE_OVERLAP": "歷史與監控樣本重疊",
    "INSUFFICIENT_HISTORY_GROUPS": "穩定歷史子組不足",
    "INVALID_HISTORY_GROUP": "歷史包含無效子組",
    "ZERO_HISTORY_VARIATION": "歷史組內變異為零",
    "UNSTABLE_HISTORY_RANGE": "歷史組內範圍不穩定",
    "UNSTABLE_HISTORY_MEAN": "歷史子組均值不穩定",
    "MISSING_GROUP_ID": "缺少子組識別",
    "INCOMPLETE_OR_OVERSIZED_GROUP": "子組不完整或超過設定大小",
    "MISSING_OR_DUPLICATE_SPECIMEN": "試片識別缺失或重複",
    "REUSED_SPECIMEN_IN_SOURCE": "同一試片被重複使用",
    "INVALID_IDENTITY": "資料識別無效",
    "DUPLICATE_RECORD": "資料包含重複紀錄",
    "LOCAL_SEGMENT_WITHOUT_SAMPLING_EVIDENCE": "區段缺少正式取樣證據",
    "INCOMPATIBLE_PRODUCT_ID": "產品不符合 SPC profile",
    "INCOMPATIBLE_RECIPE_ID": "配方不符合 SPC profile",
    "INCOMPATIBLE_SEGMENT_ID": "同一子組的取樣事件不一致",
    "INCONSISTENT_SAMPLING_TIME": "同一子組的取樣時間不一致",
    "INVALID_AVAILABILITY": "結果可得時間無效",
    "INCOMPATIBLE_CONDITIONS": "製程條件不符合 SPC profile",
    "MIXED_CONDITIONS": "同一子組混入不同製程條件",
    "ENVIRONMENT_OUTSIDE_PROFILE": "環境條件超出 SPC profile",
    "MISSING_OR_INVALID_MEASUREMENT": "量測值缺失或無效",
    "INVALID_PHYSICAL_MEASUREMENT": "量測值不符合物理限制",
    "NO_COMPLETE_TARGET_GROUP": "沒有完整有效的目標子組",
    "UNKNOWN_ADJACENCY_SINGLE_POINTS_ONLY": "無法確認相鄰子組順序",
    "EMPTY_VIEW": "目前篩選範圍沒有資料",
    "MONITORING_BEFORE_ORIGIN": "監控資料早於固定監控起點",
    "BASELINE_PROFILE_MISMATCH": "基準與目前 SPC profile 不相容",
    "UNSUPPORTED_RULE_VERSION": "不支援此 SPC 規則版本",
    "SPC_SIDECAR_MISSING": "缺少 SPC 取樣 sidecar",
    "SPC_SIDECAR_HASH_MISMATCH": "SPC 取樣 sidecar 指紋不符",
    "UNSUPPORTED_SPC_PROFILE_VERSION": "不支援此 canonical SPC profile 版本",
}


def format_reason(reason: str) -> str:
    raw = str(reason)
    code, separator, detail = raw.partition(":")
    label = REASON_LABELS.get(code, "未識別原因")
    suffix = f"：{detail}" if separator and detail else ""
    return f"{label}{suffix}（{raw}）"


def format_reasons(reasons) -> str:
    return "；".join(format_reason(reason) for reason in reasons)
