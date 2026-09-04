from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest


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
            paths = module.scaffold(destination, "demo-api-tests", "0.1.0")

            self.assertTrue(paths)
            self.assertIn('name = "demo-api-tests"', (destination / "pyproject.toml").read_text())
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
                module.scaffold(destination, "demo-api-tests", "0.1.0")


if __name__ == "__main__":
    unittest.main()
