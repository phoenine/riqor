import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import load_tool

migrate_run_state = load_tool("migrate_run_state")
run_state = load_tool("run_state")


def legacy_state(*, workflow: str = "workflows/feature-quality.md"):
    state = run_state.default_state("demo")
    del state["schema_version"]
    state.update(
        {
            "product_line": "v2",
            "entry": "feature-quality",
            "workflow": workflow,
            "phase": "Intake",
        }
    )
    return state


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MigrateRunStateTests(unittest.TestCase):
    def test_dry_run_is_read_only_and_normalizes_safe_fields(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps(legacy_state()), encoding="utf-8")
            before = file_hash(path)

            report, candidate = migrate_run_state.audit_state(path)

            self.assertEqual(report["status"], "ready")
            self.assertEqual(candidate["schema_version"], 2)
            self.assertEqual(candidate["workflow"], "workflows/feature-quality/README.md")
            self.assertEqual(file_hash(path), before)
            self.assertTrue(report["post_migration_validation_errors"])

    def test_unrecognized_structural_error_blocks_migration(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = legacy_state()
            state["repository_evidence"] = [
                {
                    "repo": "demo",
                    "evidence_type": "search",
                    "references": ["query"],
                    "supports": [],
                }
            ]
            path.write_text(json.dumps(state), encoding="utf-8")

            report, _candidate = migrate_run_state.audit_state(path)

            self.assertEqual(report["status"], "blocked")
            self.assertTrue(any("evidence_type" in error for error in report["blockers"]))

    def test_write_creates_backup_and_migrates_one_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            original = json.dumps(legacy_state(), ensure_ascii=False, indent=2) + "\n"
            path.write_text(original, encoding="utf-8")
            report, candidate = migrate_run_state.audit_state(path)
            self.assertEqual(report["status"], "ready")

            backup = migrate_run_state.write_candidate(
                path,
                candidate,
                report["detected_version"],
            )

            self.assertTrue(backup.is_file())
            self.assertEqual(backup.read_text(encoding="utf-8"), original)
            migrated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["schema_version"], 2)
            self.assertEqual(migrated["workflow"], "workflows/feature-quality/README.md")

    def test_absolute_skill_path_only_rewrites_when_hash_matches(self):
        state = legacy_state(workflow="workflows/feature-quality/README.md")
        skill_path = migrate_run_state.AGENT_NEXT_ROOT / "skills/agent-next/SKILL.md"
        state["skill_receipts"] = [
            {
                "skill": "agent-next",
                "path": "/legacy/profile/skills/agent-next/SKILL.md",
                "sha256": migrate_run_state.sha256_file(skill_path),
                "supports_phase": "Intake",
            }
        ]
        candidate, actions, blockers = migrate_run_state.build_candidate(state)

        self.assertEqual(blockers, [])
        self.assertEqual(candidate["skill_receipts"][0]["path"], "skills/agent-next/SKILL.md")
        self.assertTrue(any(action["field"] == "skill_receipts[0].path" for action in actions))


if __name__ == "__main__":
    unittest.main()
