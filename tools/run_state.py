#!/usr/bin/env python3
"""Create or update an agent-next run state file."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import AGENT_NEXT_ROOT, as_logical_path, resolve_repo_path  # noqa: E402
from phases import normalize_phase, workflow_readme_path  # noqa: E402
from run_state_schema import CURRENT_SCHEMA_VERSION, detect_schema_version  # noqa: E402


DEFAULT_ROOT = AGENT_NEXT_ROOT / "runs"
VALID_KNOWLEDGE_PLAN_STATUSES = {"pending", "not_needed", "proposed", "confirmed", "rejected"}


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def default_state(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "run_id": run_id,
        "project_id": "",
        "tracks": [],
        # Legacy Agent-next compatibility. New runs use project_id + tracks.
        "product_line": "",
        "release_scope_tracks": [],
        "entry": "",
        "workflow": "",
        "phase": "",
        "required_skills": [],
        "loaded_skills": [],
        "skill_receipts": [],
        "repositories": {"dev": [], "test": [], "tools": []},
        "repository_evidence": [],
        "knowledge_used": [],
        "knowledge_plan": {
            "status": "pending",
            "summary": "",
            "evidence": [],
        },
        "knowledge_proposed_updates": [],
        "environment": {
            "required_groups": [],
            "checked_groups": [],
            "target": "",
        },
        "confirmations": [],
        "artifacts": [],
        "traceability": [],
        "gate_results": [],
        "notes": [],
    }


def load_state(path: Path, run_id: str) -> dict[str, Any]:
    if not path.exists():
        return default_state(run_id)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("run_id") != run_id:
        raise ValueError(f"state run_id mismatch: expected {run_id!r}, got {data.get('run_id')!r}")
    version = detect_schema_version(data)
    if version != CURRENT_SCHEMA_VERSION:
        shown = "invalid" if version is None else f"v{version}"
        raise ValueError(
            f"state schema version is {shown}; run tools/migrate_run_state.py --state {path} first"
        )
    return data


def update_state(args: argparse.Namespace) -> Path:
    run_dir = resolve_repo_path(args.runs_root) / args.run_id
    state_path = run_dir / "state.json"
    state = load_state(state_path, args.run_id)

    if args.entry:
        state["entry"] = args.entry
        if args.workflow:
            state["workflow"] = args.workflow
        elif not state.get("workflow"):
            state["workflow"] = workflow_readme_path(args.entry)
    elif args.workflow:
        state["workflow"] = args.workflow
    if args.phase:
        entry = state.get("entry") or args.entry
        state["phase"] = normalize_phase(args.phase, entry)

    if getattr(args, "project_id", None):
        state["project_id"] = args.project_id
    if getattr(args, "track", []):
        state["tracks"] = unique(state.get("tracks", []) + args.track)
    if getattr(args, "product_line", None):
        state["product_line"] = args.product_line
    if getattr(args, "release_scope_track", []):
        state["release_scope_tracks"] = unique(state.get("release_scope_tracks", []) + args.release_scope_track)

    if args.required_skill:
        state["required_skills"] = unique(state["required_skills"] + args.required_skill)
    if args.loaded_skill:
        state["loaded_skills"] = unique(state["loaded_skills"] + args.loaded_skill)
    if args.skill_receipt:
        state["skill_receipts"] = upsert_skill_receipts(
            state.get("skill_receipts", []),
            args.skill_receipt,
            state.get("phase", ""),
        )

    env = state.setdefault("environment", {})
    env.setdefault("required_groups", [])
    env.setdefault("checked_groups", [])
    env.setdefault("target", "")
    if args.required_env:
        env["required_groups"] = unique(env["required_groups"] + args.required_env)
    if args.checked_env:
        env["checked_groups"] = unique(env["checked_groups"] + args.checked_env)
    if args.target:
        env["target"] = args.target

    if getattr(args, "repository", []):
        add_repositories(state, args.repository)
    if getattr(args, "repository_evidence", []):
        state["repository_evidence"].extend(parse_repository_evidence(value) for value in args.repository_evidence)
    if getattr(args, "knowledge_used", []):
        state["knowledge_used"].extend(parse_knowledge_used(value) for value in args.knowledge_used)
    update_knowledge_plan(state, args)
    if getattr(args, "knowledge_proposed_update", []):
        state["knowledge_proposed_updates"] = upsert_by_path(
            state.get("knowledge_proposed_updates", []),
            [parse_kv_record(value, required=["path", "summary", "status"]) for value in args.knowledge_proposed_update],
        )
    if getattr(args, "confirmation", []):
        state["confirmations"] = upsert_by_id(
            state.get("confirmations", []),
            [parse_kv_record(value, required=["id", "action", "status"]) for value in args.confirmation],
        )
    if getattr(args, "trace", []):
        state["traceability"].extend(parse_kv_record(value, required=["from", "to", "relation"]) for value in args.trace)
    if getattr(args, "gate_result", []):
        state["gate_results"].extend(json.loads(value) for value in args.gate_result)
    if getattr(args, "note", []):
        state["notes"] = unique(state.get("notes", []) + args.note)

    run_dir.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return state_path


def parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_kv_record(value: str, required: list[str] | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for part in value.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"expected key=value segment in: {value}")
        key, raw = part.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if key in {"references", "supports", "used_for", "source_artifacts", "evidence"}:
            record[key] = parse_csv(raw)
        else:
            record[key] = raw
    for key in required or []:
        if key not in record or record[key] == "" or record[key] == []:
            raise ValueError(f"missing required key {key!r} in: {value}")
    return record


def upsert_by_id(current: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = list(current)
    for record in records:
        record_id = record.get("id")
        for index, existing in enumerate(result):
            if existing.get("id") == record_id:
                result[index] = record
                break
        else:
            result.append(record)
    return result


def upsert_by_path(current: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = list(current)
    for record in records:
        record_path = record.get("path")
        for index, existing in enumerate(result):
            if existing.get("path") == record_path:
                result[index] = record
                break
        else:
            result.append(record)
    return result


def normalize_knowledge_plan_status(value: str) -> str:
    status = value.strip().replace("-", "_")
    if status not in VALID_KNOWLEDGE_PLAN_STATUSES:
        allowed = ", ".join(sorted(VALID_KNOWLEDGE_PLAN_STATUSES))
        raise ValueError(f"knowledge plan status must be one of: {allowed}")
    return status


def update_knowledge_plan(state: dict[str, Any], args: argparse.Namespace) -> None:
    status = getattr(args, "knowledge_plan_status", None)
    summary = getattr(args, "knowledge_plan_summary", None)
    evidence = getattr(args, "knowledge_plan_evidence", [])
    confirmed_by = getattr(args, "knowledge_plan_confirmed_by", None)
    confirmed_at = getattr(args, "knowledge_plan_confirmed_at", None)
    if not any([status, summary, evidence, confirmed_by, confirmed_at]):
        return

    plan = state.setdefault("knowledge_plan", {"status": "pending", "summary": "", "evidence": []})
    plan.setdefault("status", "pending")
    plan.setdefault("summary", "")
    plan.setdefault("evidence", [])
    if status:
        plan["status"] = normalize_knowledge_plan_status(status)
    if summary is not None:
        plan["summary"] = summary
    if evidence:
        plan["evidence"] = unique(plan.get("evidence", []) + evidence)
    if confirmed_by:
        plan["confirmed_by"] = confirmed_by
    if confirmed_at:
        plan["confirmed_at"] = confirmed_at


def add_repositories(state: dict[str, Any], repository_args: list[str]) -> None:
    repositories = state.setdefault("repositories", {"dev": [], "test": [], "tools": []})
    for value in repository_args:
        record = parse_kv_record(value, required=["kind", "name", "path"])
        kind = record["kind"]
        if kind not in {"dev", "test", "tools"}:
            raise ValueError(f"repository kind must be dev, test, or tools: {kind}")
        bucket = repositories.setdefault(kind, [])
        for index, existing in enumerate(bucket):
            if existing.get("name") == record["name"]:
                bucket[index] = record
                break
        else:
            bucket.append(record)


def parse_repository_evidence(value: str) -> dict[str, Any]:
    record = parse_kv_record(value, required=["repo", "evidence_type"])
    if "reference" in record:
        record["references"] = [record.pop("reference")]
    record.setdefault("references", [])
    record.setdefault("supports", [])
    if not record["references"]:
        raise ValueError(f"repository evidence requires reference or references: {value}")
    return record


def parse_knowledge_used(value: str) -> dict[str, Any]:
    record = parse_kv_record(value, required=["path"])
    if "purpose" in record:
        record["used_for"] = [record.pop("purpose")]
    record.setdefault("used_for", [])
    if not record["used_for"]:
        raise ValueError(f"knowledge_used requires purpose or used_for: {value}")
    return record


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_skill_receipt(value: str) -> tuple[str, Path, str]:
    if "=" not in value:
        raise ValueError(f"skill receipt must use skill=path format: {value}")
    skill, raw_path = value.split("=", 1)
    if not skill or not raw_path:
        raise ValueError(f"skill receipt must use skill=path format: {value}")
    logical = as_logical_path(raw_path)
    return skill, resolve_repo_path(raw_path), logical


def upsert_skill_receipts(
    current: list[dict[str, Any]],
    receipt_args: list[str],
    phase: str,
) -> list[dict[str, Any]]:
    receipts = list(current)
    for value in receipt_args:
        skill, path, logical_path = parse_skill_receipt(value)
        if not path.exists():
            raise FileNotFoundError(f"skill receipt path not found: {logical_path}")
        record = {
            "skill": skill,
            "path": logical_path,
            "sha256": sha256_file(path),
            "supports_phase": phase,
        }
        for index, existing in enumerate(receipts):
            if existing.get("skill") == skill and existing.get("path") == logical_path:
                receipts[index] = record
                break
        else:
            receipts.append(record)
    return receipts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--project-id", help="Project Profile project.id for this run.")
    parser.add_argument("--track", action="append", default=[], help="Project-defined owning track; repeatable.")
    parser.add_argument(
        "--product-line",
        help="Legacy compatibility field. Prefer --project-id and --track for new runs.",
    )
    parser.add_argument("--release-scope-track", action="append", default=[])
    parser.add_argument("--entry", choices=["feature-quality", "bug-regression", "release-acceptance"])
    parser.add_argument("--workflow")
    parser.add_argument("--phase")
    parser.add_argument("--required-skill", action="append", default=[])
    parser.add_argument("--loaded-skill", action="append", default=[])
    parser.add_argument(
        "--skill-receipt",
        action="append",
        default=[],
        help="Record a loaded skill as skill=path and store the file sha256.",
    )
    parser.add_argument("--required-env", action="append", default=[])
    parser.add_argument("--checked-env", action="append", default=[])
    parser.add_argument("--target")
    parser.add_argument("--repository", action="append", default=[], help="kind=dev,name=repo,path=repositories/dev/repo[,commit=...]")
    parser.add_argument("--repository-evidence", action="append", default=[], help="repo=name,evidence_type=file,reference=path[,supports=id1|id2]")
    parser.add_argument("--knowledge-used", action="append", default=[], help="path=knowledge/...,purpose=...")
    parser.add_argument("--knowledge-plan-status", help="pending|not-needed|proposed|confirmed|rejected")
    parser.add_argument("--knowledge-plan-summary")
    parser.add_argument("--knowledge-plan-evidence", action="append", default=[])
    parser.add_argument("--knowledge-plan-confirmed-by")
    parser.add_argument("--knowledge-plan-confirmed-at")
    parser.add_argument("--knowledge-proposed-update", action="append", default=[], help="path=knowledge/...,summary=...,status=proposed|confirmed|rejected")
    parser.add_argument("--confirmation", action="append", default=[], help="id=...,action=...,status=required|confirmed|rejected|not_required")
    parser.add_argument("--trace", action="append", default=[], help="from=REQ-1,to=RISK-1,relation=covers")
    parser.add_argument("--gate-result", action="append", default=[], help="JSON gate result to append")
    parser.add_argument("--note", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    path = update_state(parse_args())
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
