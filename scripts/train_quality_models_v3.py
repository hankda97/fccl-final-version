from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from fccl_testline.modeling import train_all


if __name__ == "__main__":
    registry = train_all(ROOT / "generated_data/model_dataset_v3", ROOT / "artifacts/synthetic_v3/quality-v3.0")
    print({target: item["test_metrics"] for target, item in registry["targets"].items()})
