from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.bootstrap import init_project
from tools.cli import main


ROOT = Path(__file__).resolve().parents[1]


def write_classification(path: Path, level: str = "A0", target: str = "api") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# 自动化分类记录",
                "",
                "| Case ID | Level | Target | Core Oracle | Dependencies | Side Effect | Existing Coverage | Decision Basis | Destination |",
                "|---|---|---|---|---|---|---|---|---|",
                f"| TC-001 | {level} | {target} | HTTP 200 | none | none | none | API contract | iot-ops-api-test |",
            ]
        ),
        encoding="utf-8",
    )


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
            skill_target = root / "skills/pytest-yaml-api"
            shutil.copytree(ROOT / "skills/pytest-yaml-api", skill_target)
            classification = root / "classification.md"
            write_classification(classification)

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "prepare-automation",
                        "--root",
                        str(root),
                        "--project",
                        "config/projects/iot-ops.yaml",
                        "--classification",
                        "classification.md",
                        "--no-install",
                    ]
                )

            self.assertEqual(status, 0, output.getvalue())
            destination = root / "repositories/automation/iot-ops-api-test"
            self.assertTrue((destination / "pyproject.toml").is_file())
            self.assertIn("OK automation project created", output.getvalue())
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
            classification = root / "classification.md"
            write_classification(classification, level="M0", target="manual_only")
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "prepare-automation",
                        "--root",
                        str(root),
                        "--project",
                        "config/projects/iot-ops.yaml",
                        "--classification",
                        "classification.md",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("SKIPPED", output.getvalue())
            self.assertFalse((root / "repositories/automation/iot-ops-api-test").exists())

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
            shutil.copytree(ROOT / "skills/pytest-yaml-api", root / "skills/pytest-yaml-api")
            classification = root / "classification.md"
            write_classification(classification)
            arguments = [
                "prepare-automation",
                "--root",
                str(root),
                "--project",
                "config/projects/iot-ops.yaml",
                "--classification",
                "classification.md",
                "--no-install",
            ]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(arguments), 0)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(arguments), 0)
            self.assertIn("OK automation project reused", output.getvalue())


if __name__ == "__main__":
    unittest.main()
