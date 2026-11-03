import copy

import pytest

from fccl_testline.config import load_product_recipe, validate_range_semantics


def test_versioned_product_recipe_matches_design() -> None:
    data = load_product_recipe()
    assert data["product"]["product_id"] == "FCCL-DEMO-001"
    assert data["recipe"]["recipe_id"] == "SIM-RECIPE-3.0"
    p = data["recipe"]["parameters"]
    assert p["line_speed_m_min"] == {"station": "coating", "unit": "m/min", "default": 4.8, "recipe_min": 4.4, "recipe_max": 5.2, "ui_min": 4.0, "ui_max": 5.6}
    assert p["curing_temp_c"]["default"] == 171.0
    assert p["exhaust_airflow_m3_h"]["default"] == 2100.0
    assert data["product"]["dry_thickness_um"] == {"target": 25.0, "lsl": 23.0, "usl": 27.0, "unit": "um"}


def test_ranges_cannot_be_interchanged_or_claim_model_support() -> None:
    data = load_product_recipe()
    bad = copy.deepcopy(data)
    bad["recipe"]["parameters"]["line_speed_m_min"]["recipe_min"] = 3.9
    with pytest.raises(ValueError, match="RANGE_ORDER_INVALID"):
        validate_range_semantics(bad)
    bad = copy.deepcopy(data)
    bad["recipe"]["parameters"]["line_speed_m_min"]["model_min"] = 4.0
    with pytest.raises(ValueError, match="MODEL_RANGE_MUST_COME_FROM_MANIFEST"):
        validate_range_semantics(bad)
