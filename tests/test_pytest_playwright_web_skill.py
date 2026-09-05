from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/pytest-playwright-web/scripts/scaffold_framework.py"
RUNTIME_URL = "https://github.com/phoenine/rigor-test.git"


def load_scaffolder():
    spec = importlib.util.spec_from_file_location("scaffold_web_framework", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PytestPlaywrightWebSkillTests(unittest.TestCase):
    def test_scaffold_creates_project_without_product_coupling(self):
        module = load_scaffolder()
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "web-tests"
            paths = module.scaffold(
                destination,
                "demo-web-tests",
                RUNTIME_URL,
                "v0.2.0",
            )

            self.assertTrue(paths)
            manifest = (destination / "pyproject.toml").read_text()
            self.assertIn('name = "demo-web-tests"', manifest)
            self.assertIn(
                "rigorpath-api-test[web] @ git+https://github.com/phoenine/rigor-test.git@v0.2.0",
                manifest,
            )
            self.assertTrue((destination / "pages/__init__.py").is_file())
            self.assertTrue((destination / "tests/test_runtime_smoke.py").is_file())
            env_example = (destination / ".env.example").read_text()
            self.assertNotIn("secret", env_example.lower())

    def test_scaffold_refuses_nonempty_destination(self):
        module = load_scaffolder()
        with TemporaryDirectory() as temporary:
            destination = Path(temporary)
            (destination / "owned.txt").write_text("user data")
            with self.assertRaises(FileExistsError):
                module.scaffold(destination, "web-tests", RUNTIME_URL, "v0.2.0")

    def test_scaffold_rejects_moving_runtime_branch(self):
        module = load_scaffolder()
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "immutable"):
                module.scaffold(
                    Path(temporary) / "web-tests",
                    "web-tests",
                    RUNTIME_URL,
                    "main",
                )


if __name__ == "__main__":
    unittest.main()
