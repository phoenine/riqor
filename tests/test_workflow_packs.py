from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import json

from tools.inventory import load_inventory
from tools.planner import build_plan, load_capabilities


ROOT = Path(__file__).resolve().parents[1]
PROFILE = {
    "schema_version": 1,
    "project": {"id": "sample-project", "name": "Sample", "tracks": ["backend"]},
    "knowledge": {
        "root": "knowledge/sample-project",
        "template": "standard-product",
        "index": "knowledge/sample-project/_index.md",
    },
    "artifacts": {"root": "outputs/sample-project"},
}


def write_input(root: Path, artifact_id: str, artifact_type: str, scope: str) -> None:
    directory = root / "outputs/sample-project" / scope
    directory.mkdir(parents=True, exist_ok=True)
    content = directory / f"{artifact_id}.md"
    content.write_text("# Input\n", encoding="utf-8")
    metadata = {
        "schema_version": 1,
        "id": artifact_id,
        "type": artifact_type,
        "project_id": "sample-project",
        "scope_id": scope,
        "tracks": ["backend"],
        "status": "ready",
        "revision": 1,
        "content_path": content.relative_to(root).as_posix(),
        "source_artifacts": [],
        "evidence": [],
        "validation": {"status": "passed"},
    }
    record = root / "runs" / artifact_id / "artifacts" / f"{artifact_id}.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(metadata), encoding="utf-8")


class WorkflowPackTests(unittest.TestCase):
    def test_bug_regression_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_input(root, "BUG-001", "bug_report", "bug-001")
            report = build_plan(
                goal="regression_report",
                scope_id="bug-001",
                inventory=load_inventory(root, PROFILE),
                registry=load_capabilities(ROOT, "bug-regression"),
            )
            self.assertEqual(report.blockers, [])
            self.assertEqual(len(report.steps), 7)
            self.assertEqual(report.steps[0].capability_id, "bug-intake")
            self.assertEqual(report.steps[-1].capability_id, "bug-regression-report")
            self.assertEqual(report.steps[-1].workflow, "bug-regression")
            self.assertEqual(report.steps[-1].phase, "Regression Report")
            self.assertEqual(report.steps[-1].skill, "reporting")

    def test_release_acceptance_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_input(root, "BASE-001", "release_baseline", "release-1.0")
            report = build_plan(
                goal="acceptance_report",
                scope_id="release-1.0",
                inventory=load_inventory(root, PROFILE),
                registry=load_capabilities(ROOT, "release-acceptance"),
            )
            self.assertEqual(report.blockers, [])
            self.assertEqual(len(report.steps), 5)
            self.assertEqual(report.steps[0].capability_id, "release-baseline")
            self.assertEqual(report.steps[-1].capability_id, "release-decision")
            self.assertEqual(report.steps[-1].phase, "Release Decision")
            self.assertEqual(report.steps[-1].skill, "release-acceptance")


if __name__ == "__main__":
    unittest.main()
