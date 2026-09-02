from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .phases import normalize_phase, phase_doc_path, workflow_readme_path
from .planner import CapabilityRecord
from .knowledge import KnowledgeError, load_proposals, record_proposals
from .run_state import default_state, load_state as load_run_state, parse_knowledge_used, sha256_file
from .stage_gate import PHASE_RULES, ROUTER_SKILL, check_state, write_gate_result


class LifecycleError(ValueError):
    """Raised when a generic run cannot be prepared safely."""


@dataclass(frozen=True)
class RunPreparation:
    state_path: Path
    state: dict[str, Any]


def required_skills_for(capability: CapabilityRecord) -> list[str]:
    metadata = capability.metadata
    entry = str(metadata["workflow"])
    phase = normalize_phase(str(metadata["phase"]), entry)
    rule = PHASE_RULES.get((entry, phase), {})
    skills = [ROUTER_SKILL, *rule.get("required_skills", [])]
    capability_skill = str(metadata["skill"])
    if capability_skill not in skills:
        skills.append(capability_skill)
    if rule.get("required_skills_any") and not any(
        skill in skills for skill in rule["required_skills_any"]
    ):
        skills.append(str(rule["required_skills_any"][0]))
    return list(dict.fromkeys(skills))


def prepare_run(
    *,
    root: Path,
    profile: dict[str, Any],
    capability: CapabilityRecord,
    run_id: str,
    tracks: Sequence[str],
) -> RunPreparation:
    root = root.resolve()
    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise LifecycleError("run id must be a safe single path segment")
    project_tracks = set(profile["project"]["tracks"])
    if not tracks or len(set(tracks)) != len(tracks) or set(tracks) - project_tracks:
        raise LifecycleError("run tracks must be declared by the project")

    metadata = capability.metadata
    entry = str(metadata["workflow"])
    phase = normalize_phase(str(metadata["phase"]), entry)
    state_path = root / "runs" / run_id / "state.json"
    if state_path.exists():
        try:
            state = load_run_state(state_path, run_id)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise LifecycleError(f"invalid run state: {exc}") from exc
        existing_project = str(state.get("project_id", ""))
        if existing_project and existing_project != profile["project"]["id"]:
            raise LifecycleError(
                f"run {run_id} belongs to project {existing_project}, not {profile['project']['id']}"
            )
    else:
        state = default_state(run_id)

    state["project_id"] = profile["project"]["id"]
    state["tracks"] = list(tracks)
    state["entry"] = entry
    state["workflow"] = workflow_readme_path(entry)
    state["phase"] = phase
    if entry == "release-acceptance":
        state["release_scope_tracks"] = list(tracks)

    required_skills = required_skills_for(capability)
    state["required_skills"] = required_skills
    state["loaded_skills"] = required_skills
    receipts = []
    for skill in required_skills:
        logical_path = Path("skills") / skill / "SKILL.md"
        absolute_path = root / logical_path
        if not absolute_path.is_file():
            raise LifecycleError(f"required skill does not exist: {logical_path}")
        absolute_path.read_text(encoding="utf-8")
        receipts.append(
            {
                "skill": skill,
                "path": logical_path.as_posix(),
                "sha256": sha256_file(absolute_path),
                "supports_phase": phase,
            }
        )
    other_receipts = [
        item
        for item in state.get("skill_receipts", [])
        if item.get("supports_phase") != phase
    ]
    state["skill_receipts"] = [*other_receipts, *receipts]
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return RunPreparation(state_path=state_path.relative_to(root), state=state)


def load_run(root: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    path = root.resolve() / "runs" / run_id / "state.json"
    try:
        state = load_run_state(path, run_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise LifecycleError(f"invalid run state: {exc}") from exc
    return path, state


def run_status(root: Path, run_id: str) -> tuple[dict[str, Any], list[str]]:
    _path, state = load_run(root, run_id)
    return state, check_state(state, strict_phase=True, repo_root=root)


def explain_run(root: Path, run_id: str) -> dict[str, Any]:
    state, blockers = run_status(root, run_id)
    entry = str(state.get("entry", ""))
    phase = str(state.get("phase", ""))
    return {
        "run_id": run_id,
        "project_id": state.get("project_id"),
        "tracks": state.get("tracks", []),
        "workflow": state.get("workflow"),
        "phase": phase,
        "phase_doc": phase_doc_path(entry, phase),
        "required_skills": state.get("required_skills", []),
        "artifacts": state.get("artifacts", []),
        "blockers": blockers,
    }


def record_run_evidence(
    *,
    root: Path,
    run_id: str,
    knowledge_used: Sequence[str],
    knowledge_plan_status: str | None,
    knowledge_plan_summary: str | None,
    knowledge_plan_evidence: Sequence[str],
    notes: Sequence[str],
    knowledge_proposal_files: Sequence[Path] = (),
) -> Path:
    path, state = load_run(root, run_id)
    if knowledge_used:
        state["knowledge_used"].extend(parse_knowledge_used(value) for value in knowledge_used)
    if knowledge_plan_status:
        if knowledge_plan_status not in {
            "pending",
            "not_needed",
            "proposed",
            "confirmed",
            "rejected",
        }:
            raise LifecycleError("invalid knowledge plan status")
        state["knowledge_plan"]["status"] = knowledge_plan_status
    if knowledge_plan_summary is not None:
        state["knowledge_plan"]["summary"] = knowledge_plan_summary
    if knowledge_plan_evidence:
        state["knowledge_plan"]["evidence"].extend(knowledge_plan_evidence)
    if notes:
        state["notes"] = list(dict.fromkeys([*state.get("notes", []), *notes]))
    if knowledge_proposal_files:
        try:
            record_proposals(state, load_proposals(root, knowledge_proposal_files))
        except KnowledgeError as exc:
            raise LifecycleError(str(exc)) from exc
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def gate_run(root: Path, run_id: str) -> list[str]:
    path, state = load_run(root, run_id)
    errors = check_state(state, strict_phase=True, repo_root=root)
    write_gate_result(path, state, errors)
    return errors
