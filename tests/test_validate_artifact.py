from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import unittest

from helpers import ROOT, load_tool

copy_template = load_tool("copy_template")
validate_artifact = load_tool("validate_artifact")


HAND_WRITTEN_REQUIREMENT = """# 需求说明书

## 摘要

手写需求，没有 frontmatter。
"""


def complete(path: Path) -> None:
    text = re.sub(r"<[^>\n]+>", "completed", path.read_text(encoding="utf-8"))
    path.write_text(text + "\nCompleted artifact content.\n", encoding="utf-8")


def complete_requirement(path: Path) -> None:
    text = re.sub(r"<[^>\n]+>", "completed", path.read_text(encoding="utf-8"))
    text = text.replace(
        "**依据**：completed · completed · completed",
        "**依据**：明确来源 · 已确认 · PRD §1",
    )
    path.write_text(text + "\nCompleted artifact content.\n", encoding="utf-8")


def completed_risk_text() -> str:
    text = (ROOT / "templates/artifacts/risk-analysis.md.tmpl").read_text(
        encoding="utf-8"
    )
    text = re.sub(r"<[^>\n]+>", "completed", text)
    return text.replace("**Risk Type**：completed", "**Risk Type**：security").replace(
        "**状态**：completed", "**状态**：pending_validation"
    ).replace("**等级**：completed", "**等级**：P1")


def completed_test_points_text() -> str:
    text = (ROOT / "templates/artifacts/test-points.md.tmpl").read_text(
        encoding="utf-8"
    )
    text = re.sub(r"<[^>\n]+>", "completed", text)
    text = text.replace("analysis_depth:", "analysis_depth: standard", 1)
    text = text.replace(
        "|---|---|---|---|---|---|---|---|\n\n## 复杂度辅助分析",
        "|---|---|---|---|---|---|---|---|\n"
        "| TP-001 | Sample behavior | P2 | Functional | valid | Scenario | observable result | source evidence |\n\n"
        "## 复杂度辅助分析",
    )
    for risk_type in (
        "security",
        "availability_resilience",
        "performance",
        "compatibility",
    ):
        text = text.replace(
            f"| {risk_type} | completed | completed |",
            f"| {risk_type} | not_applicable | non-platform test scope |",
        )
    return text + "\nCompleted artifact content.\n"


