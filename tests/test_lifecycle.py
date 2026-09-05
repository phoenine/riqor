from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.lifecycle import (
    explain_run,
    gate_run,
    prepare_run,
    record_run_evidence,
    required_skills_for,
    run_status,
)
from tools.planner import load_capabilities


ROOT = Path(__file__).resolve().parents[1]
PROFILE = {
    "schema_version": 1,
    "project": {
        "id": "sample-project",
        "name": "Sample",
        "tracks": ["web", "backend"],
        "default_track": "backend",
    },
    "knowledge": {
        "root": "knowledge/sample-project",
        "template": "standard-product",
        "index": "knowledge/sample-project/_index.md",
    },
    "artifacts": {"root": "outputs/sample-project"},
}


class LifecycleTests(unittest.TestCase):
    def test_intake_gate_can_precede_artifact_phase_in_the_same_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "skills", root / "skills")
            shutil.copytree(ROOT / "workflows", root / "workflows")
            capabilities = load_capabilities(ROOT, "feature-quality").records
            intake = next(item for item in capabilities if item.capability_id == "feature-intake")
            requirement = next(
                item for item in capabilities if item.capability_id == "requirement-specification"
            )

            prepare_run(
                root=root,
                profile=PROFILE,
                capability=intake,
                run_id="checkout",
                tracks=["backend"],
            )
            record_run_evidence(
                root=root,
                run_id="checkout",
                knowledge_used=[
                    "path=skills/requirement-analysis/references/intake-sources.md,purpose=intake"
                ],
                knowledge_plan_status="not_needed",
                knowledge_plan_summary="Current knowledge is sufficient.",
                knowledge_plan_evidence=[],
                notes=["intake_input:PRD-001"],
            )
            self.assertEqual(gate_run(root, "checkout"), [])

            prepare_run(
                root=root,
                profile=PROFILE,
                capability=requirement,
                run_id="checkout",
                tracks=["backend"],
            )
            _state, blockers = run_status(root, "checkout")
            self.assertFalse(any("predecessor gate" in item for item in blockers), blockers)

    def test_prepare_run_reuses_run_state_and_phase_skill_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "skills", root / "skills")
            shutil.copytree(ROOT / "workflows", root / "workflows")
            capability = next(
                item
                for item in load_capabilities(ROOT, "feature-quality").records
                if item.capability_id == "test-point-design"
            )
            result = prepare_run(
                root=root,
                profile=PROFILE,
                capability=capability,
                run_id="checkout-test-design",
                tracks=["backend"],
            )
            self.assertEqual(result.state["entry"], "feature-quality")
            self.assertEqual(result.state["phase"], "Test Design")
            self.assertEqual(
                result.state["required_skills"],
                ["agent-next", "test-analysis", "test-case-design"],
            )
            self.assertEqual(
                {item["supports_phase"] for item in result.state["skill_receipts"]},
                {"Test Design"},
            )

    def test_explain_reports_phase_doc_and_real_gate_blockers(self) -> None:
        capability = next(
            item
            for item in load_capabilities(ROOT, "feature-quality").records
            if item.capability_id == "requirement-specification"
        )
        run_id = "_test-lifecycle-explain"
        run_dir = ROOT / "runs" / run_id
        try:
            prepare_run(
                root=ROOT,
                profile=PROFILE,
                capability=capability,
                run_id=run_id,
                tracks=["backend"],
            )
            explanation = explain_run(ROOT, run_id)
            self.assertEqual(
                explanation["phase_doc"],
                "workflows/feature-quality/phases/02-requirement-specification.md",
            )
            self.assertTrue(
                any("predecessor gate passed: Intake" in item for item in explanation["blockers"])
            )
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def test_capability_skill_is_included_when_phase_has_no_fixed_skill(self) -> None:
        capability = next(
            item
            for item in load_capabilities(ROOT, "release-acceptance").records
            if item.capability_id == "release-execution-record"
        )
        self.assertIn("automation", required_skills_for(capability))


if __name__ == "__main__":
    unittest.main()
