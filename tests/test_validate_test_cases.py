import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from helpers import ROOT, load_tool

validate_test_cases = load_tool("validate_test_cases")
parse_markdown_cases = load_tool("parse_markdown_cases")
stage_gate = load_tool("stage_gate")


VALID_CASE = """---
artifact_id: "TC-SET-001"
artifact_type: test_cases
producer_phase: "Regression Plan"
source_artifacts: []
evidence: []
validation:
  status: pending
---

# 测试用例

## 摘要

## 用例列表

### TC-001：开启三倍基线过滤后参与计算的周期数应减少

优先级：P1

外部用例ID：未同步

用例类型：接口测试

可追溯关系：BUG-1649

前置条件：

1. 已部署修复版本。

操作步骤：

1. 关闭三倍基线过滤并记录各机型周期数。
2. 开启三倍基线过滤并记录各机型周期数。

预期结果：

1. 开启过滤后周期数不大于关闭时。
2. 至少一个机型周期数减少。

备注：
"""

VALID_CASE_TAIL = """
## 覆盖摘要

## 覆盖缺口
"""

VALID_CASE = VALID_CASE.rstrip() + VALID_CASE_TAIL

HAND_WRITTEN_CASE = """# Bug 回归

## VC-01: ignore3xRule=true → Cycle 数量应减少

**优先级:** P1
"""


