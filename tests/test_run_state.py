import json
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from helpers import load_tool

run_state = load_tool("run_state")


class RunStateTests(unittest.TestCase):
    def test_records_each_gate_result_argument(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="demo",
                runs_root=Path(tmp),
                project_id=None,
                track=[],
                product_line=None,
                release_scope_track=[],
                entry=None,
                workflow=None,
                phase=None,
                required_skill=[],
                loaded_skill=[],
                skill_receipt=[],
                required_env=[],
                checked_env=[],
                target=None,
                repository=[],
                repository_evidence=[],
                knowledge_used=[],
                knowledge_plan_status=None,
                knowledge_plan_summary=None,
                knowledge_plan_evidence=[],
                knowledge_plan_confirmed_by=None,
                knowledge_plan_confirmed_at=None,
                knowledge_proposed_update=[],
                confirmation=[],
                trace=[],
                gate_result=[
                    '{"phase":"Intake","status":"passed","checks":[]}',
                    '{"phase":"Requirement Specification","status":"failed","checks":[]}',
                ],
                note=[],
            )

            data = json.loads(run_state.update_state(args).read_text(encoding="utf-8"))

            self.assertEqual(
                [item["phase"] for item in data["gate_results"]],
                ["Intake", "Requirement Specification"],
            )

    def test_create_generic_project_track_state(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="generic-demo",
                runs_root=Path(tmp),
                project_id="shop-platform",
                track=["storefront", "api"],
                product_line=None,
                entry="feature-quality",
                workflow=None,
                phase="Intake",
                required_skill=[],
                loaded_skill=[],
                skill_receipt=[],
                required_env=[],
                checked_env=[],
                target=None,
                repository=[],
                repository_evidence=[],
                knowledge_used=[],
                knowledge_plan_status=None,
                knowledge_plan_summary=None,
                knowledge_plan_evidence=[],
                knowledge_plan_confirmed_by=None,
                knowledge_plan_confirmed_at=None,
                knowledge_proposed_update=[],
                confirmation=[],
                trace=[],
                gate_result=[],
                note=[],
            )

            data = json.loads(run_state.update_state(args).read_text(encoding="utf-8"))

            self.assertEqual(data["project_id"], "shop-platform")
            self.assertEqual(data["tracks"], ["storefront", "api"])
            self.assertEqual(data["product_line"], "")

    def test_create_minimal_state(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="demo",
                runs_root=Path(tmp),
                product_line="v2",
                entry="feature-quality",
                workflow="workflows/feature-quality/README.md",
                phase="Intake",
                required_skill=["agent-next", "requirement-analysis"],
                loaded_skill=["agent-next", "requirement-analysis"],
                skill_receipt=[
                    "agent-next=skills/agent-next/SKILL.md",
                    "requirement-analysis=skills/requirement-analysis/SKILL.md",
                ],
                required_env=["ZENTAO"],
                checked_env=["ZENTAO"],
                target="test",
            )

            path = run_state.update_state(args)
            data = json.loads(path.read_text())

            self.assertEqual(data["schema_version"], 2)
            self.assertEqual(data["run_id"], "demo")
            self.assertEqual(data["product_line"], "v2")
            self.assertEqual(data["entry"], "feature-quality")
            self.assertEqual(data["required_skills"], ["agent-next", "requirement-analysis"])
            self.assertEqual(data["loaded_skills"], ["agent-next", "requirement-analysis"])
            self.assertEqual(data["skill_receipts"][0]["skill"], "agent-next")
            self.assertEqual(
                data["skill_receipts"][0]["path"],
                "skills/agent-next/SKILL.md",
            )
            self.assertEqual(len(data["skill_receipts"][0]["sha256"]), 64)
            self.assertEqual(data["knowledge_plan"]["status"], "pending")
            self.assertEqual(data["environment"]["required_groups"], ["ZENTAO"])
            self.assertEqual(data["environment"]["checked_groups"], ["ZENTAO"])

    def test_legacy_state_requires_explicit_migration(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = run_state.default_state("demo")
            del state["schema_version"]
            path.write_text(json.dumps(state), encoding="utf-8")
            before = path.read_bytes()

            with self.assertRaisesRegex(ValueError, "migrate_run_state.py"):
                run_state.load_state(path, "demo")

            self.assertEqual(path.read_bytes(), before)

    def test_entry_sets_default_workflow_readme_when_missing(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="demo",
                runs_root=Path(tmp),
                product_line="v2",
                entry="bug-regression",
                workflow=None,
                phase="Bug Intake",
                required_skill=[],
                loaded_skill=[],
                skill_receipt=[],
                required_env=[],
                checked_env=[],
                target=None,
                repository=[],
                repository_evidence=[],
                knowledge_used=[],
                knowledge_plan_status=None,
                knowledge_plan_summary=None,
                knowledge_plan_evidence=[],
                knowledge_plan_confirmed_by=None,
                knowledge_plan_confirmed_at=None,
                knowledge_proposed_update=[],
                confirmation=[],
                trace=[],
                gate_result=[],
                note=[],
            )

            path = run_state.update_state(args)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["workflow"], "workflows/bug-regression/README.md")

    def test_records_release_scope_tracks(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="release-demo",
                runs_root=Path(tmp),
                product_line="v2",
                release_scope_track=["v1", "v2", "shared"],
                entry="release-acceptance",
                workflow="workflows/release-acceptance/README.md",
                phase="Release Baseline",
                required_skill=[],
                loaded_skill=[],
                skill_receipt=[],
                required_env=[],
                checked_env=[],
                target=None,
                repository=[],
                repository_evidence=[],
                knowledge_used=[],
                knowledge_plan_status=None,
                knowledge_plan_summary=None,
                knowledge_plan_evidence=[],
                knowledge_plan_confirmed_by=None,
                knowledge_plan_confirmed_at=None,
                knowledge_proposed_update=[],
                confirmation=[],
                trace=[],
                gate_result=[],
                note=[],
            )

            path = run_state.update_state(args)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["release_scope_tracks"], ["v1", "v2", "shared"])

    def test_normalizes_phase_alias_on_write(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="demo",
                runs_root=Path(tmp),
                product_line="v2",
                entry="feature-quality",
                workflow="workflows/feature-quality/README.md",
                phase="intake",
                required_skill=[],
                loaded_skill=[],
                skill_receipt=[],
                required_env=[],
                checked_env=[],
                target=None,
                repository=[],
                repository_evidence=[],
                knowledge_used=[],
                knowledge_plan_status=None,
                knowledge_plan_summary=None,
                knowledge_plan_evidence=[],
                knowledge_plan_confirmed_by=None,
                knowledge_plan_confirmed_at=None,
                knowledge_proposed_update=[],
                confirmation=[],
                trace=[],
                gate_result=[],
                note=[],
            )

            path = run_state.update_state(args)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["phase"], "Intake")

    def test_records_evidence_and_traceability(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="demo",
                runs_root=Path(tmp),
                product_line="v2",
                entry="feature-quality",
                workflow="workflows/feature-quality/README.md",
                phase="Risk Analysis",
                required_skill=[],
                loaded_skill=[],
                skill_receipt=[],
                required_env=[],
                checked_env=[],
                target=None,
                repository=["kind=dev,name=newepvs-demo,path=repositories/dev/newepvs-demo,commit=abc123"],
                repository_evidence=["repo=newepvs-demo,evidence_type=file,reference=src/App.tsx,supports=RISK-001"],
                knowledge_used=["path=skills/test-case-design/references/case-writing-rules.md,purpose=术语确认"],
                knowledge_plan_status="not-needed",
                knowledge_plan_summary="未发现需要补充的领域术语。",
                knowledge_plan_evidence=["skills/test-case-design/references/case-writing-rules.md"],
                knowledge_plan_confirmed_by=None,
                knowledge_plan_confirmed_at=None,
                knowledge_proposed_update=[],
                confirmation=["id=c1,action=run automation,status=not_required"],
                trace=["from=REQ-001,to=RISK-001,relation=drives"],
                gate_result=[],
                note=["knowledge_not_applicable: none"],
            )

            path = run_state.update_state(args)
            data = json.loads(path.read_text())

            self.assertEqual(data["repositories"]["dev"][0]["name"], "newepvs-demo")
            self.assertEqual(data["repository_evidence"][0]["references"], ["src/App.tsx"])
            self.assertEqual(data["knowledge_used"][0]["used_for"], ["术语确认"])
            self.assertEqual(data["knowledge_plan"]["status"], "not_needed")
            self.assertEqual(data["knowledge_plan"]["summary"], "未发现需要补充的领域术语。")
            self.assertEqual(data["knowledge_plan"]["evidence"], ["skills/test-case-design/references/case-writing-rules.md"])
            self.assertEqual(data["confirmations"][0]["status"], "not_required")
            self.assertEqual(data["traceability"][0]["relation"], "drives")

    def test_records_knowledge_proposed_update(self):
        with TemporaryDirectory() as tmp:
            args = Namespace(
                run_id="demo",
                runs_root=Path(tmp),
                product_line=None,
                entry=None,
                workflow=None,
                phase=None,
                required_skill=[],
                loaded_skill=[],
                skill_receipt=[],
                required_env=[],
                checked_env=[],
                target=None,
                repository=[],
                repository_evidence=[],
                knowledge_used=[],
                knowledge_plan_status="proposed",
                knowledge_plan_summary="发现一个新增术语需要确认。",
                knowledge_plan_evidence=[],
                knowledge_plan_confirmed_by=None,
                knowledge_plan_confirmed_at=None,
                knowledge_proposed_update=[
                    "path=knowledge/epvs/01-术语定义/new-term.md,summary=新增术语,status=proposed"
                ],
                confirmation=[],
                trace=[],
                gate_result=[],
                note=[],
            )

            path = run_state.update_state(args)
            data = json.loads(path.read_text())

            self.assertEqual(data["knowledge_plan"]["status"], "proposed")
            self.assertEqual(data["knowledge_proposed_updates"][0]["summary"], "新增术语")


if __name__ == "__main__":
    unittest.main()
