"""Filesystem boundaries for source, projection and trusted model artifacts."""

from __future__ import annotations

from pathlib import Path


class UnsafePathError(ValueError):
    pass


def resolve_within(path: Path | str, root: Path | str, *, must_exist: bool = False) -> Path:
    root_path = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise UnsafePathError(f"Path escapes trusted root: {candidate}") from exc
    if must_exist and not candidate.exists():
        raise FileNotFoundError(candidate)
    return candidate


def assert_output_separated(output: Path | str, readonly_roots: tuple[Path | str, ...]) -> Path:
    candidate = Path(output).resolve()
    for root in readonly_roots:
        readonly = Path(root).resolve()
        if candidate == readonly or readonly in candidate.parents or candidate in readonly.parents:
            raise UnsafePathError(f"Output overlaps read-only source: {readonly}")
    return candidate

