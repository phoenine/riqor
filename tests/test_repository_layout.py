from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayoutTests(unittest.TestCase):
    def test_design_directories_exist(self) -> None:
        expected = (
            "config/projects",
            "docs",
            "knowledge",
            "profiles/default",
            "profiles/epvs",
            "workflows/feature-quality",
            "workflows/bug-regression",
            "workflows/release-acceptance",
            "skills",
            "templates",
            "schemas",
            "tools",
            "repositories/product",
            "repositories/automation",
            "repositories/tools",
            "outputs",
            "runs",
            "tests",
        )
        missing = [path for path in expected if not (REPOSITORY_ROOT / path).is_dir()]
        self.assertEqual(missing, [])

    def test_core_has_no_src_package_tree(self) -> None:
        self.assertFalse((REPOSITORY_ROOT / "src").exists())
        self.assertTrue((REPOSITORY_ROOT / "tools/agent_next.py").is_file())

    def test_knowledge_templates_have_one_source(self) -> None:
        template_root = REPOSITORY_ROOT / "templates/knowledge/standard-product"
        self.assertTrue((template_root / "index.md.tmpl").is_file())
        self.assertTrue((template_root / "gaps.md.tmpl").is_file())

    def test_artifact_lifecycle_uses_one_template_source(self) -> None:
        self.assertTrue((REPOSITORY_ROOT / "tools/artifacts.py").is_file())
        self.assertTrue(
            (REPOSITORY_ROOT / "templates/artifacts/requirement-spec.md.tmpl").is_file()
        )
        self.assertFalse((REPOSITORY_ROOT / "templates/TEMPLATE-requirement-spec.md").exists())


if __name__ == "__main__":
    unittest.main()
