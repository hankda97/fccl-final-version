from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CONFIG_DIR = Path(__file__).with_name("config")


def load_product_recipe() -> dict[str, Any]:
    data = json.loads((CONFIG_DIR / "product_recipe_v3.json").read_text(encoding="utf-8"))
    schema = json.loads((CONFIG_DIR / "product_recipe.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    validate_range_semantics(data)
    return data


def validate_range_semantics(data: dict[str, Any]) -> None:
    for name, item in data["recipe"]["parameters"].items():
        if not item["ui_min"] <= item["recipe_min"] <= item["default"] <= item["recipe_max"] <= item["ui_max"]:
            raise ValueError(f"RANGE_ORDER_INVALID:{name}")
        if "model_min" in item or "model_max" in item:
            raise ValueError(f"MODEL_RANGE_MUST_COME_FROM_MANIFEST:{name}")