class ValidateArtifactTests(unittest.TestCase):
    def test_copy_template_types_are_covered(self):
        copy_template = load_tool("copy_template")
        for _template_key, (_file, artifact_type) in copy_template.TEMPLATES.items():
            if artifact_type == "test_cases":
                continue
            self.assertIn(artifact_type, validate_artifact.ARTIFACT_SPECS, artifact_type)

    def test_every_untouched_managed_template_is_incomplete(self):
        for _template_key, (filename, artifact_type) in copy_template.TEMPLATES.items():
            if artifact_type == "test_cases":
                continue
            with self.subTest(artifact_type=artifact_type):
                errors = validate_artifact.validate_artifact_file(
                    ROOT / "templates" / filename,
                    expected_artifact_type=artifact_type,
                )
                self.assertTrue(
                    any("untouched managed template" in error for error in errors),
                    errors,
                )

    def test_hand_written_requirement_spec_fails(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirement.md"
            path.write_text(HAND_WRITTEN_REQUIREMENT, encoding="utf-8")
            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="requirement_spec"
            )
            self.assertTrue(any("missing template section" in error for error in errors), errors)

    def test_copy_template_requirement_spec_requires_completion(self):
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "requirement.md"
            copy_template.create_artifact(
                Namespace(
                    run_id="demo",
                    runs_root=Path(tmp) / "runs",
                    templates_root=ROOT / "templates",
                    template="requirement-spec",
                    destination=destination,
                    producer_phase="Requirement Specification",
                    artifact_id="REQ-SPEC-001",
                    source_artifact=[],
                    evidence=[],
                    validation_status="pending",
                    overwrite=False,
                    allow_external_destination_for_tests=True,
                )
            )
            errors = validate_artifact.validate_artifact_file(
                destination,
                expected_artifact_type="requirement_spec",
                expected_artifact_id="REQ-SPEC-001",
            )
            self.assertTrue(any("untouched managed template" in error for error in errors))
            complete_requirement(destination)
            errors = validate_artifact.validate_artifact_file(
                destination,
                expected_artifact_type="requirement_spec",
                expected_artifact_id="REQ-SPEC-001",
            )
            self.assertEqual(errors, [])

    def test_requirement_spec_rejects_missing_source_fidelity(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirement.md"
            text = (ROOT / "templates/artifacts/requirement-spec.md.tmpl").read_text(
                encoding="utf-8"
            )
            text = re.sub(r"<[^>\n]+>", "completed", text)
            text = text.replace(
                "**依据**：completed · completed · completed",
                "**依据**：明确来源 · 已确认 · ",
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="requirement_spec"
            )

            self.assertTrue(any("依据 must use" in error for error in errors), errors)

    def test_requirement_spec_rejects_duplicate_and_nested_requirement_ids(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirement.md"
            text = (ROOT / "templates/artifacts/requirement-spec.md.tmpl").read_text(
                encoding="utf-8"
            )
            text = re.sub(r"<[^>\n]+>", "completed", text)
            text = text.replace(
                "**依据**：completed · completed · completed",
                "**依据**：明确来源 · 已确认 · PRD §1",
            )
            atomic_section = text[text.index("### REQ-001 completed") : text.index("## 业务规则")]
            text = text.replace("## 业务规则", atomic_section + "\n### REQ-001-01 nested\n\n## 业务规则")
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="requirement_spec"
            )

            self.assertIn("duplicate Atomic Requirement ID: REQ-001", errors)
            self.assertTrue(any("nested requirement IDs" in error for error in errors), errors)

    def test_requirement_spec_rejects_confirmed_assumption(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirement.md"
            text = (ROOT / "templates/artifacts/requirement-spec.md.tmpl").read_text(
                encoding="utf-8"
            )
            text = re.sub(r"<[^>\n]+>", "completed", text)
            text = text.replace(
                "**依据**：completed · completed · completed",
                "**依据**：待证假设 · 已确认 · Q-001",
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="requirement_spec"
            )

            self.assertTrue(any("assumption cannot be confirmed" in error for error in errors))

    def test_requirement_spec_rejects_non_display_labels_in_merged_evidence(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirement.md"
            text = (ROOT / "templates/artifacts/requirement-spec.md.tmpl").read_text(
                encoding="utf-8"
            )
            text = re.sub(r"<[^>\n]+>", "completed", text)
            text = text.replace(
                "**依据**：completed · completed · completed",
                "**依据**：source_explicit · confirmed · PRD §1",
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="requirement_spec"
            )

            self.assertTrue(any("明确来源" in error for error in errors), errors)
            self.assertTrue(any("已确认" in error for error in errors), errors)

    def test_requirement_spec_accepts_legacy_three_field_evidence(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirement.md"
            text = (ROOT / "templates/artifacts/requirement-spec.md.tmpl").read_text(
                encoding="utf-8"
            )
            text = re.sub(r"<[^>\n]+>", "completed", text)
            text = text.replace(
                "**依据**：completed · completed · completed",
                "**依据类型**：source_explicit\n\n"
                "**确认状态**：confirmed\n\n"
                "**来源定位**：PRD §1",
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="requirement_spec"
            )

            self.assertEqual(errors, [])

    def test_requirement_spec_rejects_merged_and_legacy_evidence_together(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirement.md"
            text = (ROOT / "templates/artifacts/requirement-spec.md.tmpl").read_text(
                encoding="utf-8"
            )
            text = re.sub(r"<[^>\n]+>", "completed", text)
            text = text.replace(
                "**依据**：completed · completed · completed",
                "**依据**：明确来源 · 已确认 · PRD §1\n\n"
                "**依据类型**：source_explicit\n\n"
                "**确认状态**：confirmed\n\n"
                "**来源定位**：PRD §1",
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="requirement_spec"
            )

            self.assertTrue(any("not both" in error for error in errors), errors)

    def test_risk_analysis_requires_typed_risk_details(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk.md"
            path.write_text(completed_risk_text(), encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="risk_analysis"
            )

            self.assertEqual(errors, [])

    def test_risk_analysis_rejects_invalid_type_status_and_level(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk.md"
            text = completed_risk_text().replace(
                "**Risk Type**：security", "**Risk Type**：ordinary"
            ).replace(
                "**状态**：pending_validation", "**状态**：waiting"
            ).replace("**等级**：P1", "**等级**：high")
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="risk_analysis"
            )

            self.assertTrue(any("Risk Type must be one of" in error for error in errors))
            self.assertTrue(any("状态 must be one of" in error for error in errors))
            self.assertTrue(any("等级 must be one of" in error for error in errors))

    def test_accepted_or_dismissed_risk_requires_decision_note(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk.md"
            text = completed_risk_text().replace(
                "**状态**：pending_validation", "**状态**：accepted"
            ).replace("**决策备注**：completed", "**决策备注**：none")
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="risk_analysis"
            )

            self.assertIn("RISK-001: accepted risk requires a non-empty 决策备注", errors)

    def test_risk_analysis_rejects_missing_evidence_and_duplicate_ids(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk.md"
            text = completed_risk_text().replace(
                "**代码证据**：completed", "**代码证据**："
            )
            risk_section = text[text.index("### RISK-001 completed") : text.index("## 覆盖范围审查")]
            text = text.replace("## 覆盖范围审查", risk_section + "\n## 覆盖范围审查")
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="risk_analysis"
            )

            self.assertIn("duplicate Risk ID: RISK-001", errors)
            self.assertIn("RISK-001: missing or empty field '代码证据'", errors)

    def test_test_points_requires_platform_nfr_assessment(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "test-points.md"
            path.write_text(completed_test_points_text(), encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="test_points"
            )

            self.assertEqual(errors, [])

    def test_covered_platform_nfr_assessment_requires_risk_and_test_point(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "test-points.md"
            text = completed_test_points_text().replace(
                "| security | not_applicable | non-platform test scope |",
                "| security | covered | security review completed |",
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="test_points"
            )

            self.assertIn(
                "security: covered assessment requires both RISK-### and TP-###",
                errors,
            )

    def test_regression_plan_from_template_passes(self):
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "plan.md"
            copy_template.create_artifact(
                Namespace(
                    run_id="demo",
                    runs_root=Path(tmp) / "runs",
                    templates_root=ROOT / "templates",
                    template="regression-plan",
                    destination=destination,
                    producer_phase="Regression Plan",
                    artifact_id="REG-PLAN-001",
                    source_artifact=[],
                    evidence=[],
                    validation_status="pending",
                    overwrite=False,
                    allow_external_destination_for_tests=True,
                )
            )
            complete(destination)
            errors = validate_artifact.validate_artifact_file(
                destination,
                expected_artifact_type="regression_plan",
                expected_artifact_id="REG-PLAN-001",
            )
            self.assertEqual(errors, [])

    def test_automation_classification_requires_valid_level_and_target(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "classification.md"
            template = (
                ROOT / "templates/artifacts/automation-classification.md.tmpl"
            ).read_text(encoding="utf-8")
            completed = re.sub(r"<[^>\n]+>", "completed", template)
            completed = completed.replace(
                "| completed | completed | completed | completed | completed | completed | completed | completed | completed |",
                "| TC-001 | A0 | api | HTTP 200 | none | none | none | API contract | shop-api-test |",
            )
            path.write_text(completed + "\nCompleted artifact content.\n", encoding="utf-8")

            self.assertEqual(
                validate_artifact.validate_artifact_file(
                    path, expected_artifact_type="automation_classification"
                ),
                [],
            )

            path.write_text(completed.replace("| A0 | api |", "| ready | service |"))
            errors = validate_artifact.validate_artifact_file(
                path, expected_artifact_type="automation_classification"
            )
            self.assertTrue(any("valid TC-### / Level / Target" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
