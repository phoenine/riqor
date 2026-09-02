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
            complete(destination)
            errors = validate_artifact.validate_artifact_file(
                destination,
                expected_artifact_type="requirement_spec",
                expected_artifact_id="REQ-SPEC-001",
            )
            self.assertEqual(errors, [])

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


if __name__ == "__main__":
    unittest.main()
