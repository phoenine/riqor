from __future__ import annotations

import unittest
from pathlib import Path

from tools.doctor import run_doctor


ROOT = Path(__file__).resolve().parents[1]


class DoctorTests(unittest.TestCase):
    def test_example_project_passes(self) -> None:
        report = run_doctor(ROOT / "examples/shop-platform/project.yaml", ROOT)
        self.assertEqual(report.errors, [])
        self.assertIn("project shop-platform", report.checks)
        self.assertIn("capabilities 17", report.checks)
        self.assertIn("artifact templates 16", report.checks)


if __name__ == "__main__":
    unittest.main()
