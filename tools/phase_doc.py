#!/usr/bin/env python3
"""Resolve lazy-load workflow phase document paths."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import resolve_repo_path  # noqa: E402
from phases import (  # noqa: E402
    CANONICAL_PHASES,
    WORKFLOW_ENTRIES,
    list_phase_doc_paths,
    normalize_phase,
    phase_doc_path,
    workflow_readme_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve workflow README or phase doc paths.")
    parser.add_argument("--entry", choices=WORKFLOW_ENTRIES, help="Workflow entrypoint")
    parser.add_argument("--phase", help="Canonical or alias phase name")
    parser.add_argument(
        "--workflow-readme",
        action="store_true",
        help="Print workflows/<entry>/README.md instead of a phase file",
    )
    parser.add_argument(
        "--list-phases",
        action="store_true",
        help="List all phase doc paths for --entry (JSON array of {phase, path})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON {\"path\": \"...\", \"exists\": true|false}",
    )
    args = parser.parse_args()

    if not args.entry:
        parser.error("--entry is required")

    if args.workflow_readme:
        logical = workflow_readme_path(args.entry)
        return emit(logical, args.json)

    if args.list_phases:
        payload = [
            {"phase": phase, "path": path, "exists": resolve_repo_path(path).is_file()}
            for phase, path in list_phase_doc_paths(args.entry)
        ]
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            for item in payload:
                flag = "ok" if item["exists"] else "MISSING"
                print(f"{item['path']}\t{item['phase']}\t{flag}")
        return 0

    if not args.phase:
        parser.error("--phase is required unless --workflow-readme or --list-phases is set")

    normalized = normalize_phase(args.phase, args.entry)
    if normalized not in CANONICAL_PHASES[args.entry]:
        allowed = ", ".join(CANONICAL_PHASES[args.entry])
        print(f"error: unknown phase {args.phase!r} for entry {args.entry!r}; must be one of: {allowed}", file=sys.stderr)
        return 1

    logical = phase_doc_path(args.entry, normalized)
    return emit(logical, args.json)


def emit(logical_path: str, as_json: bool) -> int:
    exists = resolve_repo_path(logical_path).is_file()
    if as_json:
        print(json.dumps({"path": logical_path, "exists": exists}, indent=2))
    else:
        print(logical_path)
    return 0 if exists else 2


if __name__ == "__main__":
    raise SystemExit(main())
