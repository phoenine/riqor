#!/usr/bin/env python3
"""Canonical workflow phase names for agent-next run state and stage gates."""

from __future__ import annotations

import re

CANONICAL_PHASES: dict[str, tuple[str, ...]] = {
    "feature-quality": (
        "Intake",
        "Requirement Specification",
        "Risk Analysis",
        "Test Design",
        "Optional Case Sync Or Generation",
        "Optional Case Execute",
        "Optional Bug Report",
        "Optional Test Report",
    ),
    "bug-regression": (
        "Bug Intake",
        "Change Scope",
        "Impact Analysis",
        "Coverage Match",
        "Decision Gate",
        "Regression Plan",
        "Execution",
        "Regression Report",
    ),
    "release-acceptance": (
        "Release Baseline",
        "Scope Collection",
        "Acceptance Plan",
        "Acceptance Execution",
        "Release Decision",
        "Optional Post-release Observation",
    ),
}

WORKFLOW_ENTRIES: tuple[str, ...] = tuple(CANONICAL_PHASES.keys())

# Entry-scoped aliases for common drift (lowercase keys).
PHASE_ALIASES: dict[tuple[str, str], str] = {
    ("feature-quality", "intake"): "Intake",
    ("bug-regression", "bug intake"): "Bug Intake",
    ("release-acceptance", "post-release observation"): "Optional Post-release Observation",
    ("release-acceptance", "optional post-release observation"): "Optional Post-release Observation",
}

ALL_CANONICAL_PHASES: tuple[str, ...] = tuple(
    phase for phases in CANONICAL_PHASES.values() for phase in phases
)


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def phase_slug(phase: str) -> str:
    """Stable filename slug for a canonical phase name."""
    return re.sub(r"[^a-z0-9]+", "-", phase.lower()).strip("-")


def build_phase_doc_filenames(entry: str) -> dict[str, str]:
    """Map canonical phase name to numbered filename under phases/."""
    if entry not in CANONICAL_PHASES:
        raise KeyError(f"unknown entry: {entry}")
    return {
        phase: f"{index:02d}-{phase_slug(phase)}.md"
        for index, phase in enumerate(CANONICAL_PHASES[entry], start=1)
    }


PHASE_DOC_FILENAMES: dict[str, dict[str, str]] = {
    entry: build_phase_doc_filenames(entry) for entry in WORKFLOW_ENTRIES
}


def workflow_readme_path(entry: str) -> str:
    if entry not in CANONICAL_PHASES:
        raise KeyError(f"unknown entry: {entry}")
    return f"workflows/{entry}/README.md"


def phase_doc_path(entry: str, phase: str) -> str:
    """Repo-relative path to the lazy-load phase document."""
    if entry not in CANONICAL_PHASES:
        raise KeyError(f"unknown entry: {entry}")
    normalized = normalize_phase(phase, entry)
    filenames = PHASE_DOC_FILENAMES[entry]
    if normalized not in filenames:
        allowed = ", ".join(CANONICAL_PHASES[entry])
        raise ValueError(f"unknown phase {phase!r} for entry {entry!r}; must be one of: {allowed}")
    return f"workflows/{entry}/phases/{filenames[normalized]}"


def list_phase_doc_paths(entry: str) -> list[tuple[str, str]]:
    return [(phase, phase_doc_path(entry, phase)) for phase in CANONICAL_PHASES[entry]]


def normalize_phase(phase: str, entry: str | None = None) -> str:
    """Return the canonical phase name when entry is known; otherwise best effort."""
    trimmed = _collapse_whitespace(phase)
    if not trimmed:
        return trimmed

    if entry and entry in CANONICAL_PHASES:
        lowered = trimmed.lower()
        alias = PHASE_ALIASES.get((entry, lowered))
        if alias:
            return alias
        for canonical in CANONICAL_PHASES[entry]:
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


def phase_validation_error(entry: str | None, phase: str) -> str | None:
    if not phase:
        return "required non-empty string"
    if entry not in CANONICAL_PHASES:
        return None
    normalized = normalize_phase(phase, entry)
    if normalized not in CANONICAL_PHASES[entry]:
        allowed = ", ".join(CANONICAL_PHASES[entry])
        return f"must be one of: {allowed}"
    return None


def format_phase_reference(entry: str) -> str:
    if entry not in CANONICAL_PHASES:
        return ""
    return "\n".join(f"- `{phase}`" for phase in CANONICAL_PHASES[entry])
