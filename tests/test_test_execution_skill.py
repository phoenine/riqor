from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest

import yaml

from tools.artifact_frontmatter import validate_managed_artifact_body


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/test-execution/scripts/normalize_junit.py"


def load_normalizer():
    spec = importlib.util.spec_from_file_location("normalize_junit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestExecutionSkillTests(unittest.TestCase):
    def _cases(self, root: Path) -> Path:
        path = root / "cases.yaml"
        cases = []
        for index in range(1, 6):
            cases.append(
                {
                    "id": f"AUTO-{index:03d}",
                    "title": f"Case {index}",
                    "source": {
                        "requirements": ["REQ-001"],
                        "business_rules": [],
                        "risks": [],
                        "questions": [],
                        "test_points": ["TP-001"],
                        "test_cases": [f"TC-{index:03d}"],
                        "data_rows": [],
                    },
                }
            )
        path.write_text(yaml.safe_dump({"cases": cases}), encoding="utf-8")
        return path

    def test_normalizes_all_statuses_and_not_run(self):
        module = load_normalizer()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = module.load_cases([self._cases(root)])
            junit = root / "junit.xml"
            junit.write_text(
                """<testsuite>
<testcase name="test_case[AUTO-001]" time="0.1"/>
<testcase name="test_case[AUTO-002]" time="0.2"><failure message="bad value"/></testcase>
<testcase name="test_case[AUTO-003]" time="0.3"><skipped message="blocked: fixture"/></testcase>
<testcase name="test_case[AUTO-004]" time="0.4"><error message="collection failed"/></testcase>
</testsuite>""",
                encoding="utf-8",
            )

            results = module.normalize(cases, module.load_junit([junit]))

            self.assertEqual(
                {result["id"]: result["status"] for result in results},
                {
                    "AUTO-001": "passed",
                    "AUTO-002": "failed",
                    "AUTO-003": "blocked",
                    "AUTO-004": "infrastructure_error",
                    "AUTO-005": "not_run",
                },
            )
            record = module.render_record(
                results,
                {
                    "entry": "feature-quality",
                    "project_id": "demo",
                    "environment": "local",
                    "repository": "repositories/automation/demo",
                    "revision": "abc123",
                    "command": "pytest --junitxml=junit.xml",
                    "exit_code": "1",
                    "started_at": "2026-09-04T10:00:00+08:00",
                    "ended_at": "2026-09-04T10:01:00+08:00",
                },
            )
            self.assertIn("TC-002 | AUTO-002 | automated_by", record)
            self.assertIn("infrastructure_error=1", record)
            self.assertIn("not_run=1", record)
            self.assertEqual(
                validate_managed_artifact_body(record, "execution_record"),
                [],
            )

    def test_unknown_junit_case_is_rejected(self):
        module = load_normalizer()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = module.load_cases([self._cases(root)])
            junit = root / "junit.xml"
            junit.write_text(
                '<testsuite><testcase name="test[AUTO-999]"/></testsuite>',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(module.ExecutionContractError, "AUTO-999"):
                module.normalize(cases, module.load_junit([junit]))

    def test_parameterized_results_aggregate_conservatively(self):
        module = load_normalizer()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = module.load_cases([self._cases(root)])
            junit = root / "junit.xml"
            junit.write_text(
                """<testsuite>
<testcase name="test[AUTO-001-row1]"/>
<testcase name="test[AUTO-001-row2]"><skipped message="unsupported"/></testcase>
</testsuite>""",
                encoding="utf-8",
            )

            results = module.normalize(cases, module.load_junit([junit]))

            self.assertEqual(results[0]["status"], "skipped")
            self.assertEqual(results[0]["executions"], 2)

    def test_runner_crash_marks_unreported_cases_as_infrastructure_error(self):
        module = load_normalizer()
        with TemporaryDirectory() as tmp:
            cases = module.load_cases([self._cases(Path(tmp))])

            results = module.normalize(
                cases,
                {},
                infrastructure_error="pytest collection crashed",
            )

            self.assertTrue(
                all(result["status"] == "infrastructure_error" for result in results)
            )

    def test_unexplained_nonzero_exit_is_rejected(self):
        module = load_normalizer()
        results = [{"status": "passed"}]

        with self.assertRaisesRegex(module.ExecutionContractError, "non-zero"):
            module.validate_exit_code(results, "5")


if __name__ == "__main__":
    unittest.main()
