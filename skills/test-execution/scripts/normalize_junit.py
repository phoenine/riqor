#!/usr/bin/env python3
"""Normalize JUnit XML and traceable YAML cases into an execution record."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable

import yaml


AUTO_RE = re.compile(r"(?<![A-Z0-9_-])(AUTO-\d+)(?!\d)")
STATUS_ORDER = {
    "passed": 0,
    "skipped": 1,
    "blocked": 2,
    "failed": 3,
    "infrastructure_error": 4,
}


class ExecutionContractError(ValueError):
    pass


def _files(paths: Iterable[Path], suffixes: tuple[str, ...]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(item for item in path.rglob("*") if item.suffix in suffixes)
        else:
            found.append(path)
    return sorted(set(found))


def load_cases(paths: Iterable[Path]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for path in _files(paths, (".yaml", ".yml")):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        for case in payload.get("cases", []) if isinstance(payload, dict) else []:
            case_id = str(case.get("id", "")) if isinstance(case, dict) else ""
            if not AUTO_RE.fullmatch(case_id):
                errors.append(f"{path}: invalid or missing AUTO case ID")
            elif case_id in cases:
                errors.append(f"{path}: duplicate case definition {case_id}")
            else:
                cases[case_id] = case
    if not cases:
        errors.append("no traceable AUTO cases found")
    if errors:
        raise ExecutionContractError("\n".join(errors))
    return cases


def _result_status(testcase: ET.Element) -> tuple[str, str]:
    error = testcase.find("error")
    if error is not None:
        return "infrastructure_error", error.get("message", "runner error")
    failure = testcase.find("failure")
    if failure is not None:
        return "failed", failure.get("message", "assertion failed")
    skipped = testcase.find("skipped")
    if skipped is not None:
        reason = skipped.get("message", "skipped")
        status = "blocked" if "block" in reason.lower() else "skipped"
        return status, reason
    return "passed", ""


def load_junit(paths: Iterable[Path]) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    requested = list(paths)
    files = _files(requested, (".xml",))
    if requested and not files:
        raise ExecutionContractError("no JUnit XML files found")
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        for testcase in root.iter("testcase"):
            identity = " ".join(
                filter(None, (testcase.get("classname"), testcase.get("name")))
            )
            match = AUTO_RE.search(identity)
            if not match:
                errors.append(f"{path}: testcase has no AUTO-### identity: {identity}")
                continue
            status, message = _result_status(testcase)
            try:
                duration = float(testcase.get("time", "0") or 0)
            except ValueError:
                errors.append(f"{path}: invalid testcase time: {identity}")
                continue
            results.setdefault(match.group(1), []).append(
                {
                    "status": status,
                    "message": message,
                    "time": duration,
                    "evidence": str(path),
                }
            )
    if errors:
        raise ExecutionContractError("\n".join(errors))
    return results


def validate_exit_code(results: list[dict[str, Any]], exit_code: str) -> None:
    try:
        code = int(exit_code)
    except ValueError as exc:
        raise ExecutionContractError("exit code must be an integer") from exc
    if code != 0 and not any(
        result["status"] in {"failed", "infrastructure_error"} for result in results
    ):
        raise ExecutionContractError(
            "non-zero exit code is not explained by failed or infrastructure_error results"
        )


def normalize(
    cases: dict[str, dict[str, Any]],
    junit_results: dict[str, list[dict[str, Any]]],
    infrastructure_error: str | None = None,
) -> list[dict[str, Any]]:
    unknown = sorted(set(junit_results) - set(cases))
    if unknown:
        raise ExecutionContractError("unknown JUnit case IDs: " + ", ".join(unknown))
    normalized: list[dict[str, Any]] = []
    for case_id, case in sorted(cases.items()):
        executions = junit_results.get(case_id, [])
        if executions:
            status = max(executions, key=lambda item: STATUS_ORDER[item["status"]])["status"]
            evidence = ", ".join(sorted({item["evidence"] for item in executions}))
            detail = "; ".join(item["message"] for item in executions if item["message"])
        elif infrastructure_error:
            status, evidence, detail = (
                "infrastructure_error",
                "none",
                infrastructure_error,
            )
        else:
            status, evidence, detail = "not_run", "none", "no JUnit result"
        normalized.append(
            {
                "id": case_id,
                "title": str(case.get("title", "")),
                "source": case.get("source", {}),
                "status": status,
                "evidence": evidence,
                "detail": detail or "none",
                "executions": len(executions),
            }
        )
    return normalized


def _cell(value: Any) -> str:
    if isinstance(value, list):
        value = " / ".join(str(item) for item in value) or "none"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_record(results: list[dict[str, Any]], metadata: dict[str, str]) -> str:
    counts = Counter(result["status"] for result in results)
    rows: list[str] = []
    trace: list[str] = []
    for result in results:
        source = result["source"] if isinstance(result["source"], dict) else {}
        cases = source.get("test_cases", [])
        points = source.get("test_points", [])
        upstream = []
        for key in ("requirements", "business_rules", "risks", "questions", "data_rows"):
            upstream.extend(source.get(key, []))
        rows.append(
            "| {id} | {title} | {tc} | {tp} | {upstream} | {status} | {count} | {evidence} | {detail} |".format(
                id=_cell(result["id"]),
                title=_cell(result["title"]),
                tc=_cell(cases),
                tp=_cell(points),
                upstream=_cell(upstream),
                status=result["status"],
                count=result["executions"],
                evidence=_cell(result["evidence"]),
                detail=_cell(result["detail"]),
            )
        )
        trace.extend(
            f"| {_cell(case_id)} | {result['id']} | automated_by |" for case_id in cases
        )
    summary = " / ".join(f"{key}={counts.get(key, 0)}" for key in (
        "passed", "failed", "blocked", "skipped", "not_run", "infrastructure_error"
    ))
    return f"""# 执行记录

