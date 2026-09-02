#!/usr/bin/env python3
"""Validate agent-next Markdown test case files against parser and writing rules."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from artifact_frontmatter import (  # noqa: E402
    UNRESOLVED_PLACEHOLDER_RE,
    validate_test_cases_template_body,
)
from parse_markdown_cases import parse_markdown_case_file  # noqa: E402
from paths import resolve_repo_path  # noqa: E402

CASE_RULES_PATH = "skills/test-case-design/references/case-writing-rules.md"
COVERAGE_REVIEW_RULES_PATH = "skills/test-case-design/references/coverage-review-rules.md"
TEST_CASE_DESIGN_RULES_PATH = "skills/test-case-design/references/test-case-design-methodology.md"
TEMPLATE_PATH = "templates/artifacts/test-cases.md.tmpl"

# API / code tokens that should not appear in business-facing titles.
FORBIDDEN_TITLE_TOKENS = re.compile(
    r"\b(?:ignore3xRule|ignore_3x|ignore3x|p97|p03|fetch_cycle_times|LEFT\s*JOIN|INNER\s*JOIN)\b",
    re.IGNORECASE,
)
CAMEL_CASE_RE = re.compile(r"[a-z][A-Z]")
NON_TC_HEADING_RE = re.compile(r"^#{1,3}\s+(VC-|VER-|VERIFY-)", re.IGNORECASE | re.MULTILINE)


def validate_test_case_file(
    path: Path,
    *,
    source_root: Path | None = None,
    expected_artifact_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"test case file not found: {path}"]

    text = path.read_text(encoding="utf-8")
    errors.extend(validate_test_cases_template_body(text))
    if "用业务语言描述可观察结果" in text or UNRESOLVED_PLACEHOLDER_RE.search(text):
        errors.append("test case artifact contains unresolved template placeholders")
    if re.search(r"^(?:\d+\.|-)\s*$", text, re.MULTILINE):
        errors.append("test case artifact contains empty template list items")
    errors.extend(_check_non_tc_headings(text))

    root = source_root or path.parent
    cases = parse_markdown_case_file(path, source_root=root)
    if not cases:
        errors.append("no TC-00N： headings found under ## 用例列表; see case-writing-rules.md")
        return errors

    for case in cases:
        case_id = case.get("id", "<unknown>")
        prefix = f"{case_id}"
        for message in case.get("errors", []):
            errors.append(f"{prefix}: {message}")
        title = str(case.get("title", "")).strip()
        if not title:
            errors.append(f"{prefix}: empty title")
            continue
        errors.extend(f"{prefix}: {message}" for message in _check_title_quality(title))

    return errors


def _check_non_tc_headings(text: str) -> list[str]:
    errors: list[str] = []
    for match in NON_TC_HEADING_RE.finditer(text):
        errors.append(
            f"invalid case heading {match.group(0).strip()!r}; use ### TC-001：业务描述"
        )
    return errors


def _check_title_quality(title: str) -> list[str]:
    errors: list[str] = []
    if FORBIDDEN_TITLE_TOKENS.search(title):
        errors.append(f"title uses implementation/API token; rewrite in business language: {title!r}")
    if CAMEL_CASE_RE.search(title):
        errors.append(f"title contains camelCase; rewrite in business language: {title!r}")
    if "=" in title:
        errors.append(f"title looks like a parameter expression; use business language: {title!r}")
    if "→" in title or "->" in title:
        errors.append(f"title uses arrow comparison; describe the business outcome instead: {title!r}")
    if title.startswith("【") and title.endswith("】") and len(title) < 8:
        errors.append(f"title too generic: {title!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-file", type=Path, required=True)
    parser.add_argument("--artifact-id", default=None, help="Optional state artifact id to cross-check.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Optional root for relative source paths in parser output.",
    )
    args = parser.parse_args()
    case_file = resolve_repo_path(args.case_file)
    errors = validate_test_case_file(
        case_file,
        source_root=args.source_root,
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
