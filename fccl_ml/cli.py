"""Command line entry point for the versioned FCCL ML pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import PipelineConfig
from .dataset import build_canonical_dataset
from .training import TrainingConfig, train_models


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fccl_ml.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--profile", required=True, choices=("synthetic-ground-truth-v2", "simulated-inspection-v2"))
    build.add_argument("--project-root", type=Path, default=Path.cwd())
    build.add_argument("--output", type=Path)
    train = subparsers.add_parser("train")
    train.add_argument("--profile", required=True, choices=("synthetic-ground-truth-v2", "simulated-inspection-v2"))
    train.add_argument("--project-root", type=Path, default=Path.cwd())
    train.add_argument("--dataset-dir", type=Path)
    train.add_argument("--artifact-root", type=Path)
    args = parser.parse_args(argv)
    if args.command == "build":
        config = PipelineConfig.default(args.project_root)
        result = build_canonical_dataset(config, args.profile, args.output)
        print(json.dumps({"profile": result.profile, "output": str(result.output_dir), "dataset_version": result.manifest["dataset_version"], "rows": {k: len(v) for k, v in result.projections.items()}}, ensure_ascii=False))
        return 0
    if args.command == "train":
        config = PipelineConfig.default(args.project_root)
        dataset_dir = args.dataset_dir or config.dataset_dir / args.profile
        artifact_root = args.artifact_root or config.artifact_dir
        result = train_models(dataset_dir, artifact_root, TrainingConfig(seed=config.seed))
        print(json.dumps({"profile": result.profile, "output": str(result.output_dir), "model_version": result.registry["active_model_version"]}, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

