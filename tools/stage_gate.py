#!/usr/bin/env python3
"""Run stage-gate checks for an agent-next state file.

Machine-enforced rules mirror `workflows/stage-gates.md`. Optional phases may
pass with a skip note: `optional_skip:<phase>: <reason>` in `notes[]`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import AGENT_NEXT_ROOT, resolve_managed_repo_path, resolve_repo_path  # noqa: E402
from phases import (  # noqa: E402
    CANONICAL_PHASES,
    normalize_phase,
    phase_validation_error,
    workflow_readme_path,
)
from run_state_schema import CURRENT_SCHEMA_VERSION  # noqa: E402
from validate_test_cases import (  # noqa: E402
    CASE_RULES_PATH,
    COVERAGE_REVIEW_RULES_PATH,
    TEST_CASE_DESIGN_RULES_PATH,
    validate_test_case_file,
)
from validate_artifact import validate_artifact_file  # noqa: E402
from artifact_frontmatter import ARTIFACT_SPECS  # noqa: E402
from traceability_lint import lint_run_state_traceability  # noqa: E402


ROUTER_SKILL = "agent-next"
RESOLVED_KNOWLEDGE_PLAN_STATUSES = {"not_needed", "proposed", "confirmed", "rejected"}
VALID_KNOWLEDGE_PLAN_STATUSES = {"pending"} | RESOLVED_KNOWLEDGE_PLAN_STATUSES

REQUIRED_TOP_LEVEL = [
    "schema_version",
    "run_id",
    "entry",
    "workflow",
    "phase",
    "required_skills",
    "loaded_skills",
    "skill_receipts",
    "repositories",
    "repository_evidence",
    "knowledge_used",
    "knowledge_plan",
    "environment",
    "confirmations",
    "artifacts",
    "traceability",
    "gate_results",
]

ARTIFACT_REQUIRED = [
    "id",
    "type",
    "path",
    "producer_phase",
    "source_artifacts",
    "evidence",
    "validation",
]

# Keys per phase rule:
# - required_skills: skills that must be declared and loaded (router added automatically)
# - required_skills_any: at least one of these skills must be declared and loaded
# - artifact_types: required artifact types for the phase
# - optional_artifact_types: acceptable artifacts when an optional phase is performed
# - optional: phase may be skipped with optional_skip:<phase>: note
# - knowledge: requires knowledge_used or knowledge_not_applicable: note
# - repository_evidence: requires repository_evidence or repository_not_applicable: note
# - knowledge_plan_resolved: knowledge_plan.status must not remain pending
# - require_intake_input: requires intake_input: note (feature testing)
# - require_bug_intake: requires bug_intake: note (bug regression)
# - require_environment_target: environment.target must be non-empty
# - require_note_prefixes: at least one note must start with each prefix
# - traceability: traceability list must not be empty
PHASE_RULES: dict[tuple[str, str], dict[str, Any]] = {
    # Feature testing
    ("feature-quality", "Intake"): {
        "required_skills": ["requirement-analysis"],
        "knowledge": True,
        "knowledge_plan_resolved": True,
        "require_intake_input": True,
    },
    ("feature-quality", "Requirement Specification"): {
        "required_skills": ["requirement-analysis"],
        "artifact_types": ["requirement_spec"],
        "knowledge": True,
    },
    ("feature-quality", "Risk Analysis"): {
        "required_skills": ["test-analysis"],
        "artifact_types": ["risk_analysis"],
        "knowledge": True,
        "repository_evidence": True,
    },
    ("feature-quality", "Test Design"): {
        "required_skills": ["test-analysis", "test-case-design"],
        "artifact_types": ["test_points"],
        "knowledge": True,
    },
    ("feature-quality", "Optional Case Sync Or Generation"): {
        "optional": True,
        "optional_artifact_types": ["automation_classification"],
        "require_note_prefixes": ["external_sync:"],
    },
    ("feature-quality", "Optional Case Execute"): {
        "optional": True,
        "required_skills_any": ["automation", "test-case-design"],
        "optional_artifact_types": ["execution_record"],
        "require_note_prefixes": ["data_injection:"],
    },
    ("feature-quality", "Optional Bug Report"): {
        "optional": True,
        "required_skills": ["reporting"],
        "optional_artifact_types": ["bug_report"],
    },
    ("feature-quality", "Optional Test Report"): {
        "optional": True,
        "required_skills": ["reporting"],
        "artifact_types": ["run_summary"],
        "traceability": True,
    },
    # Bug regression
    ("bug-regression", "Bug Intake"): {
        "required_skills": ["requirement-analysis"],
        "knowledge": True,
        "require_bug_intake": True,
        "require_note_prefixes": ["bug_surface:"],
    },
    ("bug-regression", "Change Scope"): {
        "required_skills": ["test-analysis"],
        "artifact_types": ["change_scope"],
        "knowledge": True,
        "repository_evidence": True,
    },
    ("bug-regression", "Impact Analysis"): {
        "required_skills": ["test-analysis"],
        "artifact_types": ["risk_analysis"],
        "knowledge": True,
        "repository_evidence": True,
    },
    ("bug-regression", "Coverage Match"): {
        "required_skills": ["test-case-design", "automation"],
        "artifact_types": ["coverage_match"],
        "knowledge": True,
    },
    ("bug-regression", "Decision Gate"): {
        "required_skills": ["test-case-design", "automation"],
        "require_note_prefixes": ["decision_path:"],
    },
    ("bug-regression", "Regression Plan"): {
        "required_skills": ["test-case-design", "automation", "reporting"],
        "artifact_types": ["regression_plan"],
        "require_note_prefixes": ["regression_strategy:"],
    },
    ("bug-regression", "Execution"): {
        "optional": True,
        "required_skills_any": ["test-case-design", "automation"],
        "optional_artifact_types": ["execution_record"],
        "require_note_prefixes": ["data_injection:"],
    },
    ("bug-regression", "Regression Report"): {
        "required_skills": ["reporting"],
        "artifact_types": ["regression_report"],
        "traceability": True,
    },
    # Release acceptance
    ("release-acceptance", "Release Baseline"): {
        "required_skills": ["release-acceptance"],
        "knowledge": True,
        "repository_evidence": True,
        "require_environment_target": True,
        "require_release_scope_tracks": True,
        "require_note_prefixes": ["release_baseline:"],
    },
    ("release-acceptance", "Scope Collection"): {
        "required_skills": ["release-acceptance", "requirement-analysis", "test-analysis"],
        "knowledge": True,
        "require_release_scope_tracks": True,
        "require_note_prefixes": ["release_scope:"],
    },
    ("release-acceptance", "Acceptance Plan"): {
        "required_skills": ["release-acceptance", "test-case-design", "automation"],
        "artifact_types": ["acceptance_plan"],
        "knowledge": True,
    },
    ("release-acceptance", "Acceptance Execution"): {
        "required_skills": ["automation", "release-acceptance"],
        "optional_artifact_types": ["execution_record"],
        "require_note_prefixes_always": ["automation_execution_plan:", "automation_execution_skip:"],
        "require_note_prefixes": ["execution_evidence:", "data_injection:", "optional_skip:"],
    },
    ("release-acceptance", "Release Decision"): {
        "required_skills": ["release-acceptance", "reporting"],
        "artifact_types": ["acceptance_report"],
        "traceability": True,
        "require_note_prefixes": ["release_decision:"],
    },
    ("release-acceptance", "Optional Post-release Observation"): {
        "optional": True,
        "required_skills": ["release-acceptance", "reporting"],
    },
}

def load_state(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def has_note(state: dict[str, Any], prefix: str) -> bool:
    return any(str(note).startswith(prefix) for note in state.get("notes", []))


def has_optional_skip(state: dict[str, Any], phase: str) -> bool:
    phase_prefix = f"optional_skip:{phase}:"
    return any(str(note).startswith(phase_prefix) for note in state.get("notes", []))


def artifact_types(state: dict[str, Any]) -> set[str]:
    return {artifact.get("type") for artifact in state.get("artifacts", []) if artifact.get("type")}


def release_scope_tracks(state: dict[str, Any]) -> set[str]:
    tracks = state.get("release_scope_tracks", [])
    if not isinstance(tracks, list):
        return set()
    return {str(track) for track in tracks}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_receipt_skills(
    state: dict[str, Any], phase: str, *, repo_root: Path | None = None
) -> set[str]:
    root = (repo_root or AGENT_NEXT_ROOT).resolve()
    valid: set[str] = set()
    for receipt in state.get("skill_receipts", []):
        raw_path = str(receipt.get("path", "")).strip()
        expected_sha = str(receipt.get("sha256", "")).strip()
        if not raw_path or Path(raw_path).is_absolute() or receipt.get("supports_phase") != phase:
            continue
        path = resolve_repo_path(raw_path, root=root)
        try:
            in_skills = path.resolve().is_relative_to((root / "skills").resolve())
        except OSError:
            in_skills = False
        if not in_skills or not path.is_file() or len(expected_sha) != 64:
            continue
        if sha256_file(path) == expected_sha:
            valid.add(str(receipt.get("skill", "")))
    return valid


def check_recorded_reference_paths(
    state: dict[str, Any], *, repo_root: Path | None = None
) -> list[str]:
    errors: list[str] = []
    root = (repo_root or AGENT_NEXT_ROOT).resolve()
    knowledge_root = (root / "knowledge").resolve()
    skills_root = (root / "skills").resolve()
    for item in state.get("knowledge_used", []):
        if not isinstance(item, dict):
            continue
        raw_path = str(item.get("path", "")).strip()
        if not raw_path:
            continue
        if Path(raw_path).is_absolute():
            errors.append(f"knowledge_used path must be repo-relative: {raw_path}")
            continue
        path = resolve_repo_path(raw_path, root=root)
        try:
            resolved = path.resolve()
            allowed = resolved.is_relative_to(knowledge_root) or (
                resolved.is_relative_to(skills_root)
                and "/references/" in raw_path.replace("\\", "/")
            )
        except OSError:
            allowed = False
        if not allowed:
            errors.append(
                "knowledge_used path must be under knowledge/ or a skills/*/references/ directory: "
                f"{raw_path}"
            )
        elif not path.is_file():
            errors.append(f"knowledge_used path does not exist: {raw_path}")
    return errors


def check_predecessor_gate(state: dict[str, Any], entry: str, phase: str) -> list[str]:
    phases = CANONICAL_PHASES.get(entry)
    if not phases or phase not in phases:
        return []
    index = phases.index(phase)
    if index == 0:
        return []
    predecessor = phases[index - 1]
    passed = any(
        result.get("phase") == predecessor and result.get("status") == "passed"
        for result in state.get("gate_results", [])
        if isinstance(result, dict)
    )
    if passed:
        return []
    return [f"phase {phase} requires predecessor gate passed: {predecessor}"]


def repository_records(state: dict[str, Any]) -> list[dict[str, Any]]:
    repositories = state.get("repositories", {})
    records: list[dict[str, Any]] = []
    for kind in ("dev", "test", "tools"):
        for item in repositories.get(kind, []):
            if isinstance(item, dict):
                records.append(item)
    return records


def check_repository_evidence_records(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records_by_name = {
        str(record.get("name", "")): record
        for record in repository_records(state)
        if record.get("name")
    }
    for evidence in state.get("repository_evidence", []):
        if not isinstance(evidence, dict):
            continue
        repo = str(evidence.get("repo", "")).strip()
        if not repo:
            continue
        record = records_by_name.get(repo)
        if record is None:
            errors.append(f"repository_evidence repo has no matching repository record: {repo}")
            continue
        if not any(
            record.get(field)
            for field in ("branch", "tag", "commit", "working_tree_state")
        ):
            errors.append(
                f"repository record {repo} requires branch, tag, commit, or working_tree_state"
            )
    return errors


def check_templated_artifacts(
    state: dict[str, Any], *, repo_root: Path | None = None
) -> list[str]:
    errors: list[str] = []
    root = (repo_root or AGENT_NEXT_ROOT).resolve()
    for artifact in state.get("artifacts", []):
        artifact_type = str(artifact.get("type", "")).strip()
        if artifact_type == "test_cases":
            continue
        if artifact_type not in ARTIFACT_SPECS:
            continue

        artifact_id = artifact.get("id", "<unknown>")
        try:
            path = resolve_managed_repo_path(
                str(artifact.get("path", "")).strip(), "outputs", root=root
            )
        except ValueError:
            continue
        file_errors = validate_artifact_file(
            path,
            expected_artifact_type=artifact_type,
            expected_artifact_id=str(artifact.get("id", "")).strip() or None,
        )
        for message in file_errors:
            errors.append(f"artifact {artifact_id} template validation: {message}")
    return errors


def check_test_case_artifacts(
    state: dict[str, Any], *, repo_root: Path | None = None
) -> list[str]:
    errors: list[str] = []
    root = (repo_root or AGENT_NEXT_ROOT).resolve()
    has_test_cases = False
    knowledge_paths = {
        str(item.get("path", "")).strip()
        for item in state.get("knowledge_used", [])
        if isinstance(item, dict)
    }

    for artifact in state.get("artifacts", []):
        if artifact.get("type") != "test_cases":
            continue
        has_test_cases = True
        artifact_id = artifact.get("id", "<unknown>")
        try:
            path = resolve_managed_repo_path(
                str(artifact.get("path", "")).strip(), "outputs", root=root
            )
        except ValueError:
            continue
        file_errors = validate_test_case_file(
            path,
            expected_artifact_id=str(artifact.get("id", "")).strip() or None,
        )
        for message in file_errors:
            errors.append(f"artifact {artifact_id} test case validation: {message}")

    if has_test_cases:
        required_case_references = (
            (
                TEST_CASE_DESIGN_RULES_PATH,
                "case_design_receipt:",
                "test-case-design-methodology.md",
            ),
            (
                COVERAGE_REVIEW_RULES_PATH,
                "coverage_review_receipt:",
                "coverage-review-rules.md",
            ),
            (
                CASE_RULES_PATH,
                "case_rules_receipt:",
                "case-writing-rules.md",
            ),
        )
        for path, note_prefix, filename in required_case_references:
            if path not in knowledge_paths and not has_note(state, note_prefix):
                errors.append(
                    f"test_cases artifact requires knowledge_used path {path} "
                    f"or {note_prefix} note after reading {filename}"
                )
    return errors


def check_global_state(
    state: dict[str, Any],
    *,
    verify_live_evidence: bool = True,
    repo_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    for field in REQUIRED_TOP_LEVEL:
        if field not in state:
            errors.append(f"missing top-level field: {field}")

    for field in ("run_id", "entry", "workflow", "phase"):
        if not state.get(field):
            errors.append(f"empty required field: {field}")

    if state.get("schema_version") != CURRENT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {CURRENT_SCHEMA_VERSION}")

    project_id = str(state.get("project_id", "")).strip()
    tracks = state.get("tracks", [])
    if not (project_id and isinstance(tracks, list) and tracks):
        errors.append("run identity requires project_id with tracks")

    phase_error = phase_validation_error(state.get("entry"), str(state.get("phase", "")))
    if phase_error:
        errors.append(f"phase {phase_error}")

    entry = state.get("entry")
    if entry in CANONICAL_PHASES:
        expected_workflow = workflow_readme_path(entry)
        if state.get("workflow") != expected_workflow:
            errors.append(
                f"workflow must match entry {entry}: expected {expected_workflow}, "
                f"got {state.get('workflow')!r}"
            )

    required_skills = set(state.get("required_skills", []))
    loaded_skills = set(state.get("loaded_skills", []))
    if ROUTER_SKILL not in required_skills:
        errors.append(f"required_skills must include router skill: {ROUTER_SKILL}")
    if ROUTER_SKILL not in loaded_skills:
        errors.append(f"loaded_skills must include router skill: {ROUTER_SKILL}")

    missing_skills = sorted(required_skills - loaded_skills)
    if missing_skills:
        errors.append(f"required skills not loaded: {', '.join(missing_skills)}")

    receipt_skills = {receipt.get("skill") for receipt in state.get("skill_receipts", [])}
    missing_receipts = sorted(required_skills - receipt_skills)
    if missing_receipts:
        errors.append(f"required skill receipts missing: {', '.join(missing_receipts)}")

    current_phase = normalize_phase(str(state.get("phase", "")), entry)
    for receipt in state.get("skill_receipts", []):
        skill = receipt.get("skill", "<unknown>")
        for field in ("skill", "path", "sha256", "supports_phase"):
            if not receipt.get(field):
                errors.append(f"skill receipt {skill} missing field: {field}")
        sha256 = receipt.get("sha256", "")
        if sha256 and len(sha256) != 64:
            errors.append(f"skill receipt {skill} has invalid sha256")
        if verify_live_evidence:
            raw_path = str(receipt.get("path", "")).strip()
            if raw_path and Path(raw_path).is_absolute():
                errors.append(f"skill receipt {skill} path must be repo-relative")
            elif raw_path:
                root = (repo_root or AGENT_NEXT_ROOT).resolve()
                path = resolve_repo_path(raw_path, root=root)
                try:
                    in_skills = path.resolve().is_relative_to((root / "skills").resolve())
                except OSError:
                    in_skills = False
                if not in_skills:
                    errors.append(f"skill receipt {skill} path must be under skills/: {raw_path}")
                elif not path.is_file():
                    errors.append(f"skill receipt {skill} path does not exist: {raw_path}")
                elif (
                    skill in required_skills
                    and receipt.get("supports_phase") == current_phase
                    and len(sha256) == 64
                    and sha256_file(path) != sha256
                ):
                    errors.append(f"skill receipt {skill} sha256 does not match current file: {raw_path}")

    if verify_live_evidence:
        invalid_current_receipts = sorted(
            required_skills
            - valid_receipt_skills(state, current_phase, repo_root=repo_root)
        )
        if invalid_current_receipts:
            errors.append(
                "required skill receipts are missing, stale, or for another phase: "
                + ", ".join(invalid_current_receipts)
            )

    knowledge_plan = state.get("knowledge_plan", {})
    status = knowledge_plan.get("status")
    if status not in VALID_KNOWLEDGE_PLAN_STATUSES:
        errors.append("knowledge_plan.status is invalid")
    if "summary" not in knowledge_plan or not isinstance(knowledge_plan.get("summary"), str):
        errors.append("knowledge_plan.summary must be a string")

    environment = state.get("environment", {})
    required_env = set(environment.get("required_groups", []))
    checked_env = set(environment.get("checked_groups", []))
    missing_env = sorted(required_env - checked_env)
    if missing_env:
        errors.append(f"required env groups not checked: {', '.join(missing_env)}")

    for confirmation in state.get("confirmations", []):
        status = confirmation.get("status")
        if status in {"required", "rejected"}:
            action = confirmation.get("action", confirmation.get("id", "<unknown>"))
            errors.append(f"confirmation not satisfied: {action} ({status})")

    for artifact in state.get("artifacts", []):
        artifact_id = artifact.get("id", "<unknown>")
        for field in ARTIFACT_REQUIRED:
            if field not in artifact:
                errors.append(f"artifact {artifact_id} missing field: {field}")
        validation = artifact.get("validation", {})
        if "status" not in validation:
            errors.append(f"artifact {artifact_id} missing validation.status")
        path = str(artifact.get("path", "")).strip()
        if path:
            try:
                resolve_managed_repo_path(path, "outputs")
            except ValueError as exc:
                errors.append(f"artifact {artifact_id} has invalid output path: {exc}")

    errors.extend(check_repository_evidence_records(state))
    errors.extend(check_templated_artifacts(state, repo_root=repo_root))
    errors.extend(check_test_case_artifacts(state, repo_root=repo_root))
    if verify_live_evidence:
        errors.extend(check_recorded_reference_paths(state, repo_root=repo_root))
        errors.extend(lint_run_state_traceability(state, repo_root=repo_root))

    return errors


def check_phase_skills(
    state: dict[str, Any],
    rule: dict[str, Any],
    phase: str,
    *,
    repo_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    required_skills = set(rule.get("required_skills", []))
    required_skills.add(ROUTER_SKILL)

    declared = set(state.get("required_skills", []))
    loaded = set(state.get("loaded_skills", []))
    receipts = valid_receipt_skills(state, phase, repo_root=repo_root)

    missing_declared = sorted(required_skills - declared)
    if missing_declared:
        errors.append(f"phase {phase} must declare required skills: {', '.join(missing_declared)}")

    missing_loaded = sorted(required_skills - loaded)
    if missing_loaded:
        errors.append(f"phase {phase} requires loaded skills: {', '.join(missing_loaded)}")

    missing_receipts = sorted(required_skills - receipts)
    if missing_receipts:
        errors.append(f"phase {phase} requires skill receipts: {', '.join(missing_receipts)}")

    any_skills = rule.get("required_skills_any", [])
    if any_skills:
        if not any(skill in declared and skill in loaded and skill in receipts for skill in any_skills):
            errors.append(
                f"phase {phase} requires at least one loaded skill from: {', '.join(any_skills)}"
            )

    return errors


def check_phase_rules(state: dict[str, Any], *, repo_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    entry = state.get("entry")
    phase = normalize_phase(str(state.get("phase", "")), entry)
    rule = PHASE_RULES.get((entry, phase))
    if not rule:
        return [f"unknown or unsupported phase for entry {entry!r}: {phase!r}"]

    errors.extend(check_predecessor_gate(state, entry, phase))

    if rule.get("optional") and has_optional_skip(state, phase):
        return errors

    errors.extend(check_phase_skills(state, rule, phase, repo_root=repo_root))

    present_types = artifact_types(state)
    for artifact_type in rule.get("artifact_types", []):
        if artifact_type not in present_types:
            errors.append(f"phase {phase} requires artifact type: {artifact_type}")

    if rule.get("optional"):
        optional_types = rule.get("optional_artifact_types", [])
        prefixes = rule.get("require_note_prefixes", [])
        has_evidence = bool(present_types & set(optional_types)) if optional_types else True
        if prefixes:
            has_evidence = has_evidence or any(has_note(state, prefix) for prefix in prefixes)
        if optional_types and not has_evidence:
            hint_parts = [f"skip note {f'optional_skip:{phase}:'}"]
            if prefixes:
                hint_parts.append(f"note prefixes {', '.join(prefixes)}")
            errors.append(
                f"phase {phase} requires optional artifact types {', '.join(optional_types)} "
                f"or {' or '.join(hint_parts)}"
            )
    elif rule.get("optional_artifact_types"):
        # Non-optional phase that accepts execution evidence via artifact or note.
        optional_types = set(rule.get("optional_artifact_types", []))
        if not (present_types & optional_types):
            for prefix in rule.get("require_note_prefixes", []):
                if has_note(state, prefix):
                    break
            else:
                if rule.get("require_note_prefixes"):
                    pass
                elif optional_types:
                    errors.append(
                        f"phase {phase} requires one of artifact types: {', '.join(sorted(optional_types))}"
                    )

    if rule.get("knowledge") and not state.get("knowledge_used") and not has_note(state, "knowledge_not_applicable:"):
        errors.append(f"phase {phase} requires knowledge_used or knowledge_not_applicable note")

    if (
        rule.get("repository_evidence")
        and not state.get("repository_evidence")
        and not has_note(state, "repository_not_applicable:")
    ):
        errors.append(f"phase {phase} requires repository_evidence or repository_not_applicable note")

    if rule.get("repository_evidence") and state.get("repository_evidence"):
        records = repository_records(state)
        if records and not any(
            record.get("branch") or record.get("tag") or record.get("commit") or record.get("working_tree_state")
            for record in records
        ):
            errors.append(
                f"phase {phase} requires repository branch, tag, commit, or working_tree_state "
                "when repository_evidence is recorded"
            )

    if rule.get("knowledge_plan_resolved"):
        plan_status = state.get("knowledge_plan", {}).get("status")
        if plan_status not in RESOLVED_KNOWLEDGE_PLAN_STATUSES:
            errors.append(f"phase {phase} requires knowledge_plan.status to be resolved (not pending)")

    if rule.get("require_intake_input") and not has_note(state, "intake_input:"):
        errors.append(f"phase {phase} requires intake_input note")

    if rule.get("require_bug_intake") and not has_note(state, "bug_intake:"):
        errors.append(f"phase {phase} requires bug_intake note")

    if rule.get("require_environment_target") and not str(state.get("environment", {}).get("target", "")).strip():
        errors.append(f"phase {phase} requires environment.target")

    if rule.get("require_release_scope_tracks") and not release_scope_tracks(state):
        errors.append(f"phase {phase} requires release_scope_tracks")

    always_prefixes = rule.get("require_note_prefixes_always", [])
    if always_prefixes and not any(has_note(state, prefix) for prefix in always_prefixes):
        errors.append(f"phase {phase} requires note prefix: {', '.join(always_prefixes)}")

    prefixes = rule.get("require_note_prefixes", [])
    if prefixes and not rule.get("optional_artifact_types"):
        if not any(has_note(state, prefix) for prefix in prefixes):
            errors.append(f"phase {phase} requires note prefix: {', '.join(prefixes)}")
    elif prefixes and rule.get("optional_artifact_types"):
        if not (present_types & set(rule.get("optional_artifact_types", []))) and not any(
            has_note(state, prefix) for prefix in prefixes
        ):
            errors.append(
                f"phase {phase} requires one of artifact types {', '.join(rule.get('optional_artifact_types', []))} "
                f"or note prefixes {', '.join(prefixes)}"
            )

    if rule.get("traceability") and not state.get("traceability"):
        errors.append(f"phase {phase} requires traceability links")

    if (
        entry == "bug-regression"
        and phase == "Regression Plan"
        and any(note.startswith("decision_path:") and "supplement_cases" in note for note in state.get("notes", []))
        and "test_cases" not in present_types
    ):
        errors.append(
            "phase Regression Plan requires artifact type: test_cases when decision_path is supplement_cases"
        )

    return errors


def check_state(
    state: dict[str, Any],
    strict_phase: bool = False,
    *,
    repo_root: Path | None = None,
) -> list[str]:
    errors = check_global_state(state, repo_root=repo_root)
    if strict_phase:
        errors.extend(check_phase_rules(state, repo_root=repo_root))
    return errors


def state_path_from_args(args: argparse.Namespace) -> Path:
    if args.state:
        return resolve_repo_path(args.state)
    return resolve_repo_path(args.runs_root) / args.run_id / "state.json"


def write_gate_result(path: Path, state: dict[str, Any], errors: list[str]) -> None:
    result = {
        "phase": normalize_phase(str(state.get("phase", "")), state.get("entry")),
        "status": "failed" if errors else "passed",
        "checks": [
            {
                "name": "stage_gate",
                "status": "failed" if errors else "passed",
                "details": "; ".join(errors) if errors else "all checks passed",
            }
        ],
    }
    gate_results = state.setdefault("gate_results", [])
    for index, existing in enumerate(gate_results):
        if existing.get("phase") == result["phase"]:
            gate_results[index] = result
            break
    else:
        gate_results.append(result)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--runs-root", type=Path, default=AGENT_NEXT_ROOT / "runs")
    parser.add_argument("--entry", choices=["feature-quality", "bug-regression", "release-acceptance"])
    parser.add_argument("--phase")
    parser.add_argument("--global-only", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if not args.state and not args.run_id:
        parser.error("one of --state or --run-id is required")
    return args


def main() -> int:
    args = parse_args()
    path = state_path_from_args(args)
    state = load_state(path)
    if args.entry and state.get("entry") != args.entry:
        state["entry"] = args.entry
    if args.phase:
        entry = state.get("entry") or args.entry
        state["phase"] = normalize_phase(args.phase, entry)
    errors = check_state(state, strict_phase=not args.global_only)
    if not args.no_write:
        write_gate_result(path, state, errors)
    if args.format == "json":
        print(json.dumps({"status": "failed" if errors else "passed", "errors": errors}, indent=2))
    elif errors:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
    else:
        print("PASSED")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
