#!/usr/bin/env python3
"""Reject duplicate and dangling internal traceability references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import AGENT_NEXT_ROOT, resolve_managed_repo_path, resolve_repo_path  # noqa: E402


INTERNAL_ID_RE = re.compile(
    r"(?<![A-Z0-9_-])(?:REQ|RISK|TP|TC|AUTO|BR|Q|SRC)-\d+(?![A-Z0-9_-])"
)
UNSUPPORTED_RA_RE = re.compile(r"(?<![A-Z0-9_-])RA-\d+(?![A-Z0-9_-])")
HEADING_DEFINITION_PATTERNS = {
    "requirement_spec": re.compile(r"^###\s+(REQ-\d+)\b", re.MULTILINE),
    "risk_analysis": re.compile(r"^###\s+(RISK-\d+)\b", re.MULTILINE),
    "test_cases": re.compile(r"^###\s+(TC-\d+)[:：]", re.MULTILINE),
}
TABLE_DEFINITION_PATTERNS = {
    "requirement_spec": re.compile(
        r"^\|\s*((?:BR|Q|SRC)-\d+)\s*\|", re.MULTILINE
    ),
    "automation_implementation": re.compile(r"^\|\s*(AUTO-\d+)\s*\|", re.MULTILINE),
}
REFERENCE_SECTION_HEADINGS = {
    "requirement_spec": ("可追溯关系",),
    "risk_analysis": ("风险矩阵", "覆盖范围审查", "可追溯关系"),
    "test_points": (
        "测试空间",
        "需求覆盖",
        "风险覆盖",
        "测试点列表",
        "复杂度辅助分析",
        "非功能覆盖评估",
        "覆盖缺口",
        "可追溯关系",
    ),
    "automation_implementation": ("来源覆盖", "可追溯关系"),
    "automation_classification": ("用例分类", "现有覆盖", "可追溯关系"),
    "execution_record": (
        "执行范围",
        "自动化执行计划",
        "自动化未执行项",
        "执行结果",
        "覆盖缺口与未执行范围",
        "可追溯关系",
    ),
}
REFERENCE_FIELD_PATTERNS = {
    "requirement_spec": (
        re.compile(r"^\*\*依据\*\*[：:].*$", re.MULTILINE),
        re.compile(r"^\*\*来源定位\*\*[：:].*$", re.MULTILINE),
    ),
    "risk_analysis": (re.compile(r"^\*\*来源\*\*[：:].*$", re.MULTILINE),),
    "test_cases": (
        re.compile(r"^可追溯关系\s*[：:].*$", re.MULTILINE),
        re.compile(r"^断言依据\s*[：:].*$", re.MULTILINE),
    ),
}


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _section_ranges(text: str, headings: Iterable[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for heading in headings:
        match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
        if not match:
            continue
        next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(text)
        ranges.append((match.end(), end))
    return ranges


def _ids_in_range(text: str, start: int, end: int) -> list[tuple[str, int]]:
    return [
        (match.group(0), _line_number(text, start + match.start()))
        for match in INTERNAL_ID_RE.finditer(text[start:end])
    ]


def _unsupported_ra_references(
    text: str, artifact_type: str
) -> list[tuple[str, int]]:
    references: list[tuple[str, int]] = []
    ranges = _section_ranges(text, REFERENCE_SECTION_HEADINGS.get(artifact_type, ()))
    for pattern in REFERENCE_FIELD_PATTERNS.get(artifact_type, ()):
        ranges.extend((match.start(), match.end()) for match in pattern.finditer(text))
    for start, end in ranges:
        references.extend(
            (match.group(0), _line_number(text, start + match.start()))
            for match in UNSUPPORTED_RA_RE.finditer(text[start:end])
        )
    return list(dict.fromkeys(references))


def extract_definitions(text: str, artifact_type: str) -> list[tuple[str, int]]:
    definitions: list[tuple[str, int]] = []
    heading_pattern = HEADING_DEFINITION_PATTERNS.get(artifact_type)
    if heading_pattern:
        definitions.extend(
            (match.group(1), _line_number(text, match.start()))
            for match in heading_pattern.finditer(text)
        )

    table_pattern = TABLE_DEFINITION_PATTERNS.get(artifact_type)
    if table_pattern:
        definitions.extend(
            (match.group(1), _line_number(text, match.start()))
            for match in table_pattern.finditer(text)
        )

    if artifact_type == "test_points":
        for start, end in _section_ranges(text, ("测试点列表",)):
            definitions.extend(
                (match.group(1), _line_number(text, start + match.start()))
                for match in re.finditer(r"^\|\s*(TP-\d+)\s*\|", text[start:end], re.MULTILINE)
            )
        definitions.extend(
            (match.group(1), _line_number(text, match.start()))
            for match in re.finditer(r"^###\s+(TP-\d+)\b", text, re.MULTILINE)
        )
    return definitions


def extract_references(text: str, artifact_type: str) -> list[tuple[str, int]]:
    references: list[tuple[str, int]] = []
    for start, end in _section_ranges(
        text, REFERENCE_SECTION_HEADINGS.get(artifact_type, ())
    ):
        references.extend(_ids_in_range(text, start, end))

    for pattern in REFERENCE_FIELD_PATTERNS.get(artifact_type, ()):
        for field_match in pattern.finditer(text):
            references.extend(_ids_in_range(text, field_match.start(), field_match.end()))

    return list(dict.fromkeys(references))


def _duplicate_definition_errors(
    definitions: Iterable[tuple[str, str, int]],
) -> list[str]:
    errors: list[str] = []
    seen: dict[str, tuple[str, int]] = {}
    for identifier, source, line in definitions:
        previous = seen.get(identifier)
        if previous:
            errors.append(
                f"duplicate_definition {identifier}: {previous[0]}:{previous[1]} and {source}:{line}"
            )
        else:
            seen[identifier] = (source, line)
    return errors


def lint_test_points_text(text: str, *, source: str = "<memory>") -> list[str]:
    definitions = extract_definitions(text, "test_points")
    errors = _duplicate_definition_errors(
        (identifier, source, line) for identifier, line in definitions
    )
    defined_test_points = {identifier for identifier, _line in definitions}
    if not defined_test_points:
        errors.append(f"{source}: test_points must define at least one TP-###")
        return errors

    for target, line in extract_references(text, "test_points"):
        if target.startswith("TP-") and target not in defined_test_points:
            errors.append(
                f"dangling_reference {source}:{line}: {target} NOT FOUND in test point definitions"
            )
    return errors


def lint_run_state_traceability(
    state: dict[str, Any], *, repo_root: Path | None = None
) -> list[str]:
    root = (repo_root or AGENT_NEXT_ROOT).resolve()
    artifacts: list[tuple[str, str, str]] = []
    for artifact in state.get("artifacts", []):
        artifact_type = str(artifact.get("type", "")).strip()
        raw_path = str(artifact.get("path", "")).strip()
        if not artifact_type or not raw_path:
            continue
        try:
            path = resolve_managed_repo_path(raw_path, "outputs", root=root)
        except ValueError:
            continue
        if path.is_file():
            artifacts.append((artifact_type, raw_path, path.read_text(encoding="utf-8")))

    definitions: list[tuple[str, str, int]] = []
    references: list[tuple[str, str, int]] = []
    errors: list[str] = []
    for artifact_type, source, text in artifacts:
        definitions.extend(
            (identifier, source, line)
            for identifier, line in extract_definitions(text, artifact_type)
        )
        references.extend(
            (identifier, source, line)
            for identifier, line in extract_references(text, artifact_type)
        )
        for identifier, line in _unsupported_ra_references(text, artifact_type):
            errors.append(
                f"unsupported_reference {source}:{line}: "
                f"{identifier} has no defined RA contract"
            )

    errors.extend(_duplicate_definition_errors(definitions))
    registry = {identifier for identifier, _source, _line in definitions}

    for target, source, line in references:
        if target not in registry:
            errors.append(f"dangling_reference {source}:{line}: {target} NOT FOUND")

    for index, link in enumerate(state.get("traceability", [])):
        if not isinstance(link, dict):
            continue
        for endpoint in ("from", "to"):
            value = str(link.get(endpoint, "")).strip()
            if INTERNAL_ID_RE.fullmatch(value) and value not in registry:
                errors.append(
                    f"dangling_reference run_state.traceability[{index}].{endpoint}: "
                    f"{value} NOT FOUND"
                )
            elif UNSUPPORTED_RA_RE.fullmatch(value):
                errors.append(
                    f"unsupported_reference run_state.traceability[{index}].{endpoint}: "
                    f"{value} has no defined RA contract"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=AGENT_NEXT_ROOT)
    args = parser.parse_args()
    state_path = resolve_repo_path(args.state, root=args.repo_root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    errors = lint_run_state_traceability(state, repo_root=args.repo_root)
    if errors:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
    else:
        print("PASSED")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
