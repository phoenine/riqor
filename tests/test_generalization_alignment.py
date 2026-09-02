from __future__ import annotations

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

    def test_generic_execution_chain_has_no_epvs_skill_dependency(self) -> None:
        paths = [ROOT / "tools" / "stage_gate.py"]
        paths.extend((ROOT / "workflows").glob("*.md"))
        paths.extend((ROOT / "workflows").glob("*/README.md"))
        paths.extend((ROOT / "workflows").glob("*/phases/*.md"))
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("epvs-", path.read_text(encoding="utf-8").lower())

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

    def test_epvs_compatibility_is_explicit_profile_data(self) -> None:
        profile = yaml.safe_load((ROOT / "profiles" / "epvs" / "profile.yaml").read_text(encoding="utf-8"))
        self.assertEqual(profile["legacy"]["skills"]["zentao-sync"], "epvs-zentao-sync")
        self.assertEqual(profile["legacy"]["product_line_tracks"]["v2"], "v2")
        self.assertEqual(profile["private_project_profile"], "config/projects/epvs.yaml")


if __name__ == "__main__":
    unittest.main()
