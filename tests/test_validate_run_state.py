import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import ROOT, load_tool, write_template_artifact

validate_run_state = load_tool("validate_run_state")
stage_gate = load_tool("stage_gate")


def valid_state():
    skill_path = ROOT / "skills/agent-next/SKILL.md"
    return {
        "schema_version": 2,
        "run_id": "demo",
        "product_line": "v2",
        "entry": "feature-quality",
        "workflow": "workflows/feature-quality/README.md",
        "phase": "Requirement Specification",
        "required_skills": ["agent-next"],
        "loaded_skills": ["agent-next"],
        "skill_receipts": [
            {
                "skill": "agent-next",
                "path": "skills/agent-next/SKILL.md",
                "sha256": stage_gate.sha256_file(skill_path),
                "supports_phase": "Requirement Specification",
            }
        ],
        "repositories": {
            "dev": [
                {
                    "kind": "dev",
                    "name": "newepvs-demo",
                    "path": "repositories/dev/newepvs-demo",
                    "working_tree_state": "unknown",
                }
            ],
            "test": [],
            "tools": [],
        },
        "repository_evidence": [
            {
                "repo": "newepvs-demo",
                "evidence_type": "file",
                "references": ["src/App.tsx"],
                "supports": ["REQ-001"],
            }
        ],
        "knowledge_used": [
            {"path": "skills/test-case-design/references/case-writing-rules.md", "used_for": ["术语确认"]}
        ],
        "knowledge_plan": {
            "status": "not_needed",
            "summary": "未发现需要补充的知识。",
            "evidence": ["skills/test-case-design/references/case-writing-rules.md"],
        },
        "knowledge_proposed_updates": [],
        "environment": {
            "required_groups": ["ZENTAO"],
            "checked_groups": ["ZENTAO"],
            "target": "test",
        },
        "confirmations": [{"id": "c1", "action": "none", "status": "not_required"}],
        "artifacts": [
            {
                "id": "REQ-001",
                "type": "requirement_spec",
                "path": "outputs/v2/requirements/requirement.md",
                "producer_phase": "Requirement Specification",
                "source_artifacts": [],
                "evidence": [],
                "validation": {"status": "pending"},
            }
        ],
        "traceability": [{"from": "REQ-001", "to": "RISK-001", "relation": "drives"}],
        "gate_results": [
            {
                "phase": "Requirement Specification",
                "status": "passed",
                "checks": [{"name": "stage_gate", "status": "passed"}],
            }
        ],
    }


