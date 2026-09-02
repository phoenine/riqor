from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from tools import contracts, inventory, registration
from tools.artifacts import gate_artifact


class RegistrationTests(unittest.TestCase):
    def _profile(self) -> dict:
        return contracts.load_yaml(ROOT / "examples/shop-platform/project.yaml")

    def test_registers_existing_file_as_ready_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = root / "docs" / "release-baseline.md"
            content.parent.mkdir()
            content.write_text("# Release baseline\n", encoding="utf-8")
            profile = self._profile()

            result = registration.register_existing_artifact(
                root=root,
                profile=profile,
                artifact_id="BASELINE-checkout-001",
                artifact_type="release_baseline",
                scope_id="checkout-release",
                content_path=Path("docs/release-baseline.md"),
                tracks=["web", "backend"],
                ready=True,
            )

            self.assertEqual(
                result.manifest_path,
                Path("runs/import-shop-platform/artifacts/BASELINE-checkout-001.json"),
            )
            report = inventory.load_inventory(root, profile)
            self.assertTrue(report.ok)
            self.assertEqual(report.records[0].artifact_type, "release_baseline")
            self.assertEqual(report.records[0].effective_status, "ready")
            self.assertRegex(
                report.records[0].metadata["content_sha256"], r"^[a-f0-9]{64}$"
            )

    def test_draft_external_input_can_be_marked_ready_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = root / "docs" / "release-baseline.md"
            content.parent.mkdir()
            content.write_text("# Release baseline\n", encoding="utf-8")
            profile = self._profile()
            registration.register_existing_artifact(
                root=root,
                profile=profile,
                artifact_id="BASELINE-checkout-001",
                artifact_type="release_baseline",
                scope_id="checkout-release",
                content_path=Path("docs/release-baseline.md"),
                tracks=["web", "backend"],
            )

            result = gate_artifact(
                root=root,
                profile=profile,
                artifact_id="BASELINE-checkout-001",
                mark_ready=True,
            )

            self.assertTrue(result.passed)
            self.assertTrue(result.marked_ready)
            self.assertEqual(
                inventory.load_inventory(root, profile).records[0].effective_status,
                "ready",
            )

    def test_rejects_content_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            content = Path(outside) / "baseline.md"
            content.write_text("# Release baseline\n", encoding="utf-8")

            with self.assertRaisesRegex(registration.RegistrationError, "inside the repository"):
                registration.register_existing_artifact(
                    root=root,
                    profile=self._profile(),
                    artifact_id="BASELINE-checkout-001",
                    artifact_type="release_baseline",
                    scope_id="checkout-release",
                    content_path=content,
                    tracks=["backend"],
                )
