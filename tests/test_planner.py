from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import json
import yaml

from tools.inventory import load_inventory
from tools.planner import (
    CapabilityRecord,
    CapabilityRegistry,
    build_plan,
    load_capabilities,
)


ROOT = Path(__file__).resolve().parents[1]
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


def write_ready(root: Path, artifact_id: str, artifact_type: str, scope: str) -> None:
    path = root / "runs" / artifact_id / "artifacts" / f"{artifact_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": 1,
        "id": artifact_id,
        "type": artifact_type,
        "project_id": "sample-project",
        "scope_id": scope,
        "tracks": ["web"],
        "status": "ready",
        "revision": 1,
        "content_path": f"outputs/sample-project/content/{artifact_id}.md",
        "source_artifacts": [],
        "evidence": [],
        "validation": {"status": "passed"},
    }
    content = root / metadata["content_path"]
    content.parent.mkdir(parents=True, exist_ok=True)
    content.write_text(f"# {artifact_id}\n", encoding="utf-8")
    path.write_text(json.dumps(metadata), encoding="utf-8")


class PlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_capabilities(ROOT, workflow="feature-quality")
        self.assertEqual(self.registry.errors, [])

    def test_plans_full_chain_from_prd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_ready(root, "PRD-001", "prd", "checkout")
            inventory = load_inventory(root, PROFILE)
            report = build_plan(
                goal="test_cases",
                scope_id="checkout",
                inventory=inventory,
                registry=self.registry,
            )
            self.assertEqual(report.blockers, [])
            self.assertEqual(
                [step.capability_id for step in report.steps],
                [
                    "feature-intake",
                    "requirement-specification",
                    "document-risk-analysis",
                    "test-point-design",
                    "test-case-design",
                ],
            )

    def test_existing_requirement_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_ready(root, "PRD-001", "prd", "checkout")
            write_ready(root, "REQ-001", "requirement_spec", "checkout")
            report = build_plan(
                goal="test_cases",
                scope_id="checkout",
                inventory=load_inventory(root, PROFILE),
                registry=self.registry,
            )
            self.assertNotIn(
                "requirement-specification",
                [step.capability_id for step in report.steps],
            )

    def test_missing_external_input_blocks_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = build_plan(
                goal="test_cases",
                scope_id="checkout",
                inventory=load_inventory(Path(temporary), PROFILE),
                registry=self.registry,
            )
            self.assertTrue(any("missing external input prd" in item for item in report.blockers))

    def test_scope_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_ready(root, "PRD-OTHER", "prd", "other-feature")
            report = build_plan(
                goal="test_cases",
                scope_id="checkout",
                inventory=load_inventory(root, PROFILE),
                registry=self.registry,
            )
            self.assertTrue(any("missing external input prd" in item for item in report.blockers))

    def test_ready_goal_needs_no_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_ready(root, "TC-001", "test_cases", "checkout")
            report = build_plan(
                goal="test_cases",
                scope_id="checkout",
                inventory=load_inventory(root, PROFILE),
                registry=self.registry,
            )
            self.assertTrue(report.ready)
            self.assertEqual(report.steps, [])

    def test_automation_implementation_uses_prepare_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_ready(root, "TC-001", "test_cases", "checkout")
            write_ready(root, "AUTO-CLASS-001", "automation_classification", "checkout")
            report = build_plan(
                goal="automation_implementation",
                scope_id="checkout",
                inventory=load_inventory(root, PROFILE),
                registry=self.registry,
            )
            self.assertEqual(report.blockers, [])
            self.assertEqual(
                [step.capability_id for step in report.steps],
                ["feature-intake", "automation-prepare"],
            )
            self.assertEqual(report.steps[-1].skill, "pytest-yaml-api")

    def test_stale_artifact_is_planned_for_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_ready(root, "PRD-001", "prd", "checkout")
            write_ready(root, "REQ-001", "requirement_spec", "checkout")
            write_ready(root, "RISK-001", "risk_analysis", "checkout")
            risk_path = root / "runs/RISK-001/artifacts/RISK-001.json"
            risk = json.loads(risk_path.read_text(encoding="utf-8"))
            risk["status"] = "stale"
            risk["validation"]["status"] = "pending"
            risk_path.write_text(json.dumps(risk), encoding="utf-8")

            report = build_plan(
                goal="risk_analysis",
                scope_id="checkout",
                inventory=load_inventory(root, PROFILE),
                registry=self.registry,
            )
            self.assertEqual(report.blockers, [])
            self.assertEqual(
                [step.capability_id for step in report.steps],
                ["feature-intake", "document-risk-analysis"],
            )
            self.assertIn("risk_analysis (stale)", report.steps[1].reason)

    def test_multiple_producers_block_instead_of_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_ready(root, "PRD-001", "prd", "checkout")
            write_ready(root, "REQ-001", "requirement_spec", "checkout")
            duplicate = CapabilityRecord(
                path=Path("workflows/custom/capabilities/other-risk.yaml"),
                metadata={
                    "schema_version": 1,
                    "id": "other-risk-analysis",
                    "title": "Other risk analysis",
                    "requires": {"all": ["requirement_spec"]},
                    "produces": ["risk_analysis"],
                    "side_effect": False,
                    "action_class": "local_write",
                },
            )
            registry = CapabilityRegistry(records=[*self.registry.records, duplicate])
            report = build_plan(
                goal="risk_analysis",
                scope_id="checkout",
                inventory=load_inventory(root, PROFILE),
                registry=registry,
            )
            self.assertTrue(
                any("multiple capabilities produce risk_analysis" in item for item in report.blockers)
            )

    def test_multiple_workflow_packs_require_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capability = {
                "schema_version": 1,
                "id": "produce-result",
                "title": "Produce result",
                "workflow": "bug-regression",
                "phase": "Bug Intake",
                "skill": "agent-next",
                "produces": ["result"],
                "side_effect": False,
                "action_class": "local_write",
            }
            for pack in ("feature-quality", "bug-regression"):
                path = root / "workflows" / pack / "capabilities" / "result.yaml"
                path.parent.mkdir(parents=True)
                path.write_text(yaml.safe_dump(capability), encoding="utf-8")
            skill_path = root / "skills" / "agent-next" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text("---\nname: agent-next\ndescription: test fixture\n---\n", encoding="utf-8")

            unresolved = load_capabilities(root)
            self.assertTrue(
                any("multiple workflow packs found" in error for error in unresolved.errors)
            )
            selected = load_capabilities(root, workflow="bug-regression")
            self.assertEqual(selected.errors, [])
            self.assertEqual(selected.workflow, "bug-regression")


if __name__ == "__main__":
    unittest.main()
