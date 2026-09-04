import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from helpers import load_tool, write_template_artifact

stage_gate = load_tool("stage_gate")
ROOT = Path(__file__).resolve().parents[1]


def skill_receipt(skill, phase):
    logical_path = f"skills/{skill}/SKILL.md"
    return {
        "skill": skill,
        "path": logical_path,
        "sha256": stage_gate.sha256_file(ROOT / logical_path),
        "supports_phase": phase,
    }


def valid_state(**overrides):
    gate_results_overridden = "gate_results" in overrides
    state = {
        "schema_version": 3,
        "run_id": "demo",
        "project_id": "shop-platform",
        "tracks": ["storefront"],
        "entry": "feature-quality",
        "workflow": "workflows/feature-quality/README.md",
        "phase": "Intake",
        "required_skills": ["agent-next"],
        "loaded_skills": ["agent-next"],
        "skill_receipts": [skill_receipt("agent-next", "Intake")],
        "repositories": {"dev": [], "test": [], "tools": []},
        "repository_evidence": [],
        "knowledge_used": [],
        "knowledge_plan": {
            "status": "pending",
            "summary": "",
            "evidence": [],
        },
        "environment": {
            "required_groups": ["ZENTAO"],
            "checked_groups": ["ZENTAO"],
            "target": "test",
        },
        "confirmations": [],
        "artifacts": [],
        "traceability": [],
        "gate_results": [],
        "notes": [],
    }
    state.update(overrides)
    phase = stage_gate.normalize_phase(str(state["phase"]), state["entry"])
    state["skill_receipts"][0] = skill_receipt("agent-next", phase)
    phases = stage_gate.CANONICAL_PHASES.get(state["entry"], ())
    if not gate_results_overridden and phase in phases and phases.index(phase) > 0:
        predecessor = phases[phases.index(phase) - 1]
        state["gate_results"] = [
            {
                "phase": predecessor,
                "status": "passed",
                "checks": [{"name": "stage_gate", "status": "passed"}],
            }
        ]
    return state


def add_skill(state, skill, phase):
    state["required_skills"] = sorted(set(state["required_skills"]) | {skill})
    state["loaded_skills"] = sorted(set(state["loaded_skills"]) | {skill})
    state["skill_receipts"].append(skill_receipt(skill, phase))


