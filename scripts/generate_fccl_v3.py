from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fccl_testline.generation import write_v3


if __name__ == "__main__":
    manifest = write_v3(ROOT / "generated_data" / "v3")
    print(f"generated {manifest['rolls']} rolls / {manifest['segments']} segments")