## 摘要

| 项 | 内容 |
|---|---|
| 入口 | {_cell(metadata['entry'])} |
| project_id | {_cell(metadata['project_id'])} |
| 环境目标 | {_cell(metadata['environment'])} |
| Repository / Revision | {_cell(metadata['repository'])} / {_cell(metadata['revision'])} |
| Command | {_cell(metadata['command'])} |
| Exit Code | {_cell(metadata['exit_code'])} |
| 执行窗口 | {_cell(metadata['started_at'])} → {_cell(metadata['ended_at'])} |
| 结果统计 | {summary} |

## 执行范围

| AUTO ID | 标题 | TC | TP | Upstream | 结果 | Executions | 证据 | 备注 |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## 自动化执行计划

| Repository | Revision | Command | Target Environment | Status |
|---|---|---|---|---|
| {_cell(metadata['repository'])} | {_cell(metadata['revision'])} | {_cell(metadata['command'])} | {_cell(metadata['environment'])} | completed |

## 自动化未执行项

见执行范围中 `not_run`、`blocked` 和 `skipped` 行。

## 覆盖缺口与未执行范围

不得将 `blocked`、`skipped`、`not_run` 或 `infrastructure_error` 计为通过。

## 执行结果

结果以“执行范围”的规范化状态和 JUnit 证据为准。

## 阻塞与跳过

见执行范围中的状态与备注。

## 发现问题

失败仅作为候选问题；由 Reporting 和缺陷流程结合断言来源判断。

## 测试管理平台验收单

未同步。

## 结论

由 Reporting 基于规范化状态计算，不在执行阶段推断发布结论。

## 可追溯关系

| From | To | Relation |
|---|---|---|
{chr(10).join(trace) if trace else '| none | none | none |'}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, action="append", default=[])
    parser.add_argument("--cases", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--ended-at", required=True)
    parser.add_argument("--infrastructure-error")
    args = parser.parse_args()
    if not args.junit and not args.infrastructure_error:
        parser.error("provide --junit or --infrastructure-error")
    cases = load_cases(args.cases)
    results = normalize(
        cases,
        load_junit(args.junit),
        infrastructure_error=args.infrastructure_error,
    )
    validate_exit_code(results, args.exit_code)
    content = render_record(
        results,
        {
            "entry": args.entry,
            "project_id": args.project_id,
            "environment": args.environment,
            "repository": args.repository,
            "revision": args.revision,
            "command": args.command,
            "exit_code": args.exit_code,
            "started_at": args.started_at,
            "ended_at": args.ended_at,
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
