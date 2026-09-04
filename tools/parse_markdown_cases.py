#!/usr/bin/env python3
"""Parse agent-next Markdown test cases into raw TestSpec JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CASE_HEADING_RE = re.compile(r"^#{2,3}\s+(TC-\d+)[:：]\s*(.+?)\s*$", re.MULTILINE)
NUMBERED_ITEM_RE = re.compile(r"^\s*(\d+)[.、]\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^(优先级|外部用例ID|禅道ID|用例类型|前置条件|测试数据|测试步骤|操作步骤|预期结果|备注|可追溯关系)\s*(?:[:：]\s*(.*))?$")
REF_RE = re.compile(
    r"\b(?:[A-Z][A-Z0-9]*-)?(?:REQ|RISK|TP|TC|BR|Q|AUTO|RUN|BUG|DATA)-\d+\b"
)


def parse_markdown_case_file(path: Path, source_root: Path | None = None) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    source_root = source_root or path.parent
    blocks = _split_case_blocks(text)
    return [_parse_case_block(block, line, path, source_root) for block, line in blocks]


def write_raw_spec_file(case_file: Path, output_dir: Path, source_root: Path | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_root = source_root or case_file.parent
    cases = parse_markdown_case_file(case_file, source_root=source_root)
    payload = {
        "source_file": _relative_source(case_file, source_root),
        "case_count": len(cases),
        "cases": cases,
    }
    out = output_dir / f"{case_file.stem}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def write_raw_specs(cases_dir: Path, output_dir: Path) -> list[Path]:
    written: list[Path] = []
    for case_file in sorted(cases_dir.glob("*.md")):
        written.append(write_raw_spec_file(case_file, output_dir, source_root=cases_dir))
    return written


def _split_case_blocks(text: str) -> list[tuple[str, int]]:
    matches = list(CASE_HEADING_RE.finditer(text))
    blocks: list[tuple[str, int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = re.sub(r"\n---\s*$", "", text[start:end].strip()).strip()
        blocks.append((block, text.count("\n", 0, start) + 1))
    return blocks


def _parse_case_block(block: str, start_line: int, source_path: Path, source_root: Path) -> dict[str, Any]:
    lines = block.splitlines()
    heading = CASE_HEADING_RE.match(lines[0].strip()) if lines else None
    warnings: list[str] = []
    errors: list[str] = []
    case_id = heading.group(1) if heading else "UNKNOWN"
    title = heading.group(2).strip() if heading else ""
    if heading is None:
        errors.append("missing TC heading")

    fields = _collect_fields(lines[1:])
    priority = _single_line_field(fields, "优先级", warnings)
    external_case_id = _single_line_field(fields, "外部用例ID", warnings)
    if not external_case_id:
        external_case_id = _single_line_field(fields, "禅道ID", warnings)
    case_type = _single_line_field(fields, "用例类型", warnings)
    traceability = "\n".join(fields.get("可追溯关系", [])).strip()
    preconditions = _parse_numbered_items(fields.get("前置条件", []), "preconditions", warnings)
    test_data = "\n".join(fields.get("测试数据", [])).strip()
    steps = _parse_indexed_items(fields.get("测试步骤", fields.get("操作步骤", [])), "steps", warnings)
    expects = _parse_indexed_items(fields.get("预期结果", []), "expects", warnings)
    remark = "\n".join(fields.get("备注", []) + fields.get("可追溯关系", [])).strip()

    if steps and expects and len(steps) != len(expects):
        errors.append(f"steps/expects count mismatch: {len(steps)} != {len(expects)}")
    for required, value in (
        ("优先级", priority),
        ("外部用例ID", external_case_id),
        ("用例类型", case_type),
        ("可追溯关系", traceability),
    ):
        if not value:
            errors.append(f"missing field: {required}")

    return {
        "id": case_id,
        "title": title,
        "priority": priority,
        "external_case_id": external_case_id,
        "zentao_id": external_case_id,
        "case_type": case_type,
        "source": {
            "case_file": _relative_source(source_path, source_root),
            "line": start_line,
        },
        "preconditions": preconditions,
        "test_data": test_data,
        "steps": steps,
        "expects": expects,
        "remark": remark,
        "refs": _extract_refs(remark),
        "raw": block,
        "warnings": warnings,
        "errors": errors,
    }


def _collect_fields(lines: list[str]) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        match = FIELD_RE.match(stripped)
        if match:
            current = match.group(1)
            fields.setdefault(current, [])
            tail = (match.group(2) or "").strip()
            if tail:
                fields[current].append(tail)
            continue
        if current is not None:
            fields[current].append(stripped)
    return fields


def _single_line_field(fields: dict[str, list[str]], name: str, warnings: list[str]) -> str:
    values = fields.get(name, [])
    if not values:
        return ""
    if len(values) > 1:
        warnings.append(f"field has multiple lines: {name}")
    return values[0].strip()


def _parse_numbered_items(lines: list[str], field_name: str, warnings: list[str]) -> list[str]:
    return [item["text"] for item in _parse_indexed_items(lines, field_name, warnings)]


def _parse_indexed_items(lines: list[str], field_name: str, warnings: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in lines:
        match = NUMBERED_ITEM_RE.match(line)
        if match:
            items.append({"index": int(match.group(1)), "text": match.group(2).strip()})
        elif line.strip():
            warnings.append(f"unparsed {field_name} line: {line.strip()}")
    return items


def _extract_refs(text: str) -> dict[str, list[str]]:
    refs = REF_RE.findall(text)
    return {
        "requirements": _dedupe([ref for ref in refs if _ref_kind(ref) == "REQ"]),
        "business_rules": _dedupe([ref for ref in refs if _ref_kind(ref) == "BR"]),
        "questions": _dedupe([ref for ref in refs if _ref_kind(ref) == "Q"]),
        "risks": _dedupe([ref for ref in refs if _ref_kind(ref) == "RISK"]),
        "test_points": _dedupe([ref for ref in refs if _ref_kind(ref) in {"TP", "TC"}]),
        "automation": _dedupe([ref for ref in refs if _ref_kind(ref) == "AUTO"]),
        "bugs": _dedupe([ref for ref in refs if _ref_kind(ref) == "BUG"]),
        "data": _dedupe([ref for ref in refs if _ref_kind(ref) == "DATA"]),
    }


def _ref_kind(ref: str) -> str:
    parts = ref.split("-")
    return parts[-2] if len(parts) > 2 else parts[0]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _relative_source(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cases-dir", type=Path)
    group.add_argument("--case-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.case_file:
        written = [write_raw_spec_file(args.case_file, args.output, source_root=args.case_file.parent)]
    else:
        written = write_raw_specs(args.cases_dir, args.output)
    print(f"written={len(written)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
