import unittest

from helpers import ROOT, load_tool

paths = load_tool("paths")


class PathsTests(unittest.TestCase):
    def test_resolve_strips_legacy_prefix(self):
        resolved = paths.resolve_repo_path("knowledge/.gitkeep")
        self.assertEqual(resolved, ROOT / "knowledge" / ".gitkeep")
        self.assertTrue(resolved.exists())
        legacy = paths.resolve_repo_path("agent-next/knowledge/.gitkeep")
        self.assertEqual(legacy, resolved)

    def test_resolve_plain_relative(self):
        resolved = paths.resolve_repo_path("config/projects.yaml")
        self.assertEqual(resolved, ROOT / "config" / "projects.yaml")

    def test_as_repo_path(self):
        self.assertEqual(
            paths.as_repo_path(ROOT / "skills" / "agent-next" / "SKILL.md"),
            "skills/agent-next/SKILL.md",
        )
        self.assertEqual(
            paths.as_repo_path("knowledge/.gitkeep"),
            "knowledge/.gitkeep",
        )
        self.assertEqual(
            paths.as_repo_path("agent-next/knowledge/.gitkeep"),
            "knowledge/.gitkeep",
        )
        self.assertEqual(
            paths.as_repo_path("agent-next/workflows/feature-quality/README.md"),
            "workflows/feature-quality/README.md",
        )

    def test_managed_repo_path_rejects_absolute_and_parent_escape(self):
        with self.assertRaisesRegex(ValueError, "repo-relative under outputs"):
            paths.resolve_managed_repo_path("/tmp/out.md", "outputs")
        with self.assertRaisesRegex(ValueError, "stay under outputs"):
            paths.resolve_managed_repo_path("outputs/../README.md", "outputs")

    def test_managed_repo_path_accepts_output_path(self):
        self.assertEqual(
            paths.resolve_managed_repo_path("outputs/v2/demo.md", "outputs"),
            paths.AGENT_NEXT_ROOT / "outputs/v2/demo.md",
        )


if __name__ == "__main__":
    unittest.main()
