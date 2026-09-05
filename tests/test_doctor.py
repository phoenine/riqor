from __future__ import annotations

import unittest
from pathlib import Path

from tools.doctor import DoctorReport, _check_automation_provider, run_doctor


ROOT = Path(__file__).resolve().parents[1]


class DoctorTests(unittest.TestCase):
    def test_example_project_passes(self) -> None:
        report = run_doctor(ROOT / "examples/shop-platform/project.yaml", ROOT)
        self.assertEqual(report.errors, [])
        self.assertIn("project shop-platform", report.checks)
        self.assertIn("capabilities 18", report.checks)
        self.assertIn("artifact templates 16", report.checks)

    def test_api_automation_rejects_moving_revision(self) -> None:
        profile = {
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
                        "runtime_url": "https://github.com/phoenine/rigorpath_api_test.git",
                        "runtime_revision": "main",
                    },
                }
            },
        }
        report = DoctorReport()
        _check_automation_provider(profile, ROOT, report, "api")
        self.assertIn(
            "api automation: automation provider config runtime_revision must be an immutable tag or commit",
            report.errors,
        )

    def test_api_automation_reports_unprepared_repository_without_error(self) -> None:
        profile = {
            "repositories": {
                "automation": [
                    {
                        "id": "unprepared-api-test",
                        "path": "repositories/automation/unprepared-api-test",
                        "capabilities": ["api"],
                    }
                ]
            },
            "integrations": {
                "api_automation": {
                    "skill": "pytest-yaml-api",
                    "config": {
                        "runtime_url": "https://github.com/phoenine/rigorpath_api_test.git",
                        "runtime_revision": "957edc6672ef18d3c06fb5b34f3089fcf548640c",
                    },
                }
            },
        }
        report = DoctorReport()
        _check_automation_provider(profile, ROOT, report, "api")
        self.assertEqual(report.errors, [])
        self.assertIn(
            "api automation pending preparation repositories/automation/unprepared-api-test",
            report.checks,
        )


if __name__ == "__main__":
    unittest.main()
