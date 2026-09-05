from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.cli import main
from tools.run_state import default_state


class RecordCommandTests(unittest.TestCase):
    def test_records_stage_gate_evidence_through_unified_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_path = root / "runs/evidence-run/state.json"
            state_path.parent.mkdir(parents=True)
            state = default_state("evidence-run")
            state.update(
                {
                    "project_id": "sample-project",
                    "tracks": ["backend"],
                    "entry": "feature-quality",
                    "workflow": "workflows/feature-quality/README.md",
                    "phase": "Risk Analysis",
                }
            )
            state_path.write_text(
                json.dumps(state), encoding="utf-8"
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "record",
                        "--root",
                        str(root),
                        "--run-id",
                        "evidence-run",
                        "--repository",
                        "kind=dev,name=app,path=repositories/product/app,commit=abc123",
                        "--repository-evidence",
                        "repo=app,evidence_type=commit,reference=abc123,supports=REQ-001",
                        "--required-env",
                        "api",
                        "--checked-env",
                        "api",
                        "--target",
                        "staging",
                        "--confirmation",
                        "id=CONF-001,action=shared_environment_execution,status=confirmed",
                        "--trace",
                        "from=REQ-001,to=TC-001,relation=verified_by",
                    ]
                )
            self.assertEqual(status, 0, output.getvalue())
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["repositories"]["dev"][0]["name"], "app")
            self.assertEqual(state["repository_evidence"][0]["repo"], "app")
            self.assertEqual(state["environment"]["target"], "staging")
            self.assertEqual(state["environment"]["checked_groups"], ["api"])
            self.assertEqual(state["confirmations"][0]["status"], "confirmed")
            self.assertEqual(state["traceability"][0]["relation"], "verified_by")


if __name__ == "__main__":
    unittest.main()
