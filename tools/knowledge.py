from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

import yaml

from .contracts import ContractError, load_yaml, validate_schema
from .run_state import load_state


class KnowledgeError(ValueError):
    """Raised when a knowledge proposal cannot be recorded or confirmed safely."""


def load_proposals(root: Path, proposal_files: Sequence[Path]) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    repository_root = root.resolve()
    for supplied_path in proposal_files:
        path = (
            supplied_path
            if supplied_path.is_absolute()
            else repository_root / supplied_path
        )
        try:
            path.resolve().relative_to(repository_root)
        except ValueError as exc:
            raise KnowledgeError(
                "knowledge proposal must be under the repository root: "
                f"{supplied_path}"
            ) from exc
        try:
            proposal = load_yaml(path)
        except ContractError as exc:
            raise KnowledgeError(str(exc)) from exc
        errors = validate_schema(proposal, "knowledge-proposal")
        if errors:
            raise KnowledgeError(
                f"invalid knowledge proposal {supplied_path}: " + "; ".join(errors)
            )
        logical_path = PurePosixPath(str(proposal["path"]))
        if logical_path.is_absolute() or ".." in logical_path.parts:
            raise KnowledgeError(
                f"knowledge proposal path must be repository-relative: {proposal['path']}"
            )
        record = {key: value for key, value in proposal.items() if key != "schema_version"}
        record["status"] = "proposed"
        proposals.append(record)
    return proposals


def record_proposals(state: dict[str, Any], proposals: Sequence[dict[str, Any]]) -> None:
    records = list(state.get("knowledge_proposed_updates", []))
    for proposal in proposals:
        for index, current in enumerate(records):
            if current.get("path") == proposal["path"]:
                if current.get("status") == "confirmed":
                    raise KnowledgeError(
                        f"knowledge proposal is already confirmed: {proposal['path']}"
                    )
                records[index] = dict(proposal)
                break
        else:
            records.append(dict(proposal))
    state["knowledge_proposed_updates"] = records
    if proposals:
        state["knowledge_plan"]["status"] = "proposed"
        if not state["knowledge_plan"].get("summary"):
            state["knowledge_plan"]["summary"] = (
                f"{len(proposals)} reusable knowledge proposal(s) await confirmation."
            )


def pending_proposals(
    state: dict[str, Any], source_artifact: str | None = None
) -> list[dict[str, Any]]:
    return [
        item
        for item in state.get("knowledge_proposed_updates", [])
        if item.get("status") == "proposed"
        and (source_artifact is None or item.get("source_artifact") == source_artifact)
    ]


def _knowledge_id(project_id: str, relative_path: Path) -> str:
    logical = "-".join(relative_path.with_suffix("").parts)
    logical = re.sub(r"[^A-Za-z0-9._-]+", "-", logical).strip("-") or "knowledge"
    return f"{project_id}-{logical}"