class ValidateRunStateTests(unittest.TestCase):
    def test_valid_state_passes(self):
        with TemporaryDirectory(dir=ROOT / "outputs") as tmp:
            artifact_path = Path(tmp) / "requirement.md"
            write_template_artifact(
                template="requirement-spec",
                destination=artifact_path,
                artifact_id="REQ-001",
                producer_phase="Requirement Specification",
            )
            state = valid_state()
            state["artifacts"][0]["path"] = artifact_path.relative_to(ROOT).as_posix()
            self.assertEqual(validate_run_state.check_state(state), [])

    def test_invalid_defaults_fail_closed(self):
        state = valid_state()
        state["product_line"] = ""
        state["entry"] = ""
        errors = validate_run_state.check_state(state)
        self.assertTrue(any(error.startswith("$:") for error in errors))
        self.assertTrue(any(error.startswith("$.entry:") for error in errors))

    def test_generic_project_track_identity_passes_schema(self):
        state = valid_state()
        state.update({"project_id": "shop-platform", "tracks": ["storefront"], "product_line": ""})
        errors = validate_run_state.check_schema(state, validate_run_state.DEFAULT_SCHEMA)
        self.assertEqual(errors, [])

    def test_schema_version_is_required_and_fixed(self):
        state = valid_state()
        del state["schema_version"]
        errors = validate_run_state.check_schema(state, validate_run_state.DEFAULT_SCHEMA)
        self.assertTrue(any("schema_version" in error for error in errors), errors)

        state["schema_version"] = 1
        errors = validate_run_state.check_schema(state, validate_run_state.DEFAULT_SCHEMA)
        self.assertTrue(any(error.startswith("$.schema_version:") for error in errors), errors)

    def test_invalid_phase_for_entry_fails(self):
        state = valid_state()
        state["phase"] = "Bug Intake"
        errors = validate_run_state.check_state(state)
        self.assertTrue(any(error.startswith("$.phase:") for error in errors))

    def test_missing_router_skill_fails_like_stage_gate(self):
        state = valid_state()
        state["required_skills"] = []
        state["loaded_skills"] = []
        state["skill_receipts"] = []
        errors = validate_run_state.check_state(state)
        self.assertIn("required_skills must include router skill: agent-next", errors)
        self.assertIn("loaded_skills must include router skill: agent-next", errors)

    def test_semantic_rules_reuse_stage_gate_global_checks(self):
        cases = [
            (
                "missing loaded skill",
                lambda state: state["required_skills"].append("reporting"),
                "required skills not loaded: reporting",
            ),
            (
                "missing skill receipt",
                lambda state: state["loaded_skills"].append("reporting")
                or state["required_skills"].append("reporting"),
                "required skill receipts missing: reporting",
            ),
            (
                "invalid skill receipt hash",
                lambda state: state["skill_receipts"][0].update({"sha256": "short"}),
                "skill receipt agent-next has invalid sha256",
            ),
            (
                "unchecked env group",
                lambda state: state["environment"].update({"required_groups": ["ZENTAO", "GITLAB"]}),
                "required env groups not checked: GITLAB",
            ),
            (
                "unsatisfied confirmation",
                lambda state: state["confirmations"][0].update({"status": "required"}),
                "confirmation not satisfied: none (required)",
            ),
            (
                "missing artifact validation status",
                lambda state: state["artifacts"][0]["validation"].pop("status"),
                "artifact REQ-001 missing validation.status",
            ),
        ]
        for name, mutate, expected_error in cases:
            with self.subTest(name=name):
                state = valid_state()
                mutate(state)
                stage_errors = [
                    error
                    for error in stage_gate.check_global_state(state, verify_live_evidence=False)
                    if not error.startswith("phase ")
                ]
                validate_errors = validate_run_state.check_semantic_rules(state)
                self.assertIn(expected_error, stage_errors)
                self.assertIn(expected_error, validate_errors)
                self.assertEqual(stage_errors, validate_errors)

    def test_invalid_knowledge_plan_fails_closed(self):
        state = valid_state()
        state["knowledge_plan"]["status"] = "maybe"
        state["knowledge_plan"]["summary"] = None
        errors = validate_run_state.check_state(state)
        self.assertTrue(any(error.startswith("$.knowledge_plan.status:") for error in errors))
        self.assertTrue(any(error.startswith("$.knowledge_plan.summary:") for error in errors))

    def test_skill_reference_is_valid_knowledge_used_evidence(self):
        state = valid_state()
        state["knowledge_used"] = [
            {
                "path": "skills/test-case-design/references/case-writing-rules.md",
                "used_for": ["case writing"],
            }
        ]
        errors = validate_run_state.check_schema(state, validate_run_state.DEFAULT_SCHEMA)
        self.assertFalse(any(error.startswith("$.knowledge_used") for error in errors), errors)

    def test_custom_schema_path_is_used(self):
        with TemporaryDirectory() as tmp:
            schema_path = Path(tmp) / "strict-run-id.schema.json"
            schema_path.write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "required": ["run_id"],
                        "properties": {
                            "run_id": {"type": "string", "const": "expected-run"},
                        },
                        "additionalProperties": True,
                    }
                ),
                encoding="utf-8",
            )
            state = valid_state()
            errors = validate_run_state.check_state(state, schema_path=schema_path)
            self.assertTrue(any(error.startswith("$.run_id:") for error in errors))


if __name__ == "__main__":
    unittest.main()
