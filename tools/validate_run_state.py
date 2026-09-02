#!/usr/bin/env python3
"""Validate an agent-next run state file against JSON Schema and semantic rules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import AGENT_NEXT_ROOT  # noqa: E402
from phases import phase_validation_error  # noqa: E402
from stage_gate import check_global_state  # noqa: E402


DEFAULT_SCHEMA = AGENT_NEXT_ROOT / "schemas" / "run-state.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _import_jsonschema():
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import ValidationError
    except ImportError as exc:
        raise RuntimeError(
            "jsonschema is required for validate_run_state.py; install with: pip install -r requirements.txt"
        ) from exc
    return Draft202012Validator, ValidationError


def format_schema_error(error: Any) -> str:
    parts = [str(part) for part in error.absolute_path]
    location = "$" if not parts else "$." + ".".join(parts)
    return f"{location}: {error.message}"


def check_schema(state: dict[str, Any], schema_path: Path) -> list[str]:
    Draft202012Validator, _ValidationError = _import_jsonschema()
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    return [format_schema_error(error) for error in sorted(validator.iter_errors(state), key=str)]


def check_semantic_rules(state: dict[str, Any]) -> list[str]:
    """Apply semantic checks beyond JSON Schema.

    Phase names use `$.phase:` errors for CLI/schema alignment. Other global
    run-state rules reuse `stage_gate.check_global_state()` so validation stays
    aligned with stage gates (router skill, skill receipts, knowledge_plan, etc.).
    """
    errors: list[str] = []
    phase_error = phase_validation_error(state.get("entry"), state.get("phase", ""))
    if phase_error:
        errors.append(f"$.phase: {phase_error}")
    errors.extend(
        error
        for error in check_global_state(state, verify_live_evidence=False)
        if not error.startswith("phase ")
    )
    return errors


def check_state(state: dict[str, Any], schema_path: Path = DEFAULT_SCHEMA) -> list[str]:
    errors = check_schema(state, schema_path)
    errors.extend(check_semantic_rules(state))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema_path = args.schema if args.schema.is_absolute() else resolve_schema_path(args.schema)
    errors = check_state(load_json(args.state), schema_path)
    if args.format == "json":
        print(json.dumps({"status": "failed" if errors else "passed", "errors": errors}, ensure_ascii=False, indent=2))
    elif errors:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
    else:
        print("PASSED")
    return 1 if errors else 0


def resolve_schema_path(path: Path) -> Path:
    if path.parts and path.parts[0] == "agent-next":
        remainder = Path(*path.parts[1:])
        return AGENT_NEXT_ROOT / remainder
    return AGENT_NEXT_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
