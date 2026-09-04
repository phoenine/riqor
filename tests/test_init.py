from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.bootstrap import InitError, KNOWLEDGE_DIRECTORIES, init_project
from tools.cli import main
from tools.contracts import (
    load_markdown_frontmatter,
    load_yaml,
    validate_project_profile,
    validate_schema,
)


class InitProjectTests(unittest.TestCase):
    def test_empty_project_creates_valid_profile_and_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = init_project(
                root=root,
                project_id="sample-project",
                name="Sample Project",
                tracks=["default"],
                default_track="default",
            )

            profile = load_yaml(root / result.profile_path)
            self.assertEqual(validate_project_profile(profile), [])
            self.assertEqual(
                profile["artifacts"]["root"], "outputs/sample-project"
            )
            index_path = root / result.knowledge_root / "_index.md"
            frontmatter = load_markdown_frontmatter(index_path)
            self.assertEqual(validate_schema(frontmatter, "knowledge-page"), [])
            sources = load_yaml(root / result.knowledge_root / "_sources.yaml")
            self.assertEqual(validate_schema(sources, "knowledge-sources"), [])
            self.assertEqual(sources["sources"], [])
            for directory in KNOWLEDGE_DIRECTORIES:
                self.assertTrue((root / result.knowledge_root / directory).is_dir())

    def test_sources_are_registered_without_becoming_confirmed_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs" / "prd.md"
            source.parent.mkdir()
            source.write_text("# PRD\n", encoding="utf-8")

            result = init_project(
                root=root,
                project_id="sample-project",
                name="Sample Project",
                tracks=["web", "backend"],
                default_track="backend",
                sources=[Path("docs/prd.md")],
            )

            sources = load_yaml(root / result.knowledge_root / "_sources.yaml")
            self.assertEqual(
                sources["sources"],
                [
                    {
                        "type": "document",
                        "reference": "docs/prd.md",
                        "status": "registered",
                    }
                ],
            )
            gaps = (root / result.knowledge_root / "_gaps.md").read_text(encoding="utf-8")
            self.assertIn("have not been synthesized into confirmed knowledge", gaps)

    def test_existing_project_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = init_project(
                root=root,
                project_id="sample-project",
                name="Sample Project",
                tracks=["default"],
                default_track="default",
            )
            original = (root / first.profile_path).read_text(encoding="utf-8")

            with self.assertRaisesRegex(InitError, "already exists"):
                init_project(
                    root=root,
                    project_id="sample-project",
                    name="Replacement",
                    tracks=["default"],
                    default_track="default",
                )
            self.assertEqual((root / first.profile_path).read_text(encoding="utf-8"), original)

    def test_source_outside_root_is_rejected_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.NamedTemporaryFile() as source:
            root = Path(temporary)
            with self.assertRaisesRegex(InitError, "under the repository root"):
                init_project(
                    root=root,
                    project_id="sample-project",
                    name="Sample Project",
                    tracks=["default"],
                    default_track="default",
                    sources=[Path(source.name)],
                )
            self.assertFalse((root / "config/projects/sample-project.yaml").exists())
            self.assertFalse((root / "knowledge/sample-project").exists())

    def test_default_track_must_be_declared(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(InitError, "default track"):
                init_project(
                    root=Path(temporary),
                    project_id="sample-project",
                    name="Sample Project",
                    tracks=["web"],
                    default_track="backend",
                )

    def test_api_automation_preset_adds_pinned_profile_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = init_project(
                root=root,
                project_id="iot-ops",
                name="IoT Ops",
                tracks=["default"],
                default_track="default",
                automations=["api"],
            )

            profile = load_yaml(root / result.profile_path)
            self.assertEqual(
                profile["repositories"]["automation"],
                [
                    {
                        "id": "iot-ops-api-test",
                        "path": "repositories/automation/iot-ops-api-test",
                        "capabilities": ["api"],
                    }
                ],
            )
            integration = profile["integrations"]["api_automation"]
            self.assertEqual(integration["skill"], "pytest-yaml-api")
            self.assertRegex(integration["config"]["runtime_revision"], r"^[0-9a-f]{40}$")
            self.assertFalse((root / "repositories/automation/iot-ops-api-test").exists())

    def test_unknown_automation_preset_is_rejected_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(InitError, "unknown automation preset"):
                init_project(
                    root=root,
                    project_id="sample-project",
                    name="Sample Project",
                    tracks=["default"],
                    default_track="default",
                    automations=["mobile"],
                )
            self.assertFalse((root / "config/projects/sample-project.yaml").exists())


class InitCliTests(unittest.TestCase):
    def test_cli_creates_default_track_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "init",
                        "--root",
                        temporary,
                        "--project-id",
                        "sample-project",
                        "--name",
                        "Sample Project",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("OK registered sources 0", output.getvalue())
            profile = load_yaml(Path(temporary) / "config/projects/sample-project.yaml")
            self.assertEqual(profile["project"]["tracks"], ["default"])

    def test_cli_configures_api_automation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "init",
                        "--root",
                        temporary,
                        "--project-id",
                        "iot-ops",
                        "--name",
                        "IoT Ops",
                        "--automation",
                        "api",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("OK configured automation api", output.getvalue())


if __name__ == "__main__":
    unittest.main()
