from __future__ import annotations

import unittest
from copy import deepcopy

from tools.contracts import (
    validate_artifact,
    validate_capability,
    validate_project_profile,
    validate_schema,
)


VALID_PROFILE = {
    "schema_version": 1,
    "project": {
        "id": "sample-project",
        "name": "Sample Project",
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


class ProjectProfileTests(unittest.TestCase):
    def test_valid_profile_passes(self) -> None:
        self.assertEqual(validate_project_profile(VALID_PROFILE), [])

    def test_unknown_core_field_fails(self) -> None:
        profile = deepcopy(VALID_PROFILE)
        profile["internal_product_code"] = "legacy"
        errors = validate_project_profile(profile)
        self.assertTrue(any("Additional properties" in error for error in errors))

    def test_default_track_must_be_declared(self) -> None:
        profile = deepcopy(VALID_PROFILE)
        profile["project"]["default_track"] = "mobile"
        self.assertIn(
            "project.default_track: must be listed in project.tracks",
            validate_project_profile(profile),
        )

    def test_knowledge_index_must_be_under_root(self) -> None:
        profile = deepcopy(VALID_PROFILE)
        profile["knowledge"]["index"] = "knowledge/other/_index.md"
        self.assertIn(
            "knowledge.index: must be located under knowledge.root",
            validate_project_profile(profile),
        )

    def test_artifact_root_must_be_repository_relative(self) -> None:
        profile = deepcopy(VALID_PROFILE)
        profile["artifacts"]["root"] = "../outside"
        self.assertIn(
            "artifacts.root: must be a safe repository-relative path",
            validate_project_profile(profile),
        )

    def test_skill_first_integration_passes_without_adapter(self) -> None:
        profile = deepcopy(VALID_PROFILE)
        profile["integrations"] = {
            "test_management": {"skill": "zentao-sync", "config": {"product_id": 11}}
        }
        self.assertEqual(validate_project_profile(profile), [])

    def test_integration_requires_skill_or_adapter(self) -> None:
        profile = deepcopy(VALID_PROFILE)
        profile["integrations"] = {"test_management": {"config": {}}}
        errors = validate_project_profile(profile)
        self.assertTrue(any("not valid under any of the given schemas" in error for error in errors))


class CapabilityTests(unittest.TestCase):
    def test_local_generation_capability_passes(self) -> None:
        capability = {
            "schema_version": 1,
            "id": "test-case-design",
            "title": "Test case design",
            "workflow": "feature-quality",
            "phase": "Test Design",
            "skill": "test-case-design",
            "requires": {"all": ["requirement_spec", "risk_analysis"]},
            "optional": ["test_points"],
            "produces": ["test_cases"],
            "side_effect": False,
            "action_class": "local_write",
        }
        self.assertEqual(validate_capability(capability), [])

    def test_remote_action_requires_side_effect_flag(self) -> None:
        capability = {
            "schema_version": 1,
            "id": "case-sync",
            "title": "Case sync",
            "workflow": "feature-quality",
            "phase": "Optional Case Sync Or Generation",
            "skill": "zentao-sync",
            "produces": ["sync_record"],
            "side_effect": False,
            "action_class": "remote_write",
        }
        self.assertIn(
            "side_effect: must be true for remote or shared actions",
            validate_capability(capability),
        )

    def test_output_cannot_also_be_input(self) -> None:
        capability = {
            "schema_version": 1,
            "id": "invalid-loop",
            "title": "Invalid loop",
            "workflow": "feature-quality",
            "phase": "Test Design",
            "skill": "test-case-design",
            "requires": {"all": ["test_cases"]},
            "produces": ["test_cases"],
            "side_effect": False,
            "action_class": "local_write",
        }
        errors = validate_capability(capability)
        self.assertTrue(any("cannot also be declared as an input" in error for error in errors))


class ArtifactTests(unittest.TestCase):
    def test_artifact_metadata_contract(self) -> None:
        artifact = {
            "schema_version": 1,
            "id": "TC-checkout-001",
            "type": "test_cases",
            "project_id": "shop-platform",
            "scope_id": "checkout",
            "tracks": ["web"],
            "status": "ready",
            "revision": 1,
            "content_path": "outputs/shop-platform/checkout/TC-checkout-001.md",
            "source_artifacts": ["REQ-checkout-001@2"],
            "evidence": [
                {"type": "document", "reference": "docs/checkout-prd.md"}
            ],
            "validation": {"status": "passed"},
        }
        self.assertEqual(validate_schema(artifact, "artifact"), [])

    def test_ready_artifact_requires_passed_validation(self) -> None:
        artifact = {
            "schema_version": 1,
            "id": "REQ-checkout-001",
            "type": "requirement_spec",
            "project_id": "shop-platform",
            "scope_id": "checkout",
            "tracks": ["backend"],
            "status": "ready",
            "revision": 1,
            "content_path": "outputs/shop-platform/checkout/REQ-checkout-001.md",
            "source_artifacts": [],
            "evidence": [],
            "validation": {"status": "pending"},
        }
        self.assertIn(
            "validation.status: a ready artifact must have passed validation",
            validate_artifact(artifact),
        )


if __name__ == "__main__":
    unittest.main()
