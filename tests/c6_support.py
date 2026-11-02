"""Explicit render-test providers. These never compute true SHAP values."""

from dataclasses import replace

from c_dashboard.adapters.explanations import (
    ExplanationInfo, ExplanationPayload, ExplanationResponse, ExplanationManifest,
)
from c_dashboard.adapters.mock_formula import DeterministicMockAdapter
from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.visualization.controller import workspace_source
from c_dashboard.visualization.explanations import make_request, select_class_output
from c_dashboard.visualization.config import SHAP_KINDS


class RenderTestModel(DeterministicMockAdapter):
    def describe(self):
        return replace(super().describe(), source="C6 render-test model", version="render-test-model-v1",
                       supports_shap=True, message="介面測試替身，不是真正模型解釋")

    def explanation_manifest(self):
        info = RenderTestProvider().describe()
        return info.manifest


class RenderTestProvider:
    def __init__(self):
        self.calls = 0

    def describe(self):
        targets = tuple(TARGET_UNITS)
        info = ExplanationInfo(
            source="C6 render-test provider", model_source=RenderTestModel().describe().source,
            model_version=RenderTestModel().describe().version, preprocessing_version="test-preprocess-v1",
            explanation_version="render-test-v1", available=True,
            feature_names=("line_speed_m_min", "ambient_rh_pct"), feature_units=("m/min", "%RH"),
            supported_targets=targets,
            output_scales=tuple((t, "probability" if t == "appearance_ng" else "regression_output") for t in targets),
            output_units=tuple((t, "probability" if t == "appearance_ng" else TARGET_UNITS[t]) for t in targets),
            background_source="render-test declared reference; no training/model calculation",
            source_kind="render-test",
        )
        manifest = ExplanationManifest(
            "render-test-manifest-v1", info.model_source, "render-test-only", info.model_version,
            "test-artifact-schema-v1", "test-features-v1", info.preprocessing_version,
            "test-labels-v1", "test-specs-v1", "test-training-dataset-v1",
            info.feature_names, info.feature_units, info.supported_targets, info.output_scales,
            info.output_units, (1, 0), info.background_source, ("c-view-v1",),
            ("c-local-labels-v1", "test-labels-v1"),
            ("c-mock", "legacy-csv", "segment-inspection", "synthetic-ground-truth"))
        return replace(info, manifest=manifest)

    def explain(self, request):
        self.calls += 1
        n = len(request.sample_ids)
        # Fixed fixture contributions are independent of Mock model outputs.
        contributions = tuple((.1 * (i + 1), -.02) for i in range(n))
        labels, index = (), None
        if request.target == "appearance_ng":
            labels = (1, 0)
            contributions, index = select_class_output(labels, (contributions, tuple((0., 0.) for _ in range(n))))
        payload = ExplanationPayload(request.sample_ids, request.feature_names, request.feature_units,
                                     request.feature_values, contributions, tuple(0. for _ in range(n)),
                                     class_labels=labels, output_index=index)
        return ExplanationResponse(request, payload=payload)


def request_for(rows, *, target="peel_strength_n_mm", kind=SHAP_KINDS[0], feature=None, info=None):
    from c_dashboard.visualization.heatmap import source_for
    info = info or RenderTestProvider().describe()
    source = source_for(rows, source_id="render-test", mapping_version="test-v1", source_kind="mock",
                        columns=info.feature_names)
    return make_request(rows, source, RenderTestModel().describe(), info, target=target, kind=kind,
                        feature=feature, model_manifest=RenderTestModel().explanation_manifest())
