#!/usr/bin/env python3
"""Validate managed Artifact Markdown body structures."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from .traceability_lint import lint_test_points_text
except ImportError:  # Standalone tool loading adds tools/ directly to sys.path.
    from traceability_lint import lint_test_points_text


TEST_CASES_TEMPLATE_MARKERS = (
    "# 测试用例",
    "## 摘要",
    "## 用例列表",
    "用例类型：",
    "断言依据：",
    "## 覆盖摘要",
    "## 覆盖缺口",
)


def validate_test_cases_template_body(text: str) -> list[str]:
    errors: list[str] = []
    for marker in TEST_CASES_TEMPLATE_MARKERS:
        if marker not in text:
            errors.append(
                f"missing template section {marker!r}; start from "
                "templates/artifacts/test-cases.md.tmpl via copy_template.py"
            )
    if "外部用例ID：" not in text and "禅道ID：" not in text:
        errors.append("missing template field '外部用例ID：'; legacy '禅道ID：' is also accepted")
    if re.search(r"^\*\*优先级\*\*:", text, re.MULTILINE):
        errors.append("uses **优先级**: bold field style; use template fields (优先级：)")
    return errors


OLD_TEST_POINTS_TEMPLATE_MARKERS = (
    "# 测试点",
    "## 摘要",
    "## 测试点列表",
    "## 可追溯关系",
)

NEW_TEST_POINTS_TEMPLATE_MARKERS = (
    "# 测试点",
    "## 摘要",
    "analysis_depth:",
    "## 测试空间",
    "## 测试点列表",
    "## 复杂度辅助分析",
    "## 非功能覆盖评估",
    "## 覆盖缺口",
    "## 可追溯关系",
)

VALID_ANALYSIS_DEPTHS = frozenset({"simple", "standard", "complex"})
PLATFORM_NFR_TYPES = (
    "security",
    "availability_resilience",
    "performance",
    "compatibility",
)
VALID_NFR_ASSESSMENT_RESULTS = frozenset({"covered", "gap", "not_applicable"})
NFR_ASSESSMENT_ROW_RE = re.compile(
    r"^\|\s*(security|availability_resilience|performance|compatibility)\s*"
    r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
    re.MULTILINE,
)
TEST_POINTS_HEADER_RE = re.compile(
    r"^\|\s*ID\s*\|\s*测试点\s*\|\s*优先级\s*\|\s*维度\s*\|\s*条件\s*\|\s*技术\s*\|\s*覆盖意图\s*\|\s*依据\s*\|\s*$",
    re.MULTILINE,
)

ATOMIC_REQUIREMENT_HEADING_RE = re.compile(
    r"^###\s+(REQ-\d+)(?!-)\s+(.+?)\s*$",
    re.MULTILINE,
)
NESTED_REQUIREMENT_HEADING_RE = re.compile(r"^###\s+REQ-\d+-\d+\b", re.MULTILINE)
REQUIREMENT_FIELDS = (
    "需求陈述",
    "依据类型",
    "确认状态",
    "来源定位",
    "优先级",
    "验收口径",
)
VALID_REQUIREMENT_BASIS_TYPES = frozenset(
    {"source_explicit", "user_confirmed", "assumption"}
)
VALID_REQUIREMENT_CONFIRMATION_STATUSES = frozenset(
    {"confirmed", "pending", "conflict"}
)
RISK_HEADING_RE = re.compile(r"^###\s+(RISK-\d+)(?!-)\s+(.+?)\s*$", re.MULTILINE)
NESTED_RISK_HEADING_RE = re.compile(r"^###\s+RISK-\d+-\d+\b", re.MULTILINE)
RISK_FIELDS = (
    "来源",
    "Risk Type",
    "Risk Subtype",
    "Risk Tags",
    "状态",
    "等级",
    "问题本质",
    "代码证据",
    "触发条件",
    "影响",
    "疑点",
    "验证方式",
    "决策备注",
)
VALID_RISK_TYPES = frozenset(
    {
        "functional",
        "security",
        "integration",
        "data",
        "state",
        "configuration",
        "compatibility",
        "performance",
        "availability_resilience",
        "usability",
        "observability",
    }
)
VALID_RISK_STATUSES = frozenset(
    {
        "identified",
        "pending_validation",
        "validated",
        "accepted",
        "mitigated",
        "closed",
        "dismissed",
    }
)
VALID_RISK_LEVELS = frozenset({"P0", "P1", "P2", "P3"})


def _uses_new_test_points_template(text: str) -> bool:
    return any(
        marker in text
        for marker in ("analysis_depth:", "## 测试空间", "## 复杂度辅助分析")
    )


def validate_test_points_template_body(text: str) -> list[str]:
    errors: list[str] = []
    if not _uses_new_test_points_template(text):
        return validate_template_markers(
            text,
            OLD_TEST_POINTS_TEMPLATE_MARKERS,
            template_name="test-points",
        )

    errors.extend(
        validate_template_markers(
            text,
            NEW_TEST_POINTS_TEMPLATE_MARKERS,
            template_name="test-points",
        )
    )

    match = re.search(r"^analysis_depth:[ \t]*([^\n]*)$", text, re.MULTILINE)
    if not match:
        errors.append("analysis_depth is required for new test_points artifacts")
    else:
        depth = match.group(1).strip().lower()
        if not depth:
            errors.append("analysis_depth must not be empty")
        elif depth not in VALID_ANALYSIS_DEPTHS:
            errors.append("analysis_depth must be one of: simple, standard, complex")

    if not TEST_POINTS_HEADER_RE.search(text):
        errors.append(
            "test_points table header must be: "
            "| ID | 测试点 | 优先级 | 维度 | 条件 | 技术 | 覆盖意图 | 依据 |"
        )

    errors.extend(validate_platform_nfr_assessment(text))

    errors.extend(lint_test_points_text(text))

    return errors


def validate_platform_nfr_assessment(text: str) -> list[str]:
    errors: list[str] = []
    heading = re.search(r"^## 非功能覆盖评估\s*$", text, re.MULTILINE)
    if not heading:
        return ["test_points must contain a 非功能覆盖评估 section"]
    next_heading = re.search(r"^## \S.*$", text[heading.end() :], re.MULTILINE)
    end = heading.end() + next_heading.start() if next_heading else len(text)
    section = text[heading.end() : end]
    rows = NFR_ASSESSMENT_ROW_RE.findall(section)
    seen: set[str] = set()
    for risk_type, result, rationale in rows:
        if risk_type in seen:
            errors.append(f"duplicate non-functional assessment row: {risk_type}")
        seen.add(risk_type)
        result = result.strip()
        rationale = rationale.strip()
        if result not in VALID_NFR_ASSESSMENT_RESULTS:
            errors.append(
                f"{risk_type}: non-functional assessment result must be one of: "
                + ", ".join(sorted(VALID_NFR_ASSESSMENT_RESULTS))
            )
        if not rationale:
            errors.append(f"{risk_type}: non-functional assessment requires refs or rationale")
        if result == "covered":
            if not re.search(r"\bRISK-\d+\b", rationale) or not re.search(
                r"\bTP-\d+\b", rationale
            ):
                errors.append(
                    f"{risk_type}: covered assessment requires both RISK-### and TP-###"
                )

    for risk_type in PLATFORM_NFR_TYPES:
        if risk_type not in seen:
            errors.append(f"missing non-functional assessment row: {risk_type}")
    return errors


def validate_requirement_spec_body(text: str) -> list[str]:
    errors: list[str] = []
    matches = list(ATOMIC_REQUIREMENT_HEADING_RE.finditer(text))

    if NESTED_REQUIREMENT_HEADING_RE.search(text):
        errors.append(
            "nested requirement IDs are not supported; use consecutive Atomic "
            "Requirement IDs such as REQ-001 and REQ-002"
        )
    if not matches:
        errors.append("requirement_spec must contain at least one ### REQ-### heading")
        return errors

    seen: set[str] = set()
    for index, match in enumerate(matches):
        requirement_id = match.group(1)
        if requirement_id in seen:
            errors.append(f"duplicate Atomic Requirement ID: {requirement_id}")
        seen.add(requirement_id)

        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        values: dict[str, str] = {}
        for field in REQUIREMENT_FIELDS:
            field_match = re.search(
                rf"^\*\*{re.escape(field)}\*\*[：:][ \t]*(.*?)[ \t]*$",
                section,
                re.MULTILINE,
            )
            if not field_match or not field_match.group(1).strip():
                errors.append(f"{requirement_id}: missing or empty field {field!r}")
                continue
            values[field] = field_match.group(1).strip()

        basis_type = values.get("依据类型")
        if basis_type and basis_type not in VALID_REQUIREMENT_BASIS_TYPES:
            errors.append(
                f"{requirement_id}: 依据类型 must be one of: "
                + ", ".join(sorted(VALID_REQUIREMENT_BASIS_TYPES))
            )

        confirmation_status = values.get("确认状态")
        if (
            confirmation_status
            and confirmation_status not in VALID_REQUIREMENT_CONFIRMATION_STATUSES
        ):
            errors.append(
                f"{requirement_id}: 确认状态 must be one of: "
                + ", ".join(sorted(VALID_REQUIREMENT_CONFIRMATION_STATUSES))
            )

        if basis_type == "assumption" and confirmation_status == "confirmed":
            errors.append(
                f"{requirement_id}: assumption cannot be confirmed; use pending or "
                "replace it with the explicit confirmation source"
            )

    return errors


def validate_risk_analysis_body(text: str) -> list[str]:
    errors: list[str] = []
    matches = list(RISK_HEADING_RE.finditer(text))

    if NESTED_RISK_HEADING_RE.search(text):
        errors.append(
            "nested risk IDs are not supported; use consecutive IDs such as "
            "RISK-001 and RISK-002"
        )
    if not matches:
        errors.append("risk_analysis must contain at least one ### RISK-### heading")
        return errors

    seen: set[str] = set()
    for index, match in enumerate(matches):
        risk_id = match.group(1)
        if risk_id in seen:
            errors.append(f"duplicate Risk ID: {risk_id}")
        seen.add(risk_id)

        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        values: dict[str, str] = {}
        for field in RISK_FIELDS:
            field_match = re.search(
                rf"^\*\*{re.escape(field)}\*\*[：:][ \t]*(.*?)[ \t]*$",
                section,
                re.MULTILINE,
            )
            if not field_match or not field_match.group(1).strip():
                errors.append(f"{risk_id}: missing or empty field {field!r}")
                continue
            values[field] = field_match.group(1).strip()

        risk_type = values.get("Risk Type")
        if risk_type and risk_type not in VALID_RISK_TYPES:
            errors.append(
                f"{risk_id}: Risk Type must be one of: "
                + ", ".join(sorted(VALID_RISK_TYPES))
            )

        status = values.get("状态")
        if status and status not in VALID_RISK_STATUSES:
            errors.append(
                f"{risk_id}: 状态 must be one of: "
                + ", ".join(sorted(VALID_RISK_STATUSES))
            )

        level = values.get("等级")
        if level and level not in VALID_RISK_LEVELS:
            errors.append(
                f"{risk_id}: 等级 must be one of: "
                + ", ".join(sorted(VALID_RISK_LEVELS))
            )

        decision_note = values.get("决策备注", "").lower()
        if status in {"accepted", "dismissed"} and decision_note in {
            "",
            "none",
            "not_available",
            "not_applicable",
        }:
            errors.append(f"{risk_id}: {status} risk requires a non-empty 决策备注")

    return errors


# Managed artifact types from tools/copy_template.py → required body sections.
ARTIFACT_SPECS: dict[str, dict[str, Any]] = {
    "requirement_spec": {
        "template": "requirement-spec",
        "markers": (
            "# 需求说明书",
            "## 基本信息",
            "## 摘要",
            "## 来源与证据",
            "## 领域术语",
            "## 变更说明",
            "## 用户故事 / 场景卡片",
            "## 需求明细",
            "### Source Fidelity 与原子化规则",
            "## 业务规则与边界条件",
            "## 可追溯关系",
        ),
    },
    "risk_analysis": {
        "template": "risk-analysis",
        "markers": (
            "# 风险分析",
            "## 摘要",
            "## 风险矩阵",
            "## 风险详情",
            "## 可追溯关系",
        ),
    },
    "change_scope": {
        "template": "change-scope",
        "markers": ("# 变更范围", "## 摘要", "## 变更文件", "## 可追溯关系"),
    },
    "coverage_match": {
        "template": "coverage-match",
        "markers": ("# 覆盖匹配", "## 摘要", "## 原 Bug 覆盖", "## 可追溯关系"),
    },
    "regression_plan": {
        "template": "regression-plan",
        "markers": ("# 回归计划", "## 摘要", "## 回归策略", "## 可追溯关系"),
    },
    "test_points": {
        "template": "test-points",
        "markers": NEW_TEST_POINTS_TEMPLATE_MARKERS,
    },
    "regression_report": {
        "template": "regression-report",
        "markers": ("# 回归测试报告", "## 摘要", "## 执行结果", "## 可追溯关系"),
    },
    "acceptance_plan": {
        "template": "acceptance-plan",
        "markers": (
            "# Release Acceptance Plan",
            "## 1. 发布基线",
            "## 2. Release Bundle",
            "## 4. 范围对账",
            "## 6. 验收侧重点",
            "## 7. 性能与稳定性",
            "## 8. 验收覆盖与测试资产",
            "## 10.1 未执行范围与覆盖缺口",
            "## 12. 验收阈值 / Exit Criteria",
            "## 14. 测试管理平台验收单",
            "## 15. Release Decision",
            "## 16. 可追溯关系",
        ),
    },
    "acceptance_report": {
        "template": "acceptance-report",
        "markers": (
            "# 验收报告",
            "## 摘要",
            "## Scope Gap",
            "## 未执行范围与覆盖缺口",
            "## 性能与稳定性摘要",
            "## 发布决策",
            "## 测试管理平台验收单",
            "## 可追溯关系",
        ),
    },
    "release_scope": {
        "template": "release-scope",
        "markers": (
            "# Release Scope",
            "## 1. 声明范围",
            "## 2. 代码范围",
            "## 3. 配置与数据范围",
            "## 4. Scope Gap",
            "## 5. 可追溯关系",
        ),
    },
    "execution_record": {
        "template": "execution-record",
        "markers": (
            "# 执行记录",
            "## 摘要",
            "## 自动化执行计划",
            "## 自动化未执行项",
            "## 覆盖缺口与未执行范围",
            "## 执行结果",
            "## 可追溯关系",
        ),
    },
    "bug_report": {
        "template": "bug-report",
        "markers": ("# Bug 报告草稿", "## 摘要", "## 复现步骤", "## 可追溯关系"),
    },
    "run_summary": {
        "template": "run-summary",
        "markers": ("# Run Summary", "## 基本信息", "## 产物", "## 可追溯关系"),
    },
    "automation_classification": {
        "template": "automation-classification",
        "markers": ("# 自动化分类记录", "## 摘要", "## 用例分类", "## 可追溯关系"),
    },
}

TEMPLATED_ARTIFACT_TYPES = frozenset(ARTIFACT_SPECS) | frozenset({"test_cases"})

UNRESOLVED_PLACEHOLDER_RE = re.compile(
    r"<[^>\n]+>|\bTBD\b|\b(?:REQ|TP|TC)-XXX\b",
    re.IGNORECASE,
)


def validate_template_markers(text: str, markers: tuple[str, ...], *, template_name: str) -> list[str]:
    errors: list[str] = []
    for marker in markers:
        if marker not in text:
            errors.append(
                f"missing template section {marker!r}; start from "
                f"templates/artifacts/{template_name}.md.tmpl via copy_template.py"
            )
    return errors


def validate_managed_artifact_body(text: str, artifact_type: str) -> list[str]:
    if artifact_type == "requirement_spec":
        spec = ARTIFACT_SPECS[artifact_type]
        return [
            *validate_template_markers(
                text,
                spec["markers"],
                template_name=str(spec["template"]),
            ),
            *validate_requirement_spec_body(text),
            *validate_artifact_completion(text, artifact_type),
        ]

    if artifact_type == "risk_analysis":
        spec = ARTIFACT_SPECS[artifact_type]
        return [
            *validate_template_markers(
                text,
                spec["markers"],
                template_name=str(spec["template"]),
            ),
            *validate_risk_analysis_body(text),
            *validate_artifact_completion(text, artifact_type),
        ]

    if artifact_type == "test_points":
        return [
            *validate_test_points_template_body(text),
            *validate_artifact_completion(text, artifact_type),
        ]

    spec = ARTIFACT_SPECS.get(artifact_type)
    if not spec:
        return []
    errors = validate_template_markers(
        text,
        spec["markers"],
        template_name=str(spec["template"]),
    )
    errors.extend(validate_artifact_completion(text, artifact_type))
    return errors


def validate_artifact_completion(text: str, artifact_type: str) -> list[str]:
    """Reject an untouched template or explicit scaffold placeholders."""
    spec = ARTIFACT_SPECS.get(artifact_type)
    if not spec:
        return []

    errors: list[str] = []
    template_path = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "artifacts"
        / f"{spec['template']}.md.tmpl"
    )
    if template_path.is_file() and text == template_path.read_text(encoding="utf-8"):
        errors.append("artifact still matches the untouched managed template")

    placeholders = sorted(set(UNRESOLVED_PLACEHOLDER_RE.findall(text)))
    if placeholders:
        errors.append("artifact contains unresolved placeholders: " + ", ".join(placeholders))
    return errors
