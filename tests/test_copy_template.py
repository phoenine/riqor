from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from helpers import ROOT, load_tool

copy_template = load_tool("copy_template")
run_state = load_tool("run_state")


class CopyTemplateTests(unittest.TestCase):
    def test_all_managed_templates_use_artifact_md_tmpl_sources(self):
        for name, (template_path, _artifact_type) in copy_template.TEMPLATES.items():
            with self.subTest(template=name):
                self.assertTrue(template_path.startswith("artifacts/"))
                self.assertTrue(template_path.endswith(".md.tmpl"))
                self.assertTrue((ROOT / "templates" / template_path).is_file())

    def test_create_artifact_from_template_and_register_state(self):
        with TemporaryDirectory() as tmp:
            runs_root = Path(tmp) / "runs"
            destination = Path(tmp) / "out" / "requirement.md"
            run_state.update_state(
                Namespace(
                    run_id="demo",
                    runs_root=runs_root,
                    project_id="shop-platform",
                    track=["storefront"],
                    entry="feature-quality",
                    workflow="workflows/feature-quality/README.md",
                    phase="Requirement Specification",
                    required_skill=[],
                    loaded_skill=[],
                    skill_receipt=[],
                    required_env=[],
                    checked_env=[],
                    target=None,
                )
            )

            path, registered = copy_template.create_artifact(
                Namespace(
                    run_id="demo",
                    runs_root=runs_root,
                    templates_root=ROOT / "templates",
                    template="requirement-spec",
                    destination=destination,
                    producer_phase="Requirement Specification",
                    artifact_id="REQ-SPEC-001",
                    source_artifact=["PRD-001"],
                    evidence=["feishu:doc-001"],
                    validation_status="pending",
                    overwrite=False,
                    allow_external_destination_for_tests=True,
                )
            )

            self.assertEqual(path, destination)
            self.assertTrue(registered)
            content = destination.read_text(encoding="utf-8")
            self.assertFalse(content.startswith("---"))
            self.assertIn("# 需求说明书", content)

            state = json.loads((runs_root / "demo" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["artifacts"][0]["id"], "REQ-SPEC-001")
            self.assertEqual(state["artifacts"][0]["source_artifacts"], ["PRD-001"])
            self.assertEqual(state["artifacts"][0]["evidence"], ["feishu:doc-001"])

    def test_existing_destination_requires_overwrite(self):
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "artifact.md"
            destination.write_text("exists", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                copy_template.create_artifact(
                    Namespace(
                        run_id="demo",
                        runs_root=Path(tmp) / "runs",
                        templates_root=ROOT / "templates",
                        template="test-cases",
                        destination=destination,
                        producer_phase="Test Design",
                        artifact_id=None,
                        source_artifact=[],
                        evidence=[],
                        validation_status="pending",
                        overwrite=False,
                        allow_external_destination_for_tests=True,
                    )
                )

    def test_bug_regression_templates(self):
        expected = {
            "change-scope": ("change_scope", "# 变更范围"),
            "coverage-match": ("coverage_match", "# 覆盖匹配"),
            "regression-plan": ("regression_plan", "# 回归计划"),
        }
        with TemporaryDirectory() as tmp:
            for template, (artifact_type, heading) in expected.items():
                destination = Path(tmp) / f"{template}.md"
                path, _registered = copy_template.create_artifact(
                    Namespace(
                        run_id="demo",
                        runs_root=Path(tmp) / "runs",
                        templates_root=ROOT / "templates",
                        template=template,
                        destination=destination,
                        producer_phase="Regression Plan",
                        artifact_id=f"{artifact_type}:demo",
                        source_artifact=[],
                        evidence=[],
                        validation_status="pending",
                        overwrite=False,
                        allow_external_destination_for_tests=True,
                    )
                )
                content = destination.read_text(encoding="utf-8")
                self.assertEqual(path, destination)
                self.assertFalse(content.startswith("---"))
                self.assertIn(heading, content)

    def test_new_report_and_execution_templates(self):
        expected = {
            "execution-record": ("execution_record", "# 执行记录"),
            "bug-report": ("bug_report", "# Bug 报告草稿"),
            "run-summary": ("run_summary", "# Run Summary"),
            "automation-classification": (
                "automation_classification",
                "# 自动化分类记录",
            ),
        }
        with TemporaryDirectory() as tmp:
            for template, (artifact_type, heading) in expected.items():
                destination = Path(tmp) / f"{template}.md"
                path, registered = copy_template.create_artifact(
                    Namespace(
                        run_id="demo",
                        runs_root=Path(tmp) / "runs",
                        templates_root=ROOT / "templates",
                        template=template,
                        destination=destination,
                        producer_phase="Closeout",
                        artifact_id=f"{artifact_type}:demo",
                        source_artifact=[],
                        evidence=[],
                        validation_status="pending",
                        overwrite=False,
                        allow_external_destination_for_tests=True,
                    )
                )
                content = destination.read_text(encoding="utf-8")
                self.assertEqual(path, destination)
                self.assertFalse(registered)
                self.assertFalse(content.startswith("---"))
                self.assertIn(heading, content)

    def test_destination_must_stay_under_outputs(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "repo-relative under outputs"):
                copy_template.create_artifact(
                    Namespace(
                        run_id="demo",
                        runs_root=Path(tmp) / "runs",
                        templates_root=ROOT / "templates",
                        template="requirement-spec",
                        destination=Path(tmp) / "requirement.md",
                        producer_phase="Requirement Specification",
                        artifact_id="REQ-SPEC-001",
                        source_artifact=[],
                        evidence=[],
                        validation_status="pending",
                        overwrite=False,
                    )
                )


if __name__ == "__main__":
    unittest.main()