class ValidateTestCasesTests(unittest.TestCase):
    def test_untouched_template_is_incomplete(self):
        errors = validate_test_cases.validate_test_case_file(ROOT / validate_test_cases.TEMPLATE_PATH)
        self.assertTrue(any("template placeholders" in error for error in errors), errors)
        self.assertTrue(any("empty template list items" in error for error in errors), errors)

    def test_valid_case_file_passes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(VALID_CASE, encoding="utf-8")
            self.assertEqual(validate_test_cases.validate_test_case_file(path), [])

    def test_external_case_id_is_primary_with_legacy_zentao_alias(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(VALID_CASE, encoding="utf-8")
            case = parse_markdown_cases.parse_markdown_case_file(path)[0]
            self.assertEqual(case["external_case_id"], "未同步")
            self.assertEqual(case["zentao_id"], "未同步")

            legacy = Path(tmp) / "legacy-cases.md"
            legacy.write_text(
                VALID_CASE.replace("外部用例ID：未同步", "禅道ID：未上传"),
                encoding="utf-8",
            )
            self.assertEqual(validate_test_cases.validate_test_case_file(legacy), [])

    def test_hand_written_file_without_template_fails(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(HAND_WRITTEN_CASE, encoding="utf-8")
            errors = validate_test_cases.validate_test_case_file(path)
            self.assertTrue(any("missing template section" in error for error in errors), errors)

    def test_vc_heading_fails(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(
                VALID_CASE.replace(
                    "### TC-001：开启三倍基线过滤后参与计算的周期数应减少",
                    "",
                )
                + "\n## VC-01: ignore3xRule=true\n",
                encoding="utf-8",
            )
            errors = validate_test_cases.validate_test_case_file(path)
            self.assertTrue(any("invalid case heading" in error or "no TC-00N" in error for error in errors))

    def test_artifact_identity_is_not_read_from_output_body(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(VALID_CASE, encoding="utf-8")
            errors = validate_test_cases.validate_test_case_file(
                path, expected_artifact_id="TC-WRONG-001"
            )
            self.assertEqual(errors, [])

    def test_camel_case_title_fails(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(
                VALID_CASE.replace(
                    "开启三倍基线过滤后参与计算的周期数应减少",
                    "ignore3xRule=true时Records减少",
                ),
                encoding="utf-8",
            )
            errors = validate_test_cases.validate_test_case_file(path)
            self.assertTrue(any("camelCase" in error or "implementation/API token" in error for error in errors))

    def test_steps_and_expects_count_must_match(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(
                VALID_CASE.replace(
                    "2. 至少一个机型周期数减少。",
                    "2. 至少一个机型周期数减少。\n3. 不显示计算异常提示。",
                ),
                encoding="utf-8",
            )
            errors = validate_test_cases.validate_test_case_file(path)
            self.assertTrue(any("steps/expects count mismatch" in error for error in errors), errors)

    def test_test_data_field_is_parsed_separately(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(
                VALID_CASE.replace(
                    "前置条件：\n\n1. 已部署修复版本。\n\n操作步骤：",
                    "前置条件：\n\n1. 已部署修复版本。\n\n测试数据：\n\n| 场景 | 输入值 |\n|---|---:|\n| 最小有效值 | 10 |\n\n操作步骤：",
                ),
                encoding="utf-8",
            )
            cases = parse_markdown_cases.parse_markdown_case_file(path)
            self.assertEqual(cases[0]["test_data"].splitlines()[0], "| 场景 | 输入值 |")
            self.assertNotIn("测试数据", cases[0]["remark"])

    def test_simple_traceability_ids_are_extracted(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(
                VALID_CASE.replace("可追溯关系：BUG-1649", "可追溯关系：TP-001 / BUG-1649"),
                encoding="utf-8",
            )
            refs = parse_markdown_cases.parse_markdown_case_file(path)[0]["refs"]
            self.assertEqual(refs["test_points"], ["TP-001"])
            self.assertEqual(refs["bugs"], ["BUG-1649"])

    def test_business_rule_and_question_refs_are_extracted(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(
                VALID_CASE.replace(
                    "可追溯关系：BUG-1649",
                    "可追溯关系：TP-001 / BR-002 / Q-003",
                ),
                encoding="utf-8",
            )

            refs = parse_markdown_cases.parse_markdown_case_file(path)[0]["refs"]

            self.assertEqual(refs["business_rules"], ["BR-002"])
            self.assertEqual(refs["questions"], ["Q-003"])

    def test_stage_gate_requires_case_design_coverage_and_writing_rules_knowledge(self):
        with TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "demo.md"
            case_path.write_text(VALID_CASE, encoding="utf-8")
            state = {
            "run_id": "demo",
            "project_id": "shop-platform",
            "tracks": ["storefront"],
            "entry": "bug-regression",
            "workflow": "workflows/bug-regression/README.md",
            "phase": "Regression Plan",
            "required_skills": ["agent-next"],
            "loaded_skills": ["agent-next"],
            "skill_receipts": [
                {
                    "skill": "agent-next",
                    "path": "skills/agent-next/SKILL.md",
                    "sha256": stage_gate.sha256_file(ROOT / "skills/agent-next/SKILL.md"),
                    "supports_phase": "Regression Plan",
                }
            ],
            "repositories": {"dev": [], "test": [], "tools": []},
            "repository_evidence": [],
            "knowledge_used": [],
            "knowledge_plan": {"status": "not_needed", "summary": "", "evidence": []},
            "environment": {"required_groups": [], "checked_groups": [], "target": ""},
            "confirmations": [],
            "artifacts": [
                {
                    "id": "TC-SET-001",
                    "type": "test_cases",
                    "path": str(case_path),
                    "producer_phase": "Regression Plan",
                    "source_artifacts": [],
                    "evidence": [],
                    "validation": {"status": "pending"},
                }
            ],
            "traceability": [],
            "gate_results": [],
            "notes": ["bug_surface: backend"],
        }
            errors = stage_gate.check_state(state)
            self.assertTrue(
                any("test-case-design-methodology.md" in error for error in errors),
                errors,
            )
            self.assertTrue(
                any("coverage-review-rules.md" in error for error in errors),
                errors,
            )
            self.assertTrue(
                any("case-writing-rules.md" in error for error in errors),
                errors,
            )

            state["knowledge_used"] = [
                {
                    "path": validate_test_cases.TEST_CASE_DESIGN_RULES_PATH,
                    "used_for": ["case design"],
                },
                {
                    "path": validate_test_cases.COVERAGE_REVIEW_RULES_PATH,
                    "used_for": ["coverage review"],
                },
                {
                    "path": validate_test_cases.CASE_RULES_PATH,
                    "used_for": ["case writing"],
                },
            ]
            self.assertFalse(
                any("test_cases artifact requires knowledge_used path" in error for error in stage_gate.check_state(state))
            )


if __name__ == "__main__":
    unittest.main()
