from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from tools.cli import main
from tools.contracts import load_markdown_frontmatter, validate_schema
from tools.knowledge import KnowledgeError, confirm_proposals, pending_proposals
from tools.lifecycle import record_run_evidence
from tools.run_state import default_state


PROFILE = {
    "schema_version": 1,
    "project": {
        "id": "sample-project",
        "name": "Sample",
        "tracks": ["default"],
        "default_track": "default",
    },
    "knowledge": {
        "root": "knowledge/sample-project",
        "template": "standard-product",
        "index": "knowledge/sample-project/_index.md",
    },
}


def prepare_run(root: Path, *, source_status: str = "passed") -> Path:
    state = default_state("demo")
    state.update(
        {
            "project_id": "sample-project",
            "tracks": ["default"],
            "entry": "feature-quality",
            "workflow": "workflows/feature-quality/README.md",
            "phase": "Requirement Specification",
            "artifacts": [
                {
                    "id": "REQ-001",
                    "type": "requirement_spec",
                    "path": "outputs/sample/requirement-spec.md",
                    "producer_phase": "Requirement Specification",
                    "source_artifacts": [],
                    "evidence": [],
                    "validation": {"status": source_status},
                }
            ],
        }
    )
    state_path = root / "runs/demo/state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    knowledge_root = root / "knowledge/sample-project"
    knowledge_root.mkdir(parents=True)
    (knowledge_root / "_index.md").write_text(
        "---\nid: sample-index\ntitle: Sample Knowledge\ntype: index\n"
        "confidence: confirmed\n---\n\n# Sample Knowledge\n",
        encoding="utf-8",
    )
    proposal = root / "runs/demo/order-timeout.yaml"
    proposal.write_text(
        "schema_version: 1\n"
        "path: knowledge/sample-project/business-rules/order-timeout.md\n"
        "title: Order timeout\n"
        "type: business_rule\n"
        "summary: Stable order timeout rule\n"
        "content: Orders expire after the configured timeout.\n"
        "source_artifact: REQ-001\n",
        encoding="utf-8",
    )
    return proposal


def record(root: Path, proposal: Path) -> dict:
    state_path = record_run_evidence(
        root=root,
        run_id="demo",
        knowledge_used=[],
        knowledge_plan_status=None,
        knowledge_plan_summary=None,
        knowledge_plan_evidence=[],
        notes=[],
        knowledge_proposal_files=[proposal.relative_to(root)],
    )
    return json.loads(state_path.read_text(encoding="utf-8"))


class KnowledgeLifecycleTests(unittest.TestCase):
    def test_recording_proposal_does_not_write_knowledge(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal = prepare_run(root)

            state = record(root, proposal)

            target = root / "knowledge/sample-project/business-rules/order-timeout.md"
            self.assertFalse(target.exists())
            self.assertEqual(state["knowledge_plan"]["status"], "proposed")
            self.assertEqual(len(pending_proposals(state, "REQ-001")), 1)

    def test_confirm_writes_valid_page_and_updates_index_and_state(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal = prepare_run(root)
            record(root, proposal)

            written = confirm_proposals(
                root=root,
                profile=PROFILE,
                run_id="demo",
                source_artifact="REQ-001",
                confirmed_by="user",
            )

            self.assertEqual(
                written,
                [Path("knowledge/sample-project/business-rules/order-timeout.md")],
            )
            page = root / written[0]
            frontmatter = load_markdown_frontmatter(page)
            self.assertEqual(validate_schema(frontmatter, "knowledge-page"), [])
            self.assertEqual(frontmatter["confidence"], "confirmed")
            self.assertEqual(frontmatter["sources"][0]["reference"], "REQ-001")
            self.assertIn("Orders expire", page.read_text(encoding="utf-8"))
            index = (root / PROFILE["knowledge"]["index"]).read_text(encoding="utf-8")
            self.assertIn("[Order timeout](business-rules/order-timeout.md)", index)
            state = json.loads((root / "runs/demo/state.json").read_text(encoding="utf-8"))
            self.assertEqual(validate_schema(state, "run-state"), [])
            self.assertEqual(state["knowledge_plan"]["status"], "confirmed")
            self.assertEqual(state["knowledge_proposed_updates"][0]["status"], "confirmed")
            self.assertEqual(
                state["confirmations"][0]["action"],
                "confirm requirement REQ-001 and persist listed knowledge",
            )
            self.assertIn(written[0].as_posix(), state["knowledge_plan"]["evidence"])

    def test_confirmation_requires_requirement_gate_pass(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal = prepare_run(root, source_status="pending")
            record(root, proposal)

            with self.assertRaisesRegex(KnowledgeError, "has not passed"):
                confirm_proposals(
                    root=root,
                    profile=PROFILE,
                    run_id="demo",
                    source_artifact="REQ-001",
                    confirmed_by="user",
                )

            self.assertFalse(
                (root / "knowledge/sample-project/business-rules/order-timeout.md").exists()
            )

    def test_confirmation_never_overwrites_existing_knowledge(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal = prepare_run(root)
            record(root, proposal)
            target = root / "knowledge/sample-project/business-rules/order-timeout.md"
            target.parent.mkdir(parents=True)
            target.write_text("existing knowledge\n", encoding="utf-8")

            with self.assertRaisesRegex(KnowledgeError, "requires separate review"):
                confirm_proposals(
                    root=root,
                    profile=PROFILE,
                    run_id="demo",
                    source_artifact="REQ-001",
                    confirmed_by="user",
                )

            self.assertEqual(target.read_text(encoding="utf-8"), "existing knowledge\n")

    def test_proposal_must_stay_under_profile_knowledge_root(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal = prepare_run(root)
            content = proposal.read_text(encoding="utf-8").replace(
                "knowledge/sample-project/business-rules/order-timeout.md",
                "knowledge/another-project/order-timeout.md",
            )
            proposal.write_text(content, encoding="utf-8")
            record(root, proposal)

            with self.assertRaisesRegex(KnowledgeError, "must stay under"):
                confirm_proposals(
                    root=root,
                    profile=PROFILE,
                    run_id="demo",
                    source_artifact="REQ-001",
                    confirmed_by="user",
                )

    def test_cli_previews_before_explicit_confirmation(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal = prepare_run(root)
            record(root, proposal)
            profile_path = root / "project.yaml"
            profile_path.write_text(
                yaml.safe_dump(PROFILE, sort_keys=False), encoding="utf-8"
            )

            preview = StringIO()
            with redirect_stdout(preview):
                preview_status = main(
                    [
                        "knowledge",
                        "--root",
                        str(root),
                        "--project",
                        "project.yaml",
                        "--run-id",
                        "demo",
                        "--source-artifact",
                        "REQ-001",
                    ]
                )
            self.assertEqual(preview_status, 0)
            self.assertIn("PROPOSED knowledge/sample-project", preview.getvalue())
            self.assertFalse(
                (root / "knowledge/sample-project/business-rules/order-timeout.md").exists()
            )

            confirmed = StringIO()
            with redirect_stdout(confirmed):
                confirm_status = main(
                    [
                        "knowledge",
                        "--root",
                        str(root),
                        "--project",
                        "project.yaml",
                        "--run-id",
                        "demo",
                        "--source-artifact",
                        "REQ-001",
                        "--confirm",
                    ]
                )
            self.assertEqual(confirm_status, 0)
            self.assertIn("OK confirmed knowledge", confirmed.getvalue())


if __name__ == "__main__":
    unittest.main()
