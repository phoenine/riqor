from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import json

from tools.inventory import load_inventory


PROFILE = {
    "schema_version": 1,
    "project": {"id": "sample-project", "name": "Sample", "tracks": ["web"]},
    "knowledge": {
        "root": "knowledge/sample-project",
        "template": "standard-product",
        "index": "knowledge/sample-project/_index.md",
    },
    "artifacts": {"root": "outputs/sample-project"},
}


def artifact(
    artifact_id: str,
    artifact_type: str,
    *,
    revision: int = 1,
    sources: list[str] | None = None,
    status: str = "ready",
    scope_id: str = "checkout",
) -> dict:
    return {
        "schema_version": 1,
        "id": artifact_id,
        "type": artifact_type,
        "project_id": "sample-project",
        "scope_id": scope_id,
        "tracks": ["web"],
        "status": status,
        "revision": revision,
        "content_path": f"outputs/sample-project/content/{artifact_id}.md",
        "source_artifacts": sources or [],
        "evidence": [],
        "validation": {"status": "passed" if status == "ready" else "pending"},
    }


def write_artifact(root: Path, name: str, metadata: dict) -> None:
    path = root / "runs" / name / "artifacts" / f"{metadata['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = root / metadata["content_path"]
    content.parent.mkdir(parents=True, exist_ok=True)
    content.write_text(f"# {metadata['id']}\n", encoding="utf-8")
    path.write_text(json.dumps(metadata), encoding="utf-8")


class InventoryTests(unittest.TestCase):
    def test_records_from_another_project_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_artifact(root, "local", artifact("PRD-001", "prd"))
            foreign = artifact("PRD-OTHER", "prd")
            foreign["project_id"] = "other-project"
            foreign["revision"] = "invalid-in-foreign-project"
            write_artifact(root, "foreign", foreign)

            report = load_inventory(root, PROFILE)

            self.assertEqual(report.errors, [])
            self.assertEqual([item.artifact_id for item in report.records], ["PRD-001"])

    def test_invalid_registry_revision_is_reported_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = artifact("REQ-BAD", "requirement_spec")
            metadata["revision"] = "not-a-number"
            path = root / "runs/import/artifacts/REQ-BAD.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(metadata), encoding="utf-8")
            report = load_inventory(root, PROFILE)
            self.assertTrue(any("revision" in error for error in report.errors))

    def test_output_markdown_without_registry_is_not_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "outputs/sample-project/checkout/requirement_spec/REQ-LEGACY.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                """---
artifact_id: REQ-LEGACY
artifact_type: requirement_spec
producer_phase: Requirement Specification
source_artifacts: []
evidence: []
validation:
  status: passed
---
# 需求说明书
""",
                encoding="utf-8",
            )
            report = load_inventory(root, PROFILE)
            self.assertEqual(report.errors, [])
            self.assertEqual(len(report.records), 0)

    def test_registry_revision_marks_downstream_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_artifact(
                root, "source", artifact("REQ-LEGACY", "requirement_spec", revision=2)
            )
            write_artifact(
                root,
                "risk",
                artifact("RISK-001", "risk_analysis", sources=["REQ-LEGACY@1"]),
            )
            report = load_inventory(root, PROFILE)
            risk = next(item for item in report.records if item.artifact_id == "RISK-001")
            self.assertEqual(risk.effective_status, "stale")
            self.assertIn("source revision changed", risk.reasons[0])

    def test_ready_chain_remains_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_artifact(root, "prd", artifact("PRD-001", "prd"))
            write_artifact(
                root,
                "requirement",
                artifact("REQ-001", "requirement_spec", sources=["PRD-001@1"]),
            )
            report = load_inventory(root, PROFILE)
            self.assertEqual(report.errors, [])
            self.assertEqual(
                {item.artifact_id: item.effective_status for item in report.records},
                {"PRD-001": "ready", "REQ-001": "ready"},
            )

    def test_managed_ready_artifact_becomes_stale_after_content_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = artifact("REQ-001", "requirement_spec")
            metadata["run_id"] = "requirement-run"
            write_artifact(root, "requirement-run", metadata)
            record_path = root / "runs/requirement-run/artifacts/REQ-001.json"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            from tools.run_state import sha256_file

            content_path = root / record["content_path"]
            record["content_sha256"] = sha256_file(content_path)
            record_path.write_text(json.dumps(record), encoding="utf-8")
            content_path.write_text("changed\n", encoding="utf-8")

            report = load_inventory(root, PROFILE)

            self.assertEqual(report.records[0].effective_status, "stale")
            self.assertIn("artifact content changed after validation", report.records[0].reasons)

    def test_revision_change_marks_downstream_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_artifact(root, "prd", artifact("PRD-001", "prd", revision=2))
            write_artifact(
                root,
                "requirement",
                artifact("REQ-001", "requirement_spec", sources=["PRD-001@1"]),
            )
            report = load_inventory(root, PROFILE)
            requirement = next(item for item in report.records if item.artifact_id == "REQ-001")
            self.assertEqual(requirement.effective_status, "stale")
            self.assertIn("source revision changed", requirement.reasons[0])

    def test_stale_status_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_artifact(root, "prd", artifact("PRD-001", "prd", revision=2))
            write_artifact(
                root,
                "requirement",
                artifact("REQ-001", "requirement_spec", sources=["PRD-001@1"]),
            )
            write_artifact(
                root,
                "risk",
                artifact("RISK-001", "risk_analysis", sources=["REQ-001@1"]),
            )
            report = load_inventory(root, PROFILE)
            risk = next(item for item in report.records if item.artifact_id == "RISK-001")
            self.assertEqual(risk.effective_status, "stale")
            self.assertIn("source artifact REQ-001@1 is stale", risk.reasons)

    def test_duplicate_artifact_ids_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_artifact(root, "first", artifact("PRD-001", "prd"))
            write_artifact(root, "second", artifact("PRD-001", "prd", scope_id="other"))
            report = load_inventory(root, PROFILE)
            self.assertTrue(any("duplicate artifact id PRD-001" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
