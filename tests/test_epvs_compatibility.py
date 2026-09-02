from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from helpers import load_tool
from tools.contracts import load_yaml, validate_project_profile
from tools.doctor import run_doctor


ROOT = Path(__file__).resolve().parents[1]
stage_gate = load_tool("stage_gate")


def receipt(skill: str, phase: str) -> dict[str, str]:
    path = f"skills/{skill}/SKILL.md"
    return {
        "skill": skill,
        "path": path,
        "sha256": stage_gate.sha256_file(ROOT / path),
        "supports_phase": phase,
    }


def state(*, entry: str, phase: str, product_line: str = "v2") -> dict:
    return {
        "schema_version": 2,
        "run_id": f"epvs-r4-{entry}",
        "product_line": product_line,
        "entry": entry,
        "workflow": f"workflows/{entry}/README.md",
        "phase": phase,
        "required_skills": ["agent-next"],
        "loaded_skills": ["agent-next"],
        "skill_receipts": [receipt("agent-next", phase)],
        "repositories": {"dev": [], "test": [], "tools": []},
        "repository_evidence": [],
        "knowledge_used": [],
        "knowledge_plan": {"status": "not_needed", "summary": "fixture", "evidence": []},
        "environment": {"required_groups": [], "checked_groups": [], "target": "local"},
        "confirmations": [],
        "artifacts": [],
        "traceability": [],
        "gate_results": [],
        "notes": [],
    }


def add_skill(run_state: dict, skill: str) -> None:
    run_state["required_skills"].append(skill)
    run_state["loaded_skills"].append(skill)
    run_state["skill_receipts"].append(receipt(skill, run_state["phase"]))


