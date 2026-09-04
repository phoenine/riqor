from __future__ import annotations

import re
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import yaml

from tools.artifacts import ArtifactActionError, gate_artifact, scaffold_artifact
from tools.contracts import load_yaml
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


def prepare_root(root: Path) -> None:
    shutil.copytree(ROOT / "templates", root / "templates")
    shutil.copytree(ROOT / "workflows", root / "workflows")
    shutil.copytree(ROOT / "skills", root / "skills")


def write_ready(
    root: Path,
    artifact_id: str,
    artifact_type: str,
    scope: str,
    revision: int = 1,
) -> str:
    directory = root / "outputs/sample-project" / scope / artifact_type
    directory.mkdir(parents=True, exist_ok=True)
    content_path = directory / f"{artifact_id}.md"
    content_path.write_text(f"# {artifact_id}\n\nReady input.\n", encoding="utf-8")
    relative_content = content_path.relative_to(root).as_posix()
    metadata = {
        "schema_version": 1,
        "id": artifact_id,
        "type": artifact_type,
        "project_id": "sample-project",
        "scope_id": scope,
        "tracks": ["backend"],
        "status": "ready",
        "revision": revision,
        "content_path": relative_content,
        "source_artifacts": [],
        "evidence": [],
        "validation": {"status": "passed"},
    }
    manifest = root / "runs" / f"source-{artifact_id}" / "artifacts" / f"{artifact_id}.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(metadata), encoding="utf-8")
    return f"{artifact_id}@{revision}"


