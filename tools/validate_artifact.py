#!/usr/bin/env python3
"""Validate agent-next Markdown artifacts created from managed templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from artifact_frontmatter import ARTIFACT_SPECS, validate_managed_artifact_body  # noqa: E402
from paths import resolve_repo_path  # noqa: E402

def validate_artifact_file(
    path: Path,
    *,
    expected_artifact_type: str,
    expected_artifact_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if expected_artifact_type not in ARTIFACT_SPECS:
        return [f"unknown managed artifact type: {expected_artifact_type!r}"]

    if not path.exists():
        return [f"artifact file not found: {path}"]

    text = path.read_text(encoding="utf-8")
    errors.extend(validate_managed_artifact_body(text, expected_artifact_type))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-file", type=Path, required=True)
    parser.add_argument("--artifact-type", choices=sorted(ARTIFACT_SPECS), required=True)
    parser.add_argument("--artifact-id", default=None, help="Optional state artifact id to cross-check.")
    args = parser.parse_args()
    artifact_file = resolve_repo_path(args.artifact_file)
    errors = validate_artifact_file(
        artifact_file,
        expected_artifact_type=args.artifact_type,
        expected_artifact_id=args.artifact_id,
    )
    if errors:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