class EpvsR4CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preset = yaml.safe_load(
            (ROOT / "profiles/epvs/profile.yaml").read_text(encoding="utf-8")
        )
        cls.project = load_yaml(ROOT / "profiles/epvs/project.example.yaml")
        cls.scenarios = load_yaml(ROOT / "profiles/epvs/migration-scenarios.yaml")["scenarios"]

    def test_secret_free_project_profile_example_is_valid_and_doctor_ready(self) -> None:
        self.assertEqual(validate_project_profile(self.project), [])
        self.assertEqual(
            self.project["policies"]["require_confirmation"],
            ["remote_write", "shared_environment_execution", "shared_data_mutation"],
        )
        self.assertEqual(run_doctor(ROOT / "profiles/epvs/project.example.yaml", ROOT).errors, [])
        self.assertEqual(
            self.project["integrations"]["test-management"]["config"]["environment_group"],
            "ZENTAO",
        )

        serialized = (ROOT / "profiles/epvs/project.example.yaml").read_text(encoding="utf-8").lower()
        for forbidden in ("password:", "token:", "secret:", "api_key:"):
            self.assertNotIn(forbidden, serialized)

    def test_profile_expresses_all_legacy_tracks_groups_and_output_routes(self) -> None:
        legacy = self.preset["legacy"]
        self.assertEqual(legacy["product_line_tracks"], {"v1": "v1", "v2": "v2", "shared": "shared"})
        self.assertEqual(legacy["repository_groups"], {"dev": "product", "test": "automation", "tools": "tools"})
        self.assertEqual(legacy["output_routing"]["bug"]["backend"], "outputs/shared")
        self.assertEqual(legacy["output_routing"]["bug"]["frontend"], "outputs/<owning-track>")

    def test_selected_historical_scenarios_retain_only_contract_evidence(self) -> None:
        self.assertEqual(
            self.scenarios["feature"]["recorded_passed_gates"],
            ["Requirement Specification", "Risk Analysis"],
        )
        self.assertEqual(self.scenarios["bug"]["recorded_passed_gate_count"], 8)
        self.assertEqual(
            self.scenarios["release"]["release_scope_tracks"],
            ["v2", "shared", "v1"],
        )
        snapshot = (ROOT / "profiles/epvs/migration-scenarios.yaml").read_text(encoding="utf-8").lower()
        for forbidden in ("password:", "token:", "secret:", "api_key:", "192.168."):
            self.assertNotIn(forbidden, snapshot)

    def test_feature_predictive_maintenance_migrates_skill_receipt_and_knowledge_evidence(self) -> None:
        legacy = state(entry="feature-quality", phase="Intake")
        add_skill(legacy, "epvs-requirement")
        legacy["knowledge_used"] = [{
            "path": "skills/epvs-requirement/references/intake-sources.md",
            "used_for": ["feature intake"],
        }]
        self.assertEqual(stage_gate.check_state(legacy), [])

        migrated = state(entry="feature-quality", phase="Intake", product_line="")
        migrated.update({"project_id": "epvs-example", "tracks": ["v2"]})
        add_skill(migrated, "requirement-analysis")
        migrated["knowledge_used"] = [{
            "path": "skills/requirement-analysis/references/intake-sources.md",
            "used_for": ["feature intake"],
        }]
        migrated["notes"] = ["intake_input: controlled v2 feature fixture"]
        self.assertEqual(stage_gate.check_state(migrated, strict_phase=True), [])
        self.assertEqual(
            self.preset["legacy"]["skills"]["requirement-analysis"],
            "epvs-requirement",
        )

    def test_bug_1713_keeps_v1_route_and_confirmation_boundary(self) -> None:
        scenario = self.scenarios["bug"]
        legacy = state(entry="bug-regression", phase="Bug Intake", product_line=scenario["product_line"])
        legacy["notes"] = ["bug_intake: ZenTao bug 1713", f"bug_surface: {scenario['surface']}"]
        legacy["artifacts"] = [{
            "id": "BUG-1713-NOTE",
            "type": "other",
            "path": "outputs/v1/regression/bug-1713.md",
            "producer_phase": "Bug Intake",
            "source_artifacts": [],
            "evidence": [],
            "validation": {"status": "pending"},
        }]
        self.assertEqual(stage_gate.allowed_bug_output_prefix(legacy), "outputs/v1/")
        self.assertEqual(stage_gate.check_state(legacy), [])

        migrated = state(entry="bug-regression", phase="Bug Intake", product_line="")
        migrated.update({"project_id": "epvs-example", "tracks": ["v1"]})
        migrated["notes"] = deepcopy(legacy["notes"])
        migrated["knowledge_used"] = [{
            "path": "skills/test-analysis/references/bug-regression-rules.md",
            "used_for": ["bug intake"],
        }]
        add_skill(migrated, "requirement-analysis")
        self.assertEqual(stage_gate.allowed_bug_output_prefix(migrated), None)
        self.assertEqual(stage_gate.check_state(migrated, strict_phase=True), [])
        self.assertEqual(
            self.project["extensions"]["epvs"]["output_routing"]["bug"],
            "outputs/epvs/bugs/<bug-id>",
        )

        for candidate in (legacy, migrated):
            candidate["confirmations"] = [{
                "id": "zentao-write",
                "action": "update ZenTao bug 1713",
                "status": "required",
            }]
            self.assertIn(
                "confirmation not satisfied: update ZenTao bug 1713 (required)",
                stage_gate.check_state(candidate),
            )

    def test_release_v2_0_1_preserves_tracks_repository_evidence_and_shared_action_gate(self) -> None:
        legacy = state(entry="release-acceptance", phase="Release Baseline")
        add_skill(legacy, "epvs-acceptance")
        legacy["release_scope_tracks"] = ["v1", "v2", "shared"]
        legacy["repositories"]["dev"] = [{
            "kind": "dev",
            "name": "epvs-product-v2",
            "path": "repositories/product/epvs-v2",
            "commit": "controlled-fixture",
        }]
        legacy["repository_evidence"] = [{
            "repo": "epvs-product-v2",
            "evidence_type": "commit",
            "references": ["controlled-fixture"],
            "supports": ["release-v2.0.1-qxcp1"],
        }]
        self.assertEqual(stage_gate.check_state(legacy), [])

        migrated = deepcopy(legacy)
        migrated["product_line"] = ""
        migrated.update({"project_id": "epvs-example", "tracks": ["v2"]})
        migrated["required_skills"] = ["agent-next", "release-acceptance"]
        migrated["loaded_skills"] = ["agent-next", "release-acceptance"]
        migrated["skill_receipts"] = [
            receipt("agent-next", "Release Baseline"),
            receipt("release-acceptance", "Release Baseline"),
        ]
        migrated["knowledge_used"] = [{
            "path": "skills/release-acceptance/references/version-source-sync.md",
            "used_for": ["release baseline"],
        }]
        migrated["notes"] = ["release_baseline: tag=v2.0.1-qxcp1 env=controlled-fixture"]
        self.assertEqual(stage_gate.check_state(migrated, strict_phase=True), [])

        migrated["confirmations"] = [{
            "id": "shared-execution",
            "action": "execute release checks in shared environment",
            "status": "required",
        }]
        self.assertIn(
            "confirmation not satisfied: execute release checks in shared environment (required)",
            stage_gate.check_state(migrated, strict_phase=True),
        )


if __name__ == "__main__":
    unittest.main()
