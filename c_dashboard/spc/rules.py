"""Shared history/monitoring predicates. Signal windows end at their trigger."""

RULE_LABELS = {
    "BEYOND_LIMIT": "單點超出管制界限", "TREND_UP_6": "連續六點嚴格上升",
    "TREND_DOWN_6": "連續六點嚴格下降", "ABOVE_CL_9": "連續九點高於中心線",
    "BELOW_CL_9": "連續九點低於中心線",
}


def detect_signals(points, baseline):
    """Return (point index, rule, raw-precision sequence); retain barriers."""
    if not baseline.valid:
        return ()
    signals, window = [], []
    for index, point in enumerate(points):
        if point.break_before or not point.valid:
            window = []
        if not point.valid:
            continue
        value = point.mean
        window = (window + [value])[-9:]
        if value > baseline.ucl or value < baseline.lcl:
            signals.append((index, "BEYOND_LIMIT", (value,)))
        if len(window) >= 6:
            last = window[-6:]
            if all(a < b for a, b in zip(last, last[1:])):
                signals.append((index, "TREND_UP_6", tuple(last)))
            if all(a > b for a, b in zip(last, last[1:])):
                signals.append((index, "TREND_DOWN_6", tuple(last)))
        if len(window) >= 9:
            if all(x > baseline.cl for x in window):
                signals.append((index, "ABOVE_CL_9", tuple(window)))
            if all(x < baseline.cl for x in window):
                signals.append((index, "BELOW_CL_9", tuple(window)))
    return tuple(signals)
