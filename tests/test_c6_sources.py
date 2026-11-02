from dataclasses import replace

import pytest

from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.visualization.sources import SourceProfile, LABEL_FLAGS
from c_dashboard.visualization.heatmap import source_for, compute_heatmap
from c_dashboard.visualization.explanations import make_request, ExplanationUnavailable
from c6_support import RenderTestModel, RenderTestProvider
from test_c6_heatmap import hand_rows, SPEED, PEEL, MD


PROFILE = SourceProfile(kind="segment-inspection", dataset_version="monitoring-v2",
                        alignment_version="test-alignment-v1", label_version="test-labels-v1")


def inspection_rows(rows=None):
    rows = hand_rows() if rows is None else rows.copy(deep=True)
    rows["root_roll_id"] = "TEST-ROLL"
    rows["aligned_sample_id"] = [f"TEST-ALIGNED-{i}" for i in range(len(rows))]
    rows["material_md_start_m"] = list(range(len(rows)))
    rows["material_md_end_m"] = [i+1 for i in range(len(rows))]
    rows["label_source"] = "simulated_inspection"
    rows["label_scope"] = "segment"
    rows["inspection_method"] = "laboratory_segment"
    rows["appearance_label_method"] = "online_vision"
    rows["test_method_version"] = "TEST-TM-v1"
    rows["spec_version"] = "TEST-SPEC-v1"
    for flag in LABEL_FLAGS.values():
        rows[flag] = 1
    rows["quality_label_available"] = 1
    return rows


def projected_source(rows, profile=PROFILE):
    return source_for(rows, source_id="projection-test", mapping_version="test-map-v2",
                      source_kind="test-projection", profile=profile)


def test_projection_partial_target_flags_do_not_mean_all_targets_and_do_not_fill():
    rows = inspection_rows()
    rows["peel_label_available"] = 0  # Existing numeric values must not bypass availability.
    rows["peel_label_reason"] = "DUPLICATE_INSPECTION_AMBIGUOUS"
    result = compute_heatmap(rows, projected_source(rows), [SPEED], [PEEL, MD])
    assert result.cells[0].n == 0 and result.cells[0].coefficient is None
    assert "DUPLICATE_INSPECTION_AMBIGUOUS" in result.cells[0].reason
    assert result.cells[1].coefficient == pytest.approx(-1)
    assert result.cells[1].n == 4
    assert projected_source(rows).profile.dataset_version == "monitoring-v2"
    assert "material_md_start_m" in dict(result.source.context)


@pytest.mark.parametrize("field,value,code", [
    ("label_scope", "roll", "LABEL_SCOPE"),
    ("label_source", "synthetic_ground_truth", "LABEL_SOURCE"),
    ("alignment_status", "ALIGNMENT_INCOMPLETE", "ALIGNMENT_INCOMPLETE"),
    ("peel_label_reason", "DUPLICATE_INSPECTION_AMBIGUOUS", "DUPLICATE_INSPECTION_AMBIGUOUS"),
    ("inspection_method", "unknown", "LABEL_METHOD"),
    ("material_md_end_m", 0, "MD_INTERVAL"),
    ("schema_version", "different", "VERSION_MISMATCH"),
])
def test_upstream_invalid_scope_source_alignment_method_reason_is_not_reinterpreted(field, value, code):
    rows = inspection_rows()
    rows[field] = value
    cell = compute_heatmap(rows, projected_source(rows), [SPEED], [PEEL]).cells[0]
    assert cell.n == 0 and code in cell.reason


def test_missing_projection_missing_target_flag_and_mixed_versions_do_not_guess():
    rows = inspection_rows()
    implicit = source_for(rows, source_id="implicit", mapping_version="c-view-v1", source_kind="upload")
    assert "SOURCE_PROFILE_REQUIRED" in compute_heatmap(rows, implicit, [SPEED], [PEEL]).cells[0].reason
    rows = rows.drop(columns=["peel_label_available"])
    assert "MISSING_TARGET_AVAILABILITY" in compute_heatmap(rows, projected_source(rows), [SPEED], [PEEL]).cells[0].reason
    rows = inspection_rows()
    rows.loc[0, "spec_version"] = "different"
    assert "INCOMPATIBLE_METADATA" in compute_heatmap(rows, projected_source(rows), [SPEED], [PEEL]).cells[0].reason
    # No product spec is not a reason to invent quality approval or disable valid correlation.
    rows = rows.drop(columns=["spec_version"])
    assert compute_heatmap(rows, projected_source(rows), [SPEED], [PEEL]).cells[0].coefficient == pytest.approx(1)


def test_synthetic_truth_is_explicit_separate_and_partial_exclusions_are_visible():
    from c_dashboard.visualization.charts import heatmap_spec
    rows = inspection_rows()
    rows["label_source"] = "synthetic_ground_truth"
    profile = replace(PROFILE, kind="synthetic-ground-truth")
    result = compute_heatmap(rows, projected_source(rows, profile), [SPEED], [PEEL])
    assert result.cells[0].n == 4
    assert "合成真值" in heatmap_spec(result)["title"] and "實測" not in heatmap_spec(result)["title"]
    rows.loc[0, "label_source"] = "simulated_inspection"
    cell = compute_heatmap(rows, projected_source(rows, profile), [SPEED], [PEEL]).cells[0]
    assert cell.n == 3 and cell.exclusions[0][1] == 1
    assert cell.coefficient == pytest.approx(1)


