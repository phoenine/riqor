from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.phases import phase_validation_error
from tools.workflow_registry import load_workflows


ROOT = Path(__file__).resolve().parents[1]


class WorkflowRegistryTests(unittest.TestCase):
    def test_builtin_workflows_declare_phases_and_scope_directories(self) -> None:
        registry = load_workflows(ROOT)
        self.assertEqual(registry.errors, [])
        self.assertEqual(
            set(registry.records),
            {"feature-quality", "bug-regression", "release-acceptance"},
        )
        self.assertEqual(
            registry.records["feature-quality"].scope_directory, "features"
        )
        self.assertEqual(
            registry.records["bug-regression"].phases[0].name, "Bug Intake"
        )
        self.assertTrue(
            registry.records["feature-quality"].phases[0].gate["require_intake_input"]
        )
        self.assertEqual(
            registry.records["bug-regression"]
            .phases[5]
            .gate["conditional_artifact_requirements"][0]["artifact_types"],
            ["test_cases"],
        )

    def test_custom_workflow_is_not_a_core_enum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = root / "workflows/custom-quality"
            (pack / "phases").mkdir(parents=True)
            (pack / "README.md").write_text("# Custom\n", encoding="utf-8")
            (pack / "phases/01-review.md").write_text("# Review\n", encoding="utf-8")
            (pack / "workflow.yaml").write_text(
                """schema_version: 1
id: custom-quality
readme: README.md
scope_directory: reviews
phases:
  - name: Review
    document: phases/01-review.md
    gate: {}
""",
                encoding="utf-8",
            )
            registry = load_workflows(root)
            self.assertEqual(registry.errors, [])
            self.assertIn("custom-quality", registry.records)
            self.assertIsNone(
                phase_validation_error("custom-quality", "Review", root=root)
            )


if __name__ == "__main__":
    unittest.main()
