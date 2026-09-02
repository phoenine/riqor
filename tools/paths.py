#!/usr/bin/env python3
"""Resolve repo-relative paths against the agent-next package root.

This repository root *is* the agent-next package. Run state, config, and
knowledge store paths relative to this root (for example `knowledge/shop/_index.md`).
Legacy values prefixed with `agent-next/` are still accepted when reading.
"""

from __future__ import annotations

from pathlib import Path

AGENT_NEXT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_LOGICAL_ROOT_NAME = "agent-next"

REPO_TOP_LEVEL_DIRS = frozenset(
    {
        "config",
        "docs",
        "knowledge",
        "outputs",
        "repositories",
        "runs",
        "schemas",
        "skills",
        "templates",
        "tools",
        "workflows",
    }
)


def strip_legacy_prefix(path: str | Path) -> Path:
    """Remove a leading legacy `agent-next/` prefix when present."""
    candidate = Path(path)
    if candidate.parts and candidate.parts[0] == LEGACY_LOGICAL_ROOT_NAME:
        return Path(*candidate.parts[1:])
    return candidate


def resolve_repo_path(path: str | Path, *, root: Path | None = None) -> Path:
    """Map a repo-relative (or legacy logical) path to a filesystem path.

    - Absolute paths are returned unchanged.
    - Paths starting with `agent-next/` map to `<root>/<remainder>`.
    - Other relative paths are joined to `<root>/`.
    """
    package_root = root or AGENT_NEXT_ROOT
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return package_root / strip_legacy_prefix(candidate)


def resolve_managed_repo_path(
    path: str | Path,
    managed_dir: str,
    *,
    root: Path | None = None,
) -> Path:
    """Resolve a repo-relative path and require it to stay in one managed directory."""
    package_root = root or AGENT_NEXT_ROOT
    candidate = Path(path)
    if candidate.is_absolute():
        raise ValueError(f"path must be repo-relative under {managed_dir}/: {candidate}")
    resolved = resolve_repo_path(candidate, root=package_root)
    managed_root = (package_root / managed_dir).resolve()
    if not resolved.resolve().is_relative_to(managed_root):
        raise ValueError(f"path must stay under {managed_dir}/: {candidate}")
    return resolved


def as_repo_path(path: str | Path, *, root: Path | None = None) -> str:
    """Return a stable repo-relative path from the package root."""
    package_root = root or AGENT_NEXT_ROOT
    candidate = strip_legacy_prefix(path)
    resolved = candidate if candidate.is_absolute() else resolve_repo_path(candidate, root=package_root)
    try:
        relative = resolved.resolve().relative_to(package_root.resolve())
    except ValueError:
        return candidate.as_posix()
    return relative.as_posix()


# Backward-compatible alias used by existing tools.
as_logical_path = as_repo_path
