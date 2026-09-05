#!/usr/bin/env python3
"""Canonical workflow phase names for agent-next run state and stage gates."""

from __future__ import annotations

from pathlib import Path

try:
    from .paths import AGENT_NEXT_ROOT
    from .workflow_registry import WorkflowRegistryError, load_workflow, load_workflows
except ImportError:  # pragma: no cover - compatibility for direct script imports
    try:
        from tools.paths import AGENT_NEXT_ROOT
        from tools.workflow_registry import (
            WorkflowRegistryError,
            load_workflow,
            load_workflows,
        )
    except ImportError:
        from paths import AGENT_NEXT_ROOT
        from workflow_registry import WorkflowRegistryError, load_workflow, load_workflows


def _workflow_records(root: Path) -> dict:
    registry = load_workflows(root)
    if registry.errors:
        raise WorkflowRegistryError("invalid workflow registry: " + "; ".join(registry.errors))
    return registry.records


_BUILTIN_WORKFLOWS = _workflow_records(AGENT_NEXT_ROOT)
CANONICAL_PHASES: dict[str, tuple[str, ...]] = {
    workflow_id: tuple(phase.name for phase in record.phases)
    for workflow_id, record in _BUILTIN_WORKFLOWS.items()
}

WORKFLOW_ENTRIES: tuple[str, ...] = tuple(CANONICAL_PHASES.keys())

# Entry-scoped aliases for common drift (lowercase keys).
PHASE_ALIASES: dict[tuple[str, str], str] = {
    ("release-acceptance", "post-release observation"): "Optional Post-release Observation",
}

ALL_CANONICAL_PHASES: tuple[str, ...] = tuple(
    phase for phases in CANONICAL_PHASES.values() for phase in phases
)


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def workflow_readme_path(entry: str, *, root: Path | None = None) -> str:
    return load_workflow(root or AGENT_NEXT_ROOT, entry).readme


def phase_doc_path(entry: str, phase: str, *, root: Path | None = None) -> str:
    """Repo-relative path to the lazy-load phase document."""
    package_root = root or AGENT_NEXT_ROOT
    record = load_workflow(package_root, entry)
    phases = tuple(item.name for item in record.phases)
    normalized = _normalize_phase(phase, entry, {entry: phases})
    if normalized not in phases:
        allowed = ", ".join(phases)
        raise ValueError(f"unknown phase {phase!r} for entry {entry!r}; must be one of: {allowed}")
    document = next(item.document for item in record.phases if item.name == normalized)
    return f"workflows/{entry}/{document}"


def list_phase_doc_paths(entry: str, *, root: Path | None = None) -> list[tuple[str, str]]:
    record = load_workflow(root or AGENT_NEXT_ROOT, entry)
    return [(phase.name, f"workflows/{entry}/{phase.document}") for phase in record.phases]


def normalize_phase(
    phase: str, entry: str | None = None, *, root: Path | None = None
) -> str:
    """Return the canonical phase name when entry is known; otherwise best effort."""
    canonical_phases = CANONICAL_PHASES
    if root is not None:
        canonical_phases = {
            workflow_id: tuple(item.name for item in record.phases)
            for workflow_id, record in _workflow_records(root).items()
        }
    return _normalize_phase(phase, entry, canonical_phases)


def _normalize_phase(
    phase: str,
    entry: str | None,
    canonical_phases: dict[str, tuple[str, ...]],
) -> str:
    trimmed = _collapse_whitespace(phase)
    if not trimmed:
        return trimmed
    if entry and entry in canonical_phases:
        lowered = trimmed.lower()
        alias = PHASE_ALIASES.get((entry, lowered))
        if alias:
            return alias
        for canonical in canonical_phases[entry]:
            if canonical.lower() == lowered:
                return canonical
        return trimmed

    lowered = trimmed.lower()
    alias_matches = {PHASE_ALIASES[key] for key in PHASE_ALIASES if key[1] == lowered}
    if len(alias_matches) == 1:
        return next(iter(alias_matches))

    case_matches = [canonical for canonical in ALL_CANONICAL_PHASES if canonical.lower() == lowered]
    if len(case_matches) == 1:
        return case_matches[0]

    return PHASE_ALIASES.get(("feature-quality", lowered), trimmed)


def phase_validation_error(
    entry: str | None,
    phase: str,
    *,
    root: Path | None = None,
    registered_phases: tuple[str, ...] | None = None,
) -> str | None:
    if not phase:
        return "required non-empty string"
    if registered_phases is not None and entry is not None:
        canonical_phases = {entry: registered_phases}
    elif root is not None:
        canonical_phases = {
            workflow_id: tuple(item.name for item in record.phases)
            for workflow_id, record in _workflow_records(root).items()
        }
    else:
        canonical_phases = CANONICAL_PHASES
    if entry not in canonical_phases:
        return f"cannot be validated because entry {entry!r} is not registered"
    normalized = _normalize_phase(phase, entry, canonical_phases)
    if normalized not in canonical_phases[entry]:
        allowed = ", ".join(canonical_phases[entry])
        return f"must be one of: {allowed}"
    return None
