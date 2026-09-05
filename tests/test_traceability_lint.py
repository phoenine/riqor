from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from helpers import load_tool


traceability_lint = load_tool("traceability_lint")


TEST_POINTS_WITH_DANGLING_REFERENCE = """# 测试点

## 摘要

analysis_depth: complex

## 测试空间

| 来源 | 风险 / 覆盖意图 | 维度 | 条件 | 技术 | 说明 |
|---|---|---|---|---|---|

## 需求覆盖

| Atomic Requirement ID | 测试点 ID / Coverage Gap | 覆盖说明 |
|---|---|---|
| REQ-001 | TP-001 | 登录主流程 |

## 风险覆盖

| 风险 ID | 测试点 ID | 覆盖说明 |
|---|---|---|
| RISK-024 | TP-001 / TP-043 / TP-044 | 防探测 |

## 测试点列表

| ID | 测试点 | 优先级 | 维度 | 条件 | 技术 | 覆盖意图 | 依据 |
|---|---|---|---|---|---|---|---|
| TP-001 | 登录主流程 | P1 | Functional | 正常登录 | Scenario | 登录成功 | REQ-001 |
| TP-043 | 凭证模糊提示一致性防探测 | P1 | Security | 不同账号状态 | Negative | 响应不可枚举 | RISK-024 |

## 复杂度辅助分析

不适用。

## 覆盖缺口

## 可追溯关系
"""


class TraceabilityLintTests(unittest.TestCase):
    def test_requirement_merged_evidence_is_a_traceability_reference_field(self):
        text = (
            "# 需求说明书\n"
            "### REQ-001 Login\n"
            "**依据**：明确来源 · 已确认 · RA-001\n"
        )

        references = traceability_lint._unsupported_ra_references(
            text, "requirement_spec"
        )

        self.assertEqual(references, [("RA-001", 3)])

    def test_test_points_dangling_reference_is_error(self):
        errors = traceability_lint.lint_test_points_text(
            TEST_POINTS_WITH_DANGLING_REFERENCE,
            source="test-points.md",
        )
        self.assertTrue(any("TP-044 NOT FOUND" in error for error in errors), errors)
        self.assertFalse(any("TP-043 NOT FOUND" in error for error in errors), errors)

    def test_run_lint_resolves_cross_artifact_references(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "outputs/demo"
            output.mkdir(parents=True)
            files = {
                "requirement_spec": (
                    "requirements.md",
                    "# 需求说明书\n### REQ-001 Login\n"
                    "| SRC-001 | PRD | docs/prd.md | Login |\n"
                    "**依据**：明确来源 · 已确认 · SRC-001 §2\n"
                    "| BR-001 | Rule | Note |\n"
                    "| Q-001 | Question | Impact | Owner |\n"
                    "## 可追溯关系\n| REQ-001 | BR-001 | Q-001 |\n",
                ),
                "risk_analysis": (
                    "risks.md",
                    "# 风险分析\n### RISK-001 Failure\n**来源**：REQ-001 / BR-001 / Q-001\n",
                ),
                "test_points": (
                    "test-points.md",
                    TEST_POINTS_WITH_DANGLING_REFERENCE.replace("RISK-024", "RISK-001").replace(
                        " / TP-044", ""
                    ),
                ),
                "test_cases": (
                    "test-cases.md",
                    "# 测试用例\n### TC-001：Login\n可追溯关系：TP-001 / REQ-001\n",
                ),
                "automation_implementation": (
                    "automation.md",
                    "# 自动化实现记录\n## 来源覆盖\n"
                    "| AUTO ID | TC | DATA | TP | REQ / BR / RISK / Q | Assertion Type | 说明 |\n"
                    "|---|---|---|---|---|---|---|\n"
                    "| AUTO-001 | TC-001 | none | TP-001 | REQ-001 | requirement | login |\n"
                    "## 可追溯关系\n| TC-001 | AUTO-001 | automated_by |\n",
                ),
            }
            artifacts = []
            for artifact_type, (filename, content) in files.items():
                path = output / filename
                path.write_text(content, encoding="utf-8")
                artifacts.append(
                    {
                        "id": filename,
                        "type": artifact_type,
                        "path": path.relative_to(root).as_posix(),
                    }
                )
            state = {
                "artifacts": artifacts,
                "traceability": [
                    {"from": "REQ-001", "to": "RISK-001", "relation": "drives"},
                    {"from": "RISK-001", "to": "TP-001", "relation": "covered_by"},
                    {"from": "TP-001", "to": "TC-001", "relation": "implemented_by"},
                    {"from": "TC-001", "to": "AUTO-001", "relation": "automated_by"},
                ],
            }

            self.assertEqual(
                traceability_lint.lint_run_state_traceability(state, repo_root=root), []
            )

    def test_run_lint_rejects_dangling_requirement_source(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "outputs/demo"
            output.mkdir(parents=True)
            requirement_path = output / "requirements.md"
            requirement_path.write_text(
                "# 需求说明书\n### REQ-001 Login\n"
                "**依据**：明确来源 · 已确认 · SRC-999 §2\n",
                encoding="utf-8",
            )
            state = {
                "artifacts": [
                    {
                        "id": "REQ-SPEC-001",
                        "type": "requirement_spec",
                        "path": requirement_path.relative_to(root).as_posix(),
                    }
                ]
            }

            errors = traceability_lint.lint_run_state_traceability(
                state, repo_root=root
            )

            self.assertTrue(any("SRC-999 NOT FOUND" in error for error in errors), errors)

    def test_run_lint_rejects_dangling_state_endpoint_and_undefined_ra(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "outputs/demo"
            output.mkdir(parents=True)
            risk_path = output / "risks.md"
            risk_path.write_text(
                "# 风险分析\n### RISK-001 Failure\n**来源**：RA-001\n",
                encoding="utf-8",
            )
            state = {
                "artifacts": [
                    {
                        "id": "RISK-SET-001",
                        "type": "risk_analysis",
                        "path": risk_path.relative_to(root).as_posix(),
                    }
                ],
                "traceability": [
                    {"from": "RISK-001", "to": "TP-999", "relation": "covered_by"}
                ],
            }

            errors = traceability_lint.lint_run_state_traceability(state, repo_root=root)

            self.assertTrue(any("RA-001 has no defined RA contract" in error for error in errors), errors)
            self.assertTrue(any("TP-999 NOT FOUND" in error for error in errors), errors)

    def test_run_lint_rejects_dangling_auto_reference(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "outputs/demo"
            output.mkdir(parents=True)
            cases = output / "test-cases.md"
            cases.write_text(
                "# 测试用例\n### TC-001：Login\n可追溯关系：AUTO-999\n",
                encoding="utf-8",
            )
            state = {
                "artifacts": [
                    {
                        "id": "TC-SET-001",
                        "type": "test_cases",
                        "path": cases.relative_to(root).as_posix(),
                    }
                ]
            }

            errors = traceability_lint.lint_run_state_traceability(state, repo_root=root)

            self.assertTrue(any("AUTO-999 NOT FOUND" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
