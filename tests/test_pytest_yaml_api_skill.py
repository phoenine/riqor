from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/pytest-yaml-api/scripts/scaffold_framework.py"


def load_scaffolder():
    spec = importlib.util.spec_from_file_location("scaffold_framework", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PytestYamlApiSkillTests(unittest.TestCase):
    def test_scaffold_creates_traceable_project(self):
        module = load_scaffolder()
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "api-tests"
            paths = module.scaffold(
                destination,
                "demo-api-tests",
                module.DEFAULT_RUNTIME_URL,
                "v0.1.0",
            )

            self.assertTrue(paths)
            self.assertIn('name = "demo-api-tests"', (destination / "pyproject.toml").read_text())
            self.assertIn(
                "git+https://github.com/phoenine/rigorpath_api_test.git@v0.1.0",
                (destination / "pyproject.toml").read_text(),
            )
            case = (destination / "testcases/example.yaml").read_text()
            self.assertIn("AUTO-001", case)
            self.assertIn("TP-001", case)
            self.assertIn("TC-001", case)

    def test_scaffold_refuses_nonempty_destination(self):
        module = load_scaffolder()
        with TemporaryDirectory() as tmp:
            destination = Path(tmp)
            (destination / "owned.txt").write_text("user data")

            with self.assertRaises(FileExistsError):
                module.scaffold(
                    destination,
                    "demo-api-tests",
                    module.DEFAULT_RUNTIME_URL,
                    "v0.1.0",
                )

    def test_scaffold_rejects_moving_runtime_branch(self):
        module = load_scaffolder()
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "immutable"):
                module.scaffold(
                    Path(tmp) / "api-tests",
                    "demo-api-tests",
                    module.DEFAULT_RUNTIME_URL,
                    "main",
                )

    def test_profile_selects_api_repository_and_runtime(self):
        module = load_scaffolder()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "project.yaml"
            profile.write_text(
                yaml.safe_dump(
                    {
                        "repositories": {
                            "automation": [
                                {
                                    "id": "shop-api-test",
                                    "path": "repositories/automation/shop-api-test",
                                    "capabilities": ["api"],
                                }
                            ]
                        },
                        "integrations": {
                            "api_automation": {
                                "skill": "pytest-yaml-api",
                                "config": {
                                    "runtime_url": module.DEFAULT_RUNTIME_URL,
                                    "runtime_revision": "v0.1.0",
                                },
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            destination, name, url, revision = module.settings_from_profile(
                profile, root
            )

            self.assertEqual(
                destination,
                root.resolve() / "repositories/automation/shop-api-test",
            )
            self.assertEqual(name, "shop-api-test")
            self.assertEqual(url, module.DEFAULT_RUNTIME_URL)
            self.assertEqual(revision, "v0.1.0")


if __name__ == "__main__":
    unittest.main()
