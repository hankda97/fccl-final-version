"""Pure native chart specifications; input values are already validated."""

from c_dashboard.visualization.config import label

from dataclasses import dataclass
from io import BytesIO

from c_dashboard.visualization.config import SHAP_KINDS, TEST_NOTICE
from c_dashboard.visualization.explanations import validate_response


@dataclass(frozen=True)
class RenderedExplanation:
    request: object
    spec: dict | None = None
    png: bytes | None = None


def explanation_spec(request, validated):
    values = []
    for j, feature in enumerate(request.feature_names):
        raw = [row[j] for row in request.feature_values]
        low, high = min(raw), max(raw)
        for i, sample_id in enumerate(request.sample_ids):
            value = raw[i]
            values.append({"sample_id": sample_id, "feature": feature,
                           "feature_label": f"{feature} [{request.feature_units[j]}]",
                           "value": value, "contribution": validated.contributions[i][j],
                           "normalized_value": (value-low)/(high-low) if high > low else .5})
    tooltip = [{"field": n} for n in ("sample_id", "feature_label", "value", "contribution")]
    scale_label = f"貢獻值 [{request.output_unit}] · {request.output_scale}"
    if request.kind == SHAP_KINDS[0]:
        encoding = {"x": {"field": "contribution", "type": "quantitative", "title": scale_label},
                    "y": {"field": "feature_label", "type": "nominal", "title": "模型解釋特徵"},
                    "color": {"field": "normalized_value", "type": "quantitative",
                              "scale": {"domain": [0, 1], "scheme": "redblue"},
                              "title": "特徵值（各欄正規化）"}, "tooltip": tooltip}
    else:
        values = [v for v in values if v["feature"] == request.feature]
        if not values:
            raise ValueError("所選 Dependence 特徵沒有解釋資料。")
        encoding = {"x": {"field": "value", "type": "quantitative", "title": values[0]["feature_label"],
                          "scale": {"zero": False}},
                    "y": {"field": "contribution", "type": "quantitative", "title": scale_label},
                    "tooltip": tooltip}
    suffix = f" · {TEST_NOTICE}" if request.info.source_kind == "render-test" else ""
    return {"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": request.kind + " · " + label(request.target) + suffix,
            "height": 300, "data": {"values": values},
            "mark": {"type": "point", "filled": True, "opacity": .65}, "encoding": encoding}


def prepare_explanation(request, response):
    """Consume a Figure into bytes and close it on every success/error path."""
    from matplotlib.figure import Figure
    from matplotlib import pyplot as plt
    figure = getattr(response, "figure", None)
    try:
        validated = validate_response(request, response)
        if figure is None:
            return RenderedExplanation(request, spec=explanation_spec(request, validated))
        if not isinstance(figure, Figure):
            raise ValueError("不支援的 Figure 型別；只接受受信任記憶體 Matplotlib Figure。")
        with BytesIO() as buffer:
            figure.savefig(buffer, format="png", bbox_inches="tight")
            return RenderedExplanation(request, png=buffer.getvalue())
    finally:
        if isinstance(figure, Figure):
            plt.close(figure)


def heatmap_records(result):
    return [{"feature": label(cell.feature), "target": label(cell.target),
             "r": cell.coefficient, "n": cell.n, "excluded": cell.excluded,
             "reason": cell.reason or "有效配對",
             "label_exclusions": "；".join(f"{code} ({count})" for code, count in cell.exclusions),
             "display": f"{cell.coefficient:.2f}" if cell.coefficient is not None else "N/A"}
            for cell in result.cells]


def heatmap_spec(result):
    kind = result.source.profile.kind
    observation = {"c-mock": "Mock 觀測", "synthetic-ground-truth": "合成真值",
                   "legacy-csv": "CSV 觀測（來源未驗證）", "unresolved": "待驗證投影"}.get(kind, "區段檢驗觀測")
    x = {"field": "target", "type": "nominal", "title": observation + "品質目標", "sort": None,
         "axis": {"labelAngle": -25, "labelLimit": 210}}
    y = {"field": "feature", "type": "nominal", "title": "製程／環境特徵", "sort": None,
         "axis": {"labelLimit": 230}}
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": f"Heatmap（{observation} Pearson；相關非因果）",
        "height": max(120, 32 * len({cell.feature for cell in result.cells})),
        "data": {"values": heatmap_records(result)},
        "encoding": {"x": x, "y": y,
                     "tooltip": [{"field": name} for name in ("feature", "target", "r", "n", "excluded", "reason", "label_exclusions")]},
        "layer": [
            {"mark": "rect", "encoding": {"color": {
                "condition": {"test": "isValid(datum.r)", "field": "r", "type": "quantitative",
                              "scale": {"domain": [-1, 1], "scheme": "redblue"},
                              "legend": {"title": "Pearson r"}}, "value": "#eeeeee"}}},
            {"mark": {"type": "text", "color": "#111111"},
             "encoding": {"text": {"field": "display"}}},
        ],
    }
