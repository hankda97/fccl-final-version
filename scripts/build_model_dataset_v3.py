from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from fccl_testline.dataset import write_model_dataset


if __name__ == "__main__":
    result = write_model_dataset(ROOT / "generated_data/v3/canonical_v3.csv", ROOT / "generated_data/model_dataset_v3")
    print(result["target_rows"])
