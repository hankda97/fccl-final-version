from c_dashboard.spc.messages import format_reason, format_reasons


def test_required_reason_codes_are_clear_chinese_and_preserve_raw_codes():
    text = format_reasons(("MISSING_SAMPLING_EVIDENCE", "BASELINE_UNAVAILABLE"))
    assert "缺少可驗證的取樣證據" in text
    assert "無可用的穩定歷史基準" in text
    assert "MISSING_SAMPLING_EVIDENCE" in text and "BASELINE_UNAVAILABLE" in text


def test_prefixed_detail_and_unknown_code_remain_auditable():
    known = format_reason("UNSTABLE_HISTORY_MEAN:TREND_UP_6:R/G")
    assert "歷史子組均值不穩定" in known and "TREND_UP_6:R/G" in known
    unknown = format_reason("FUTURE_REASON:detail")
    assert unknown == "未識別原因：detail（FUTURE_REASON:detail）"
