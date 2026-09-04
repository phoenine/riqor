from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.bootstrap import init_project
from tools.cli import main
from tools.traceability_lint import lint_run_state_traceability
from tools.validate_artifact import validate_artifact_file


def write_ready_artifact(
    root: Path,
    artifact_id: str,
    artifact_type: str,
    content: str,
    *,
    status: str = "ready",
) -> None:
    content_path = root / "outputs/iot-ops/features/login" / f"{artifact_type}.md"
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(content, encoding="utf-8")
    manifest = root / "runs/source-inputs/artifacts" / f"{artifact_id}.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": artifact_id,
                "type": artifact_type,
                "project_id": "iot-ops",
                "scope_id": "login",
                "tracks": ["default"],
                "status": status,
                "revision": 1,
                "content_path": content_path.relative_to(root).as_posix(),
                "source_artifacts": [],
                "evidence": [],
                "validation": {"status": "passed"},
            }
        ),
        encoding="utf-8",
    )


def write_inputs(
    root: Path,
    level: str = "A0",
    target: str = "api",
    destination: str = "iot-ops-api-test",
    classification_status: str = "ready",
) -> None:
    template = (root / "templates/artifacts/automation-classification.md.tmpl").read_text(
        encoding="utf-8"
    )
    completed = re.sub(r"<[^>\n]+>", "completed", template)
    completed = completed.replace(
        "| completed | completed | completed | completed | completed | completed | completed | completed | completed |",
        f"| TC-001 | {level} | {target} | HTTP 200 | none | none | none | API contract | {destination} |",
    )
    write_ready_artifact(
        root,
        "AUTO-CLASS-001",
        "automation_classification",
        completed + "\nCompleted artifact content.\n",
        status=classification_status,
    )
    write_ready_artifact(
        root,
        "TC-SUITE-001",
        "test_cases",
        "# Test Cases\n\n### TC-001：Health check\n",
    )


def prepare_arguments(root: Path) -> list[str]:
    return [
        "prepare-automation",
        "--root",
        str(root),
        "--project",
        "config/projects/iot-ops.yaml",
        "--classification-artifact",
        "AUTO-CLASS-001",
        "--test-cases-artifact",
        "TC-SUITE-001",
        "--implementation-artifact",
        "AUTO-IMPL-001",
        "--run-id",
        "automation-login",
        "--no-install",
    ]


class AutomationPrepareTests(unittest.TestCase):
    def test_prepare_creates_consumer_from_classification_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            init_project(
                root=root,
                project_id="iot-ops",
                name="IoT Ops",
                tracks=["default"],
                default_track="default",
                automations=["api"],
            )
            write_inputs(root)

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(prepare_arguments(root))

            self.assertEqual(status, 0, output.getvalue())
            destination = root / "repositories/automation/iot-ops-api-test"
            self.assertTrue((destination / "pyproject.toml").is_file())
            self.assertIn("OK automation project created", output.getvalue())
            implementation = root / "outputs/iot-ops/features/login/automation-implementation.md"
            self.assertTrue(implementation.is_file())
            self.assertIn(
                "case generation pending", implementation.read_text(encoding="utf-8")
            )
            self.assertEqual(
                validate_artifact_file(
                    implementation,
                    expected_artifact_type="automation_implementation",
                ),
                [],
            )
            self.assertTrue(
                (root / "runs/automation-login/artifacts/AUTO-IMPL-001.json").is_file()
            )
            state = json.loads(
                (root / "runs/automation-login/state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                {artifact["id"] for artifact in state["artifacts"]},
                {"AUTO-CLASS-001", "TC-SUITE-001", "AUTO-IMPL-001"},
            )
            self.assertEqual(lint_run_state_traceability(state, repo_root=root), [])
            self.assertIn("CASES TC-001", output.getvalue())

    def test_prepare_skips_manual_only_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            init_project(
                root=root,
                project_id="iot-ops",
                name="IoT Ops",
                tracks=["default"],
                default_track="default",
                automations=["api"],
            )
            write_inputs(root, level="M0", target="manual_only", destination="none")
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(prepare_arguments(root))
            self.assertEqual(status, 0)
            self.assertIn("SKIPPED", output.getvalue())
            self.assertFalse((root / "repositories/automation/iot-ops-api-test").exists())
            state = json.loads(
                (root / "runs/automation-login/state.json").read_text(encoding="utf-8")
            )
            self.assertTrue(any(note.startswith("optional_skip:") for note in state["notes"]))

    def test_prepare_is_idempotent_for_matching_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            init_project(
                root=root,
                project_id="iot-ops",
                name="IoT Ops",
                tracks=["default"],
                default_track="default",
                automations=["api"],
            )
            write_inputs(root)
            arguments = prepare_arguments(root)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(arguments), 0)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(arguments), 0)
            self.assertIn("OK automation project reused", output.getvalue())
            self.assertIn("OK automation implementation reused", output.getvalue())

    def test_prepare_rejects_unready_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            init_project(
                root=root,
                project_id="iot-ops",
                name="IoT Ops",
                tracks=["default"],
                default_track="default",
                automations=["api"],
            )
            write_inputs(root, classification_status="draft")
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(prepare_arguments(root))
            self.assertEqual(status, 1)
            self.assertIn("classification artifact must be ready", output.getvalue())
            self.assertFalse((root / "repositories/automation/iot-ops-api-test").exists())

    def test_prepare_rejects_destination_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            init_project(
                root=root,
                project_id="iot-ops",
                name="IoT Ops",
                tracks=["default"],
                default_track="default",
                automations=["api"],
            )
            write_inputs(root, destination="another-api-test")
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(prepare_arguments(root))
            self.assertEqual(status, 1)
            self.assertIn("destination must be iot-ops-api-test", output.getvalue())
            self.assertFalse((root / "repositories/automation/iot-ops-api-test").exists())


if __name__ == "__main__":
    unittest.main()