def test_appearance_conflict_excludes_only_appearance_even_if_numeric_available():
    rows = inspection_rows()
    rows["appearance_label_available"] = 0
    rows["appearance_label_reason"] = "APPEARANCE_FLAG_CONFLICT"
    result = compute_heatmap(rows, projected_source(rows), [SPEED], ["appearance_ng", PEEL])
    assert "APPEARANCE_FLAG_CONFLICT" in result.cells[0].reason
    assert result.cells[1].n == 4


def test_label_missing_does_not_disable_explanation_and_training_hash_need_not_equal_live_data():
    rows = inspection_rows().drop(columns=list(TARGET_UNITS))
    for flag in LABEL_FLAGS.values():
        rows[flag] = 0
    info = RenderTestProvider().describe()
    request = make_request(rows, projected_source(rows), RenderTestModel().describe(), info,
                           target=PEEL, kind="SHAP Summary Plot", model_manifest=info.manifest)
    assert len(request.sample_ids) == 4
    assert request.source.profile.dataset_version != info.manifest.dataset_version


@pytest.mark.parametrize("name,value", [
    ("manifest_id", "wrong"), ("model_type", "wrong"), ("feature_version", "wrong"),
    ("label_version", "wrong"), ("spec_version", "wrong"), ("dataset_version", "wrong"),
    ("class_labels", (0, 1)), ("manifest_id", ""),
])
def test_manifest_must_match_independently_selected_model(name, value):
    info = RenderTestProvider().describe()
    modified = replace(info, manifest=replace(info.manifest, **{name: value}))
    with pytest.raises(ValueError, match="manifest"):
        make_request(hand_rows(), projected_source(hand_rows(), SourceProfile(kind="c-mock")),
                     RenderTestModel().describe(), modified, target=PEEL, kind="SHAP Summary Plot",
                     model_manifest=info.manifest)


def test_manifest_required_source_compatibility_and_target_specific_unavailable():
    info = RenderTestProvider().describe()
    rows = inspection_rows()
    with pytest.raises(ValueError, match="manifest"):
        make_request(rows, projected_source(rows), RenderTestModel().describe(), replace(info, manifest=None),
                     target=PEEL, kind="SHAP Summary Plot", model_manifest=info.manifest)
    with pytest.raises(ExplanationUnavailable, match="相容"):
        make_request(rows, projected_source(rows, replace(PROFILE, schema_version="unsupported")),
                     RenderTestModel().describe(), info, target=PEEL, kind="SHAP Summary Plot", model_manifest=info.manifest)
    manifest = replace(info.manifest, unavailable_targets=((PEEL, "PEEL_MODEL_NOT_DELIVERED"),))
    with pytest.raises(ExplanationUnavailable, match="PEEL_MODEL_NOT_DELIVERED"):
        make_request(rows, projected_source(rows), RenderTestModel().describe(), replace(info, manifest=manifest),
                     target=PEEL, kind="SHAP Summary Plot", model_manifest=manifest)


def test_total_flag_conflict_and_missing_method_version_do_not_become_valid_labels():
    rows = inspection_rows()
    rows["quality_label_available"] = 0
    assert "AVAILABILITY_CONFLICT" in compute_heatmap(rows, projected_source(rows), [SPEED], [PEEL]).cells[0].reason
    rows["quality_label_available"] = 1
    rows["test_method_version"] = ""
    assert "MISSING_TEST_METHOD_VERSION" in compute_heatmap(rows, projected_source(rows), [SPEED], [PEEL]).cells[0].reason


@pytest.mark.parametrize("scale", ["raw_margin", "log_odds"])
def test_ng_output_scale_is_preserved_not_silently_converted_to_probability(scale):
    from c_dashboard.visualization.charts import prepare_explanation
    info = RenderTestProvider().describe()
    scales = tuple((t, scale if t == "appearance_ng" else s) for t, s in info.output_scales)
    units = tuple((t, scale if t == "appearance_ng" else u) for t, u in info.output_units)
    manifest = replace(info.manifest, output_scales=scales, output_units=units)
    info = replace(info, output_scales=scales, output_units=units, manifest=manifest)
    rows = hand_rows()
    request = make_request(rows, projected_source(rows, SourceProfile(kind="c-mock")),
        RenderTestModel().describe(), info, target="appearance_ng", kind="SHAP Summary Plot", model_manifest=manifest)
    result = prepare_explanation(request, RenderTestProvider().explain(request))
    assert scale in result.spec["encoding"]["x"]["title"]
    assert result.spec["data"]["values"][0]["contribution"] == .1


@pytest.mark.parametrize("feature", ["root_roll_id", "appearance_ng_probability", "peel_label_available", "peel_spec_pass_flag", "drift_event_id"])
def test_identity_pass_flags_availability_and_drift_are_forbidden_explanation_features(feature):
    info = RenderTestProvider().describe()
    rows = hand_rows()
    rows[feature] = 1
    changed = replace(info, feature_names=(feature, "ambient_rh_pct"))
    with pytest.raises(ValueError, match="不允許"):
        make_request(rows, projected_source(rows, SourceProfile(kind="c-mock")), RenderTestModel().describe(),
                     changed, target=PEEL, kind="SHAP Summary Plot", model_manifest=info.manifest)