class StageGateTests(unittest.TestCase):
    def test_repo_root_controls_live_skill_receipt_validation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "skills/agent-next"
            destination.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "skills/agent-next", destination)
            skill_path = destination / "SKILL.md"
            skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            state = valid_state()
            state["skill_receipts"][0]["sha256"] = stage_gate.sha256_file(skill_path)
            self.assertEqual(stage_gate.check_state(state, repo_root=root), [])
            self.assertTrue(any("sha256 does not match" in error for error in stage_gate.check_state(state)))

    def test_stage_gate_docs_use_machine_checked_knowledge_na_note(self):
        docs = (Path(__file__).resolve().parents[1] / "workflows" / "stage-gates.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("knowledge_not_applicable:", docs)
        self.assertNotIn("knowledge.not_applicable_reason", docs)
        self.assertIn("### Machine Rules By Phase", docs)
        self.assertIn("| feature-quality | Intake |", docs)
        self.assertIn("Machine: `intake_input:`", docs)

    def test_valid_state_passes_global_checks(self):
        self.assertEqual(stage_gate.check_state(valid_state()), [])

    def test_schema_version_must_be_current(self):
        state = valid_state(schema_version=1)
        self.assertIn("schema_version must be 3", stage_gate.check_state(state))

    def test_missing_loaded_skill_fails(self):
        state = valid_state()
        state["required_skills"] = ["agent-next", "requirement-analysis"]
        self.assertIn("required skills not loaded: requirement-analysis", stage_gate.check_state(state))
        self.assertIn("required skill receipts missing: requirement-analysis", stage_gate.check_state(state))

    def test_missing_router_skill_fails(self):
        state = valid_state(required_skills=[], loaded_skills=[])
        errors = stage_gate.check_state(state)
        self.assertIn("required_skills must include router skill: agent-next", errors)
        self.assertIn("loaded_skills must include router skill: agent-next", errors)

    def test_required_confirmation_fails(self):
        state = valid_state()
        state["confirmations"] = [{"id": "c1", "action": "run automation", "status": "required"}]
        self.assertIn("confirmation not satisfied: run automation (required)", stage_gate.check_state(state))

    def test_generic_project_and_track_identity_passes(self):
        state = valid_state(project_id="shop-platform", tracks=["storefront"])
        self.assertEqual(stage_gate.check_state(state), [])

    def test_missing_project_identity_fails(self):
        state = valid_state(project_id="", tracks=[])
        self.assertIn(
            "run identity requires project_id with tracks",
            stage_gate.check_state(state),
        )

    def test_project_defined_release_scope_tracks_are_allowed(self):
        state = valid_state(release_scope_tracks=["storefront", "payments"])
        self.assertEqual(stage_gate.check_state(state), [])

    def test_generic_project_defers_bug_output_routing_to_profile(self):
        state = valid_state(
            project_id="shop-platform",
            tracks=["backend"],
            entry="bug-regression",
            workflow="workflows/bug-regression/README.md",
            phase="Bug Intake",
            notes=["bug_surface: backend"],
        )
        state["skill_receipts"][0] = skill_receipt("agent-next", "Bug Intake")
        self.assertEqual(stage_gate.check_state(state), [])

    def test_missing_knowledge_plan_field_fails(self):
        state = valid_state()
        del state["knowledge_plan"]
        self.assertIn("missing top-level field: knowledge_plan", stage_gate.check_state(state))

    def test_workflow_must_match_entry(self):
        state = valid_state(workflow="workflows/bug-regression/README.md")
        self.assertIn(
            "workflow must match entry feature-quality: expected "
            "workflows/feature-quality/README.md, got 'workflows/bug-regression/README.md'",
            stage_gate.check_state(state),
        )

    def test_skill_receipt_must_match_current_file_and_phase(self):
        state = valid_state()
        state["skill_receipts"][0]["sha256"] = "a" * 64
        errors = stage_gate.check_state(state)
        self.assertTrue(any("sha256 does not match current file" in error for error in errors), errors)
        self.assertTrue(any("stale, or for another phase: agent-next" in error for error in errors), errors)

        state = valid_state()
        state["skill_receipts"][0]["supports_phase"] = "Requirement Specification"
        errors = stage_gate.check_state(state)
        self.assertTrue(any("stale, or for another phase: agent-next" in error for error in errors), errors)

    def test_recorded_knowledge_path_must_exist(self):
        state = valid_state(
            knowledge_used=[{"path": "knowledge/does-not-exist.md", "used_for": ["proof"]}]
        )
        self.assertIn(
            "knowledge_used path does not exist: knowledge/does-not-exist.md",
            stage_gate.check_state(state),
        )

    def test_repository_evidence_requires_matching_revision_record(self):
        evidence = [
            {
                "repo": "demo-repo",
                "evidence_type": "file",
                "references": ["src/main.py"],
                "supports": ["REQ-1"],
            }
        ]
        state = valid_state(repository_evidence=evidence)
        self.assertIn(
            "repository_evidence repo has no matching repository record: demo-repo",
            stage_gate.check_state(state),
        )

        state["repositories"]["dev"] = [
            {"kind": "dev", "name": "demo-repo", "path": "repositories/dev/demo-repo"}
        ]
        self.assertIn(
            "repository record demo-repo requires branch, tag, commit, or working_tree_state",
            stage_gate.check_state(state),
        )

        state["repositories"]["dev"][0]["working_tree_state"] = "unknown"
        self.assertNotIn(
            "repository record demo-repo requires branch, tag, commit, or working_tree_state",
            stage_gate.check_state(state),
        )

    def test_strict_phase_requires_predecessor_gate(self):
        state = valid_state(
            phase="Requirement Specification",
            gate_results=[],
            knowledge_used=[{"path": "skills/test-case-design/references/case-writing-rules.md", "used_for": ["terms"]}],
        )
        add_skill(state, "requirement-analysis", "Requirement Specification")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn(
            "phase Requirement Specification requires predecessor gate passed: Intake",
            errors,
        )

    def test_strict_intake_requires_requirement_skill_and_inputs(self):
        state = valid_state(phase="Intake")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn("phase Intake must declare required skills: requirement-analysis", errors)
        self.assertIn("phase Intake requires knowledge_plan.status to be resolved (not pending)", errors)
        self.assertIn("phase Intake requires intake_input note", errors)
        self.assertIn("phase Intake requires knowledge_used or knowledge_not_applicable note", errors)

    def test_strict_intake_passes_with_required_evidence(self):
        state = valid_state(
            phase="Intake",
            knowledge_plan={"status": "not_needed", "summary": "No supplement needed.", "evidence": []},
            knowledge_used=[{"path": "skills/test-case-design/references/case-writing-rules.md", "used_for": ["routing"]}],
            notes=["intake_input: ZenTao requirement 12345"],
        )
        add_skill(state, "requirement-analysis", "Intake")
        self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_knowledge_plan_resolved_statuses_are_used_by_intake_gate(self):
        for status in sorted(stage_gate.RESOLVED_KNOWLEDGE_PLAN_STATUSES):
            with self.subTest(status=status):
                state = valid_state(
                    phase="Intake",
                    knowledge_plan={"status": status, "summary": "Resolved.", "evidence": []},
                    notes=[
                        "intake_input: explicit feature description",
                        "knowledge_not_applicable: tooling-only",
                    ],
                )
                add_skill(state, "requirement-analysis", "Intake")
                self.assertNotIn(
                    "phase Intake requires knowledge_plan.status to be resolved (not pending)",
                    stage_gate.check_state(state, strict_phase=True),
                )

    def test_strict_phase_requires_artifact_and_knowledge(self):
        state = valid_state(phase="Requirement Specification")
        add_skill(state, "requirement-analysis", "Requirement Specification")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn("phase Requirement Specification requires artifact type: requirement_spec", errors)
        self.assertIn(
            "phase Requirement Specification requires knowledge_used or knowledge_not_applicable note",
            errors,
        )

    def test_strict_phase_passes_with_required_artifact_and_knowledge(self):
        with TemporaryDirectory(dir=ROOT / "outputs") as tmp:
            artifact_path = Path(tmp) / "requirement.md"
            write_template_artifact(
                template="requirement-spec",
                destination=artifact_path,
                artifact_id="REQ-001",
                producer_phase="Requirement Specification",
            )
            state = valid_state(phase="Requirement Specification")
            add_skill(state, "requirement-analysis", "Requirement Specification")
            state["knowledge_used"] = [{"path": "skills/test-case-design/references/case-writing-rules.md", "used_for": ["terms"]}]
            state["artifacts"] = [
                {
                    "id": "REQ-001",
                    "type": "requirement_spec",
                    "path": artifact_path.relative_to(ROOT).as_posix(),
                    "producer_phase": "Requirement Specification",
                    "source_artifacts": [],
                    "evidence": [],
                    "validation": {"status": "pending"},
                }
            ]
            self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_optional_phase_can_be_skipped_with_note(self):
        state = valid_state(phase="Optional Case Execute")
        add_skill(state, "automation", "Optional Case Execute")
        state["notes"] = ["optional_skip:Optional Case Execute: manual-only validation for this run"]
        self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_optional_case_execute_accepts_data_injection_skill(self):
        state = valid_state(phase="Optional Case Execute")
        add_skill(state, "automation", "Optional Case Execute")
        state["notes"] = [
            "data_injection: dataset=fixture-001 generator=seed-script"
        ]
        self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_optional_test_report_can_be_skipped_with_note(self):
        state = valid_state(phase="Optional Test Report")
        add_skill(state, "reporting", "Optional Test Report")
        state["notes"] = ["optional_skip:Optional Test Report: report not requested for this run"]
        self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_bug_regression_plan_requires_planning_skills(self):
        state = valid_state(
            entry="bug-regression",
            workflow="workflows/bug-regression/README.md",
            phase="Regression Plan",
            notes=["regression_strategy: targeted regression", "bug_surface: backend"],
        )
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn(
            "phase Regression Plan must declare required skills: automation, reporting, test-case-design",
            errors,
        )

        add_skill(state, "test-case-design", "Regression Plan")
        add_skill(state, "automation", "Regression Plan")
        add_skill(state, "reporting", "Regression Plan")
        artifact_rel = "outputs/shop-platform/regression/_stage_gate_test_plan.md"
        artifact_path = Path(__file__).resolve().parents[1] / artifact_rel
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            write_template_artifact(
                template="regression-plan",
                destination=artifact_path,
                artifact_id="REG-PLAN-001",
                producer_phase="Regression Plan",
            )
            state["artifacts"] = [
                {
                    "id": "REG-PLAN-001",
                    "type": "regression_plan",
                    "path": artifact_rel,
                    "producer_phase": "Regression Plan",
                    "source_artifacts": [],
                    "evidence": [],
                    "validation": {"status": "pending"},
                }
            ]
            self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])
        finally:
            if artifact_path.exists():
                artifact_path.unlink()

    def test_hand_written_artifact_fails_global_check(self):
        with TemporaryDirectory(dir=ROOT / "outputs") as tmp:
            artifact_path = Path(tmp) / "requirement.md"
            artifact_path.write_text("# 需求说明书\n\n手写\n", encoding="utf-8")
            state = valid_state()
            state["artifacts"] = [
                {
                    "id": "REQ-001",
                    "type": "requirement_spec",
                    "path": artifact_path.relative_to(ROOT).as_posix(),
                    "producer_phase": "Requirement Specification",
                    "source_artifacts": [],
                    "evidence": [],
                    "validation": {"status": "pending"},
                }
            ]
            errors = stage_gate.check_state(state)
            self.assertTrue(
                any("template validation" in error and "missing template section" in error for error in errors),
                errors,
            )

        state = valid_state()
        state["artifacts"] = [
            {
                "id": "bad-001",
                "type": "test_cases",
                "path": "runs/demo/verification-cases.md",
                "producer_phase": "Regression Plan",
                "source_artifacts": [],
                "evidence": [],
                "validation": {"status": "pending"},
            }
        ]
        errors = stage_gate.check_state(state)
        self.assertTrue(
            any("artifact bad-001 has invalid output path" in error for error in errors),
            errors,
        )

    def test_stage_gate_rejects_dangling_test_point_reference(self):
        with TemporaryDirectory(dir=ROOT / "outputs") as tmp:
            artifact_path = Path(tmp) / "test-points.md"
            artifact_path.write_text(
                """# 测试点

## 摘要
analysis_depth: standard
## 测试空间
## 需求覆盖
## 风险覆盖
| RISK-024 | TP-001 / TP-044 | coverage |
## 测试点列表
| ID | 测试点 | 优先级 | 维度 | 条件 | 技术 | 覆盖意图 | 依据 |
|---|---|---|---|---|---|---|---|
| TP-001 | Login | P1 | Functional | valid | Scenario | success | REQ-001 |
## 复杂度辅助分析
不适用。
## 覆盖缺口
## 可追溯关系
""",
                encoding="utf-8",
            )
            state = valid_state()
            state["artifacts"] = [
                {
                    "id": "TP-SET-001",
                    "type": "test_points",
                    "path": artifact_path.relative_to(ROOT).as_posix(),
                    "producer_phase": "Test Design",
                    "source_artifacts": [],
                    "evidence": [],
                    "validation": {"status": "pending"},
                }
            ]

            errors = stage_gate.check_state(state)

            self.assertTrue(any("TP-044 NOT FOUND" in error for error in errors), errors)

    def test_artifact_path_rejects_absolute_and_parent_escape(self):
        for path in ("/tmp/report.md", "outputs/../report.md"):
            with self.subTest(path=path):
                state = valid_state()
                state["artifacts"] = [
                    {
                        "id": "bad-path",
                        "type": "other",
                        "path": path,
                        "producer_phase": "Intake",
                        "source_artifacts": [],
                        "evidence": [],
                        "validation": {"status": "pending"},
                    }
                ]
                errors = stage_gate.check_state(state)
                self.assertTrue(any("invalid output path" in error for error in errors), errors)

    def test_regression_plan_requires_test_cases_when_supplement_path_selected(self):
        state = valid_state(
            entry="bug-regression",
            workflow="workflows/bug-regression/README.md",
            phase="Regression Plan",
            notes=[
                "regression_strategy: targeted",
                "decision_path: supplement_cases",
                "bug_surface: backend",
            ],
        )
        add_skill(state, "test-case-design", "Regression Plan")
        add_skill(state, "automation", "Regression Plan")
        add_skill(state, "reporting", "Regression Plan")
        state["artifacts"] = [
            {
                "id": "REG-PLAN-001",
                "type": "regression_plan",
                "path": "outputs/shop-platform/regression/demo-regression-plan.md",
                "producer_phase": "Regression Plan",
                "source_artifacts": [],
                "evidence": [],
                "validation": {"status": "pending"},
            }
        ]
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn(
            "phase Regression Plan requires artifact type: test_cases when decision_path is supplement_cases",
            errors,
        )

    def test_bug_intake_requires_bug_surface_note(self):
        state = valid_state(
            entry="bug-regression",
            workflow="workflows/bug-regression/README.md",
            phase="Bug Intake",
            notes=["bug_intake: ZenTao bug 1649"],
            knowledge_used=[{"path": "skills/test-case-design/references/case-writing-rules.md", "used_for": ["routing"]}],
        )
        add_skill(state, "requirement-analysis", "Bug Intake")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn("phase Bug Intake requires note prefix: bug_surface:", errors)

    def test_bug_regression_regression_report_requires_artifact(self):
        state = valid_state(
            entry="bug-regression",
            workflow="workflows/bug-regression/README.md",
            phase="Regression Report",
        )
        add_skill(state, "reporting", "Regression Report")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn("phase Regression Report requires artifact type: regression_report", errors)
        self.assertIn("phase Regression Report requires traceability links", errors)

    def test_release_baseline_requires_target_and_baseline_note(self):
        state = valid_state(
            entry="release-acceptance",
            workflow="workflows/release-acceptance/README.md",
            phase="Release Baseline",
            environment={"required_groups": ["GITLAB"], "checked_groups": ["GITLAB"], "target": ""},
        )
        add_skill(state, "release-acceptance", "Release Baseline")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn("phase Release Baseline requires environment.target", errors)
        self.assertIn("phase Release Baseline requires note prefix: release_baseline:", errors)
        self.assertIn("phase Release Baseline requires release_scope_tracks", errors)

    def test_release_baseline_accepts_release_scope_tracks(self):
        state = valid_state(
            entry="release-acceptance",
            workflow="workflows/release-acceptance/README.md",
            phase="Release Baseline",
            release_scope_tracks=["storefront", "payments"],
            notes=["release_baseline: tag=v2.8.0 env=uat"],
            knowledge_used=[{"path": "skills/test-case-design/references/case-writing-rules.md", "used_for": ["release routing"]}],
            repository_evidence=[
                {
                    "repo": "agent-next",
                    "evidence_type": "file",
                    "references": ["workflows/release-acceptance/README.md"],
                    "supports": ["release_baseline"],
                }
            ],
            repositories={
                "dev": [
                    {
                        "kind": "dev",
                        "name": "agent-next",
                        "path": ".",
                        "working_tree_state": "dirty",
                    }
                ],
                "test": [],
                "tools": [],
            },
        )
        add_skill(state, "release-acceptance", "Release Baseline")
        self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_release_acceptance_execution_accepts_data_injection_note(self):
        state = valid_state(
            entry="release-acceptance",
            workflow="workflows/release-acceptance/README.md",
            phase="Acceptance Execution",
        )
        add_skill(state, "automation", "Acceptance Execution")
        add_skill(state, "release-acceptance", "Acceptance Execution")
        state["notes"] = [
            "automation_execution_plan: API=pytest Web=playwright commands confirmed",
            "data_injection: dataset=fixture-001 generator=seed-script"
        ]
        self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_release_acceptance_execution_requires_automation_plan_or_skip(self):
        state = valid_state(
            entry="release-acceptance",
            workflow="workflows/release-acceptance/README.md",
            phase="Acceptance Execution",
            notes=["execution_evidence: manual smoke evidence only"],
        )
        add_skill(state, "automation", "Acceptance Execution")
        add_skill(state, "release-acceptance", "Acceptance Execution")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertIn(
            "phase Acceptance Execution requires note prefix: automation_execution_plan:, automation_execution_skip:",
            errors,
        )

    def test_unknown_phase_fails_in_strict_mode(self):
        state = valid_state(phase="Mystery Phase")
        errors = stage_gate.check_state(state, strict_phase=True)
        self.assertTrue(any("phase must be one of:" in error for error in errors))

    def test_phase_alias_intake_is_normalized(self):
        state = valid_state(
            phase="intake",
            knowledge_plan={"status": "not_needed", "summary": "ok", "evidence": []},
            knowledge_used=[{"path": "skills/test-case-design/references/case-writing-rules.md", "used_for": ["routing"]}],
            notes=["intake_input: feature description from user"],
        )
        add_skill(state, "requirement-analysis", "Intake")
        self.assertEqual(stage_gate.check_state(state, strict_phase=True), [])

    def test_gate_result_is_written(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = valid_state()
            path.write_text(json.dumps(state), encoding="utf-8")

            errors = stage_gate.check_state(state, strict_phase=False)
            stage_gate.write_gate_result(path, state, errors)
            data = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(data["gate_results"][0]["phase"], "Intake")
            self.assertEqual(data["gate_results"][0]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