def confirm_proposals(
    *,
    root: Path,
    profile: dict[str, Any],
    run_id: str,
    source_artifact: str,
    confirmed_by: str,
) -> list[Path]:
    repository_root = root.resolve()
    state_path = repository_root / "runs" / run_id / "state.json"
    try:
        state = load_state(state_path, run_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise KnowledgeError(f"invalid run state: {exc}") from exc

    source = next(
        (item for item in state.get("artifacts", []) if item.get("id") == source_artifact),
        None,
    )
    if source is None or source.get("type") != "requirement_spec":
        raise KnowledgeError(
            f"confirmed source must be a requirement_spec: {source_artifact}"
        )
    if source.get("validation", {}).get("status") != "passed":
        raise KnowledgeError(f"requirement artifact has not passed its gate: {source_artifact}")

    proposals = pending_proposals(state, source_artifact)
    if not proposals:
        raise KnowledgeError(f"no pending knowledge proposals for {source_artifact}")

    knowledge_root = (repository_root / profile["knowledge"]["root"]).resolve()
    index_path = (repository_root / profile["knowledge"]["index"]).resolve()
    if not index_path.is_file():
        raise KnowledgeError(
            f"knowledge index does not exist: {profile['knowledge']['index']}"
        )
    confirmed_at = datetime.now(UTC).isoformat()
    planned: list[tuple[dict[str, Any], Path, str]] = []
    for proposal in proposals:
        missing = [
            field
            for field in ("path", "title", "type", "summary", "content", "source_artifact")
            if not proposal.get(field)
        ]
        if missing:
            raise KnowledgeError(
                f"knowledge proposal {proposal.get('path', '<unknown>')} cannot be confirmed; "
                f"missing: {', '.join(missing)}"
            )
        target = (repository_root / str(proposal["path"])).resolve()
        try:
            relative = target.relative_to(knowledge_root)
        except ValueError as exc:
            raise KnowledgeError(
                f"knowledge proposal must stay under {profile['knowledge']['root']}: {proposal['path']}"
            ) from exc
        if target.exists():
            raise KnowledgeError(
                f"knowledge target already exists and requires separate review: {proposal['path']}"
            )
        frontmatter = {
            "id": _knowledge_id(profile["project"]["id"], relative),
            "title": proposal["title"],
            "type": proposal["type"],
            "sources": [{"type": "user_confirmation", "reference": source_artifact}],
            "confidence": "confirmed",
            "last_verified": confirmed_at[:10],
        }
        page_errors = validate_schema(frontmatter, "knowledge-page")
        if page_errors:
            raise KnowledgeError(
                f"generated knowledge page is invalid for {proposal['path']}: "
                + "; ".join(page_errors)
            )
        document = (
            "---\n"
            + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).rstrip()
            + "\n---\n\n# "
            + str(proposal["title"]).strip()
            + "\n\n"
            + str(proposal["content"]).strip()
            + "\n"
        )
        planned.append((proposal, target, document))

    written: list[Path] = []
    for proposal, target, document in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("x", encoding="utf-8") as file:
                file.write(document)
        except FileExistsError as exc:
            raise KnowledgeError(
                f"knowledge target already exists and requires separate review: {proposal['path']}"
            ) from exc
        written.append(target.relative_to(repository_root))
        proposal["status"] = "confirmed"
        proposal["confirmed_by"] = confirmed_by
        proposal["confirmed_at"] = confirmed_at

    index = index_path.read_text(encoding="utf-8")
    heading = "## Confirmed knowledge"
    if heading not in index:
        index = index.rstrip() + f"\n\n{heading}\n"
    for proposal, target, _document in planned:
        link = target.relative_to(index_path.parent).as_posix()
        entry = f"- [{proposal['title']}]({link})"
        if entry not in index:
            index += f"\n{entry}"
    index_path.write_text(index.rstrip() + "\n", encoding="utf-8")

    if not pending_proposals(state):
        state["knowledge_plan"]["status"] = "confirmed"
        state["knowledge_plan"]["confirmed_by"] = confirmed_by
        state["knowledge_plan"]["confirmed_at"] = confirmed_at
    state["knowledge_plan"]["evidence"] = list(
        dict.fromkeys(
            [
                *state["knowledge_plan"].get("evidence", []),
                *(path.as_posix() for path in written),
            ]
        )
    )
    confirmation = {
        "id": f"confirm-requirement-and-knowledge-{source_artifact}",
        "action": f"confirm requirement {source_artifact} and persist listed knowledge",
        "status": "confirmed",
        "confirmed_by": confirmed_by,
        "confirmed_at": confirmed_at,
    }
    confirmations = list(state.get("confirmations", []))
    for index, current in enumerate(confirmations):
        if current.get("id") == confirmation["id"]:
            confirmations[index] = confirmation
            break
    else:
        confirmations.append(confirmation)
    state["confirmations"] = confirmations
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return written
