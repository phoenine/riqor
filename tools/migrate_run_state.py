#!/usr/bin/env python3
"""Audit or safely migrate legacy agent-next run-state files to the current schema."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import AGENT_NEXT_ROOT, resolve_repo_path  # noqa: E402
from phases import workflow_readme_path  # noqa: E402
from run_state_schema import (  # noqa: E402
    CURRENT_SCHEMA_VERSION,
    LEGACY_SCHEMA_VERSION,
    detect_schema_version,
)
from validate_run_state import (  # noqa: E402
    DEFAULT_SCHEMA,
    check_schema,
    check_semantic_rules,
    load_json,
)


LEGACY_WORKFLOW_VALUES = {
    entry: {entry, f"workflows/{entry}.md"}
    for entry in ("feature-quality", "bug-regression", "release-acceptance")
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_skill_receipt_path(receipt: dict[str, Any]) -> str | None:
    raw_path = str(receipt.get("path", ""))
    if not Path(raw_path).is_absolute():
        return None
    skill = str(receipt.get("skill", "")).strip()
    expected_sha = str(receipt.get("sha256", "")).strip()
    if not skill or len(expected_sha) != 64:
        return None
    logical_path = f"skills/{skill}/SKILL.md"
    local_path = AGENT_NEXT_ROOT / logical_path
    if local_path.is_file() and sha256_file(local_path) == expected_sha:
        return logical_path
    return None


def build_candidate(state: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    candidate = copy.deepcopy(state)
    actions: list[dict[str, Any]] = []
    blockers: list[str] = []
    version = detect_schema_version(state)

    if version is None:
        return candidate, actions, ["schema_version must be an integer"]
    if version == CURRENT_SCHEMA_VERSION:
        return candidate, actions, blockers
    if version != LEGACY_SCHEMA_VERSION:
        return candidate, actions, [
            f"unsupported schema_version {version}; expected {LEGACY_SCHEMA_VERSION} or {CURRENT_SCHEMA_VERSION}"
        ]

    candidate["schema_version"] = CURRENT_SCHEMA_VERSION
    actions.append(
        {
            "field": "schema_version",
            "from": state.get("schema_version"),
            "to": CURRENT_SCHEMA_VERSION,
            "reason": "mark state with the current schema contract",
        }
    )

    entry = candidate.get("entry")
    workflow = candidate.get("workflow")
    if entry in LEGACY_WORKFLOW_VALUES and workflow in LEGACY_WORKFLOW_VALUES[entry]:
        canonical = workflow_readme_path(entry)
        candidate["workflow"] = canonical
        actions.append(
            {
                "field": "workflow",
                "from": workflow,
                "to": canonical,
                "reason": "normalize a recognized legacy workflow path",
            }
        )

    for index, receipt in enumerate(candidate.get("skill_receipts", [])):
        if not isinstance(receipt, dict):
            continue
        logical_path = safe_skill_receipt_path(receipt)
        if logical_path is None:
            continue
        old_path = receipt["path"]
        receipt["path"] = logical_path
        actions.append(
            {
                "field": f"skill_receipts[{index}].path",
                "from": old_path,
                "to": logical_path,
                "reason": "the recorded hash matches the repository skill file",
            }
        )

    return candidate, actions, blockers


def audit_state(path: Path, schema_path: Path = DEFAULT_SCHEMA) -> tuple[dict[str, Any], dict[str, Any]]:
    state = load_json(path)
    detected_version = detect_schema_version(state)
    candidate, actions, blockers = build_candidate(state)
    if not blockers:
        blockers.extend(check_schema(candidate, schema_path))
    validation_errors = [] if blockers else check_semantic_rules(candidate)
    if detected_version == CURRENT_SCHEMA_VERSION:
        status = "current" if not blockers else "blocked"
    else:
        status = "ready" if not blockers else "blocked"
    report = {
        "path": path.as_posix(),
        "detected_version": detected_version,
        "target_version": CURRENT_SCHEMA_VERSION,
        "status": status,
        "actions": actions,
        "blockers": blockers,
        "post_migration_validation_errors": validation_errors,
    }
    return report, candidate


def backup_path_for(path: Path, source_version: int | None) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    version = "invalid" if source_version is None else f"v{source_version}"
    return path.with_name(f"{path.name}.{version}.{timestamp}.bak")


def write_candidate(path: Path, candidate: dict[str, Any], source_version: int | None) -> Path:
    backup = backup_path_for(path, source_version)
    shutil.copy2(path, backup)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            json.dump(candidate, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
            temporary_name = fh.name
        os.replace(temporary_name, path)
    except Exception:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
        backup.replace(path)
        raise
    return backup


def state_paths(args: argparse.Namespace) -> list[Path]:
    if args.state:
        return [resolve_repo_path(args.state)]
    root = resolve_repo_path(args.runs_root)
    return sorted(root.glob("*/state.json"))


def build_report(results: list[dict[str, Any]], *, write: bool) -> dict[str, Any]:
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "mode": "write" if write else "dry-run",
        "summary": {
            "total": len(results),
            "current": sum(item["status"] == "current" for item in results),
            "ready": sum(item["status"] == "ready" for item in results),
            "blocked": sum(item["status"] == "blocked" for item in results),
            "with_validation_warnings": sum(bool(item["post_migration_validation_errors"]) for item in results),
            "written": sum(bool(item.get("written")) for item in results),
        },
        "states": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--state", type=Path, help="Audit or migrate one state file.")
    source.add_argument("--runs-root", type=Path, help="Dry-run every direct runs/<run-id>/state.json file.")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--write", action="store_true", help="Migrate one schema-ready state and create a backup.")
    parser.add_argument("--output", type=Path, help="Also write the JSON report to this path.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if args.write and args.runs_root:
        parser.error("--write requires one explicit --state; bulk migration is intentionally unsupported")
    return args


def main() -> int:
    args = parse_args()
    schema_path = args.schema if args.schema.is_absolute() else resolve_repo_path(args.schema)
    results: list[dict[str, Any]] = []
    for path in state_paths(args):
        result, candidate = audit_state(path, schema_path)
        if args.write and result["status"] == "ready":
            backup = write_candidate(path, candidate, result["detected_version"])
            result["written"] = True
            result["backup"] = backup.as_posix()
        elif args.write:
            result["written"] = False
        results.append(result)

    report = build_report(results, write=args.write)
    if args.output:
        output = resolve_repo_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(
            f"Run-state migration {report['mode']}: total={summary['total']} "
            f"current={summary['current']} ready={summary['ready']} "
            f"blocked={summary['blocked']} warnings={summary['with_validation_warnings']} "
            f"written={summary['written']}"
        )
        for result in results:
            print(
                f"- {result['status']}: {result['path']} "
                f"({len(result['actions'])} actions, {len(result['blockers'])} blockers, "
                f"{len(result['post_migration_validation_errors'])} warnings)"
            )
    return 1 if any(result["status"] == "blocked" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