def complete_sections(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    content = re.sub(r"<[^>\n]+>", "completed", content)
    content = content.replace("TBD", "completed").replace("XXX", "001")
    if "# 需求说明书" in content:
        content = content.replace(
            "**依据类型**：completed", "**依据类型**：source_explicit"
        ).replace("**确认状态**：completed", "**确认状态**：confirmed")
    if "# 风险分析" in content:
        content = content.replace(
            "**Risk Type**：completed", "**Risk Type**：functional"
        ).replace("**状态**：completed", "**状态**：pending_validation").replace(
            "**等级**：completed", "**等级**：P2"
        )
    path.write_text(content + "\nCompleted artifact content.\n", encoding="utf-8")


class ArtifactLifecycleTests(unittest.TestCase):
    def test_scaffold_rolls_back_when_run_registration_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-001", "prd", "checkout")
            (root / "runs/demo").mkdir(parents=True)
            (root / "runs/demo/state.json").write_text(
                '{"schema_version": 3, "run_id": "demo"}\n', encoding="utf-8"
            )
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            with patch("tools.artifacts.register_artifact", return_value=False):
                with self.assertRaisesRegex(ArtifactActionError, "run state does not exist"):
                    scaffold_artifact(
                        root=root,
                        profile=PROFILE,
                        capability=capability,
                        scope_id="checkout",
                        artifact_id="REQ-001",
                        source_references=[source],
                        tracks=["backend"],
                        run_id="demo",
                    )
            output = root / "outputs/sample-project/checkout/requirement_spec"
            self.assertFalse((output / "REQ-001.md").exists())
            self.assertFalse((output / "REQ-001.artifact.yaml").exists())

    def test_gate_rejects_a_different_run_than_the_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-001", "prd", "checkout")
            (root / "runs/demo").mkdir(parents=True)
            (root / "runs/demo/state.json").write_text(
                '{"schema_version": 3, "run_id": "demo"}\n', encoding="utf-8"
            )
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            scaffold = scaffold_artifact(
                root=root,
                profile=PROFILE,
                capability=capability,
                scope_id="checkout",
                artifact_id="REQ-001",
                source_references=[source],
                tracks=["backend"],
                run_id="demo",
            )
            complete_sections(root / scaffold.content_path)
            result = gate_artifact(
                root=root, profile=PROFILE, artifact_id="REQ-001", run_id="other-run"
            )
            self.assertFalse(result.passed)
            self.assertIn("artifact belongs to run demo, not other-run", result.errors)

    def test_gate_records_passed_phase_only_when_marking_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-001", "prd", "checkout")
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            state_path = root / "runs/demo/state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text('{"run_id": "demo", "schema_version": 3}\n', encoding="utf-8")
            result = scaffold_artifact(
                root=root,
                profile=PROFILE,
                capability=capability,
                scope_id="checkout",
                artifact_id="REQ-001",
                source_references=[source],
                tracks=["backend"],
                run_id="demo",
            )
            complete_sections(root / result.content_path)
            state_path.write_text(
                '{"schema_version": 3, "run_id": "demo", '
                f'"artifacts": [{{"id": "REQ-001", "path": "{result.content_path}"}}]}}\n',
                encoding="utf-8",
            )
            with (
                patch("tools.artifacts.check_state", return_value=[]),
                patch("tools.artifacts.write_gate_result") as write_result,
            ):
                checked = gate_artifact(
                    root=root, profile=PROFILE, artifact_id="REQ-001", run_id="demo"
                )
                self.assertTrue(checked.passed)
                write_result.assert_not_called()
                ready = gate_artifact(
                    root=root,
                    profile=PROFILE,
                    artifact_id="REQ-001",
                    mark_ready=True,
                    run_id="demo",
                )
                self.assertTrue(ready.passed)
                write_result.assert_called_once()

    def test_scaffold_gate_and_mark_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-001", "prd", "checkout")
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            result = scaffold_artifact(
                root=root,
                profile=PROFILE,
                capability=capability,
                scope_id="checkout",
                artifact_id="REQ-001",
                source_references=[source],
                tracks=["backend"],
            )
            self.assertEqual(
                result.content_path,
                Path("outputs/sample-project/features/checkout/requirement-spec.md"),
            )
            self.assertEqual(
                result.manifest_path,
                Path("runs/inventory-only/artifacts/REQ-001.json"),
            )
            manifest = load_yaml(root / result.manifest_path)
            self.assertEqual(manifest["status"], "draft")
            content_path = root / result.content_path
            self.assertFalse(content_path.read_text(encoding="utf-8").startswith("---"))
            original = content_path.read_text(encoding="utf-8")
            content_path.write_text(original.replace("# 需求说明书", "# Draft"), encoding="utf-8")
            blocked = gate_artifact(root=root, profile=PROFILE, artifact_id="REQ-001")
            self.assertFalse(blocked.passed)
            self.assertTrue(any("missing template section" in error for error in blocked.errors))
            content_path.write_text(original, encoding="utf-8")
            complete_sections(content_path)
            passed = gate_artifact(
                root=root, profile=PROFILE, artifact_id="REQ-001", mark_ready=True
            )
            self.assertTrue(passed.passed)
            self.assertTrue(passed.marked_ready)
            ready = load_yaml(root / result.manifest_path)
            self.assertEqual(ready["status"], "ready")
            self.assertEqual(ready["validation"]["status"], "passed")
            self.assertRegex(ready["content_sha256"], r"^[a-f0-9]{64}$")

    def test_untouched_scaffold_cannot_be_marked_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-001", "prd", "checkout")
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            scaffold_artifact(
                root=root,
                profile=PROFILE,
                capability=capability,
                scope_id="checkout",
                artifact_id="REQ-001",
                source_references=[source],
                tracks=["backend"],
            )

            result = gate_artifact(
                root=root, profile=PROFILE, artifact_id="REQ-001", mark_ready=True
            )

            self.assertFalse(result.passed)
            self.assertTrue(any("untouched managed template" in error for error in result.errors))

    def test_scaffold_requires_declared_input_types(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            with self.assertRaisesRegex(ArtifactActionError, "missing required source types"):
                scaffold_artifact(
                    root=root,
                    profile=PROFILE,
                    capability=capability,
                    scope_id="checkout",
                    artifact_id="REQ-001",
                    source_references=[],
                    tracks=["backend"],
                )

    def test_feature_scaffold_rejects_cross_scope_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-OTHER", "prd", "other")
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            with self.assertRaisesRegex(ArtifactActionError, "cross-scope"):
                scaffold_artifact(
                    root=root,
                    profile=PROFILE,
                    capability=capability,
                    scope_id="checkout",
                    artifact_id="REQ-001",
                    source_references=[source],
                    tracks=["backend"],
                )

    def test_release_capability_allows_explicit_cross_scope_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "SCOPE-001", "release_scope", "release-sources")
            capability = next(
                item
                for item in load_capabilities(root, "release-acceptance").records
                if item.capability_id == "release-acceptance-plan"
            )
            result = scaffold_artifact(
                root=root,
                profile=PROFILE,
                capability=capability,
                scope_id="release-1.0",
                artifact_id="PLAN-001",
                source_references=[source],
                tracks=["backend"],
            )
            self.assertTrue((root / result.manifest_path).is_file())

    def test_gate_blocks_when_source_revision_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-001", "prd", "checkout")
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            result = scaffold_artifact(
                root=root,
                profile=PROFILE,
                capability=capability,
                scope_id="checkout",
                artifact_id="REQ-001",
                source_references=[source],
                tracks=["backend"],
            )
            complete_sections(root / result.content_path)
            prd_manifest = root / "runs/source-PRD-001/artifacts/PRD-001.json"
            prd = json.loads(prd_manifest.read_text(encoding="utf-8"))
            prd["revision"] = 2
            prd_manifest.write_text(json.dumps(prd), encoding="utf-8")

            gated = gate_artifact(root=root, profile=PROFILE, artifact_id="REQ-001")
            self.assertFalse(gated.passed)
            self.assertIn(
                "source artifact is missing or revision changed: PRD-001@1",
                gated.errors,
            )

    def test_gate_blocks_when_content_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare_root(root)
            source = write_ready(root, "PRD-001", "prd", "checkout")
            capability = next(
                item
                for item in load_capabilities(root, "feature-quality").records
                if item.capability_id == "requirement-specification"
            )
            result = scaffold_artifact(
                root=root,
                profile=PROFILE,
                capability=capability,
                scope_id="checkout",
                artifact_id="REQ-001",
                source_references=[source],
                tracks=["backend"],
            )
            (root / result.content_path).unlink()

            gated = gate_artifact(root=root, profile=PROFILE, artifact_id="REQ-001")

            self.assertFalse(gated.passed)
            self.assertIn(
                f"artifact content does not exist: {result.content_path}", gated.errors
            )


if __name__ == "__main__":
    unittest.main()
