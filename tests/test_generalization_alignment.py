from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

from tools.planner import load_capabilities


ROOT = Path(__file__).resolve().parents[1]
GENERIC_SKILLS = (
    "agent-next",
    "requirement-analysis",
    "test-analysis",
    "test-case-design",
    "automation",
    "pytest-yaml-api",
    "pytest-playwright-web",
    "test-execution",
    "reporting",
    "release-acceptance",
    "zentao-sync",
)


class GeneralizationAlignmentTests(unittest.TestCase):
    def test_generic_skills_are_discoverable_by_folder_name(self) -> None:
        for skill in GENERIC_SKILLS:
            with self.subTest(skill=skill):
                path = ROOT / "skills" / skill / "SKILL.md"
                self.assertTrue(path.is_file(), path)
                frontmatter = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
                self.assertEqual(frontmatter["name"], skill)

    def test_capabilities_reference_existing_workflow_phase_and_skill(self) -> None:
        for pack in ("feature-quality", "bug-regression", "release-acceptance"):
            with self.subTest(pack=pack):
                registry = load_capabilities(ROOT, pack)
                self.assertEqual(registry.errors, [])
                self.assertTrue(registry.records)

    def test_repository_distributes_only_generic_skills(self) -> None:
        distributed = {
            path.name
            for path in (ROOT / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        self.assertEqual(distributed, set(GENERIC_SKILLS))

    def test_downstream_skills_do_not_reload_router_documents(self) -> None:
        forbidden = (
            "workflows/index.md",
            "workflows/stage-gates.md",
        )
        workflow_readme = re.compile(r"workflows/[^/]+/README\.md")
        for skill in set(GENERIC_SKILLS) - {"agent-next"}:
            with self.subTest(skill=skill):
                text = (ROOT / "skills" / skill / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                for path in forbidden:
                    self.assertNotIn(path, text)
                self.assertIsNone(workflow_readme.search(text))

    def test_requirement_phase_references_are_discoverable(self) -> None:
        phase = (
            ROOT
            / "workflows/feature-quality/phases/02-requirement-specification.md"
        ).read_text(encoding="utf-8")
        for name in ("requirement-specification.md", "knowledge-proposals.md"):
            with self.subTest(reference=name):
                self.assertIn(name, phase)
                self.assertTrue(
                    (ROOT / "skills/requirement-analysis/references" / name).is_file()
                )

    def test_zentao_stays_skill_first(self) -> None:
        skill = (ROOT / "skills" / "zentao-sync" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("zentao-cli", skill)
        code = "\n".join(
            path.read_text(encoding="utf-8")
            for root in (ROOT / "tools", ROOT / "adapters")
            for path in root.glob("*.py")
        )
        self.assertNotIn("CaseManagementAdapter", code)
        stage_gate = (ROOT / "tools" / "stage_gate.py").read_text(encoding="utf-8")
        self.assertNotIn('"zentao-sync"', stage_gate)


if __name__ == "__main__":
    unittest.main()
