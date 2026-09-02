import json
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import load_tool

phases = load_tool("phases")
phase_doc = load_tool("phase_doc")
ROOT = Path(__file__).resolve().parents[1]
PHASE_DOC_CLI = ROOT / "tools" / "phase_doc.py"


class PhaseDocTests(unittest.TestCase):
    def test_workflow_readme_path(self):
        self.assertEqual(
            phases.workflow_readme_path("bug-regression"),
            "workflows/bug-regression/README.md",
        )

    def test_phase_doc_path_bug_regression_change_scope(self):
        self.assertEqual(
            phases.phase_doc_path("bug-regression", "change scope"),
            "workflows/bug-regression/phases/02-change-scope.md",
        )

    def test_phase_doc_path_feature_testing_optional_phase(self):
        self.assertEqual(
            phases.phase_doc_path("feature-quality", "Optional Case Execute"),
            "workflows/feature-quality/phases/06-optional-case-execute.md",
        )

    def test_phase_doc_files_exist_on_disk(self):
        for entry in phases.WORKFLOW_ENTRIES:
            for phase in phases.CANONICAL_PHASES[entry]:
                path = ROOT / phases.phase_doc_path(entry, phase)
                self.assertTrue(path.is_file(), f"missing {path}")

    def test_cli_prints_phase_path(self):
        result = subprocess.run(
            [
                sys.executable,
                str(PHASE_DOC_CLI),
                "--entry",
                "bug-regression",
                "--phase",
                "Bug Intake",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout.strip(),
            "workflows/bug-regression/phases/01-bug-intake.md",
        )

    def test_cli_list_phases_json(self):
        result = subprocess.run(
            [
                sys.executable,
                str(PHASE_DOC_CLI),
                "--entry",
                "release-acceptance",
                "--list-phases",
                "--json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload), 6)
        self.assertTrue(all(item["exists"] for item in payload))

    def test_cli_unknown_phase_exits_nonzero(self):
        result = subprocess.run(
            [
                sys.executable,
                str(PHASE_DOC_CLI),
                "--entry",
                "bug-regression",
                "--phase",
                "Mystery",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
