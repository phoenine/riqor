from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.automation_provider import (
    AutomationProviderError,
    consumer_dependency,
    load_automation_provider,
    render_install_command,
    render_prepare_arguments,
)
from tools.bootstrap import init_project
from tools.contracts import load_yaml
from tools.doctor import run_doctor


class AutomationProviderTests(unittest.TestCase):
    def test_loader_and_doctor_share_the_provider_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = init_project(
                root=root,
                project_id="iot-ops",
                name="IoT Ops",
                tracks=["default"],
                default_track="default",
                automations=["api"],
            )
            profile_path = root / result.profile_path
            profile = load_yaml(profile_path)
            binding = load_automation_provider(
                root=root, profile=profile, capability="api"
            )
            self.assertEqual(binding.repository["id"], "iot-ops-api-test")
            self.assertIn("957edc", consumer_dependency(binding))
            arguments = render_prepare_arguments(
                binding, root / "repositories/automation/iot-ops-api-test"
            )
            self.assertIn("--runtime-revision", arguments)
            self.assertNotIn("--project-profile", arguments)
            self.assertEqual(
                render_install_command(
                    binding, root / "repositories/automation/iot-ops-api-test"
                )[:2],
                ["uv", "sync"],
            )

            profile["integrations"]["custom_api"] = profile["integrations"].pop(
                "api_automation"
            )
            custom_binding = load_automation_provider(
                root=root, profile=profile, capability="api"
            )
            self.assertEqual(custom_binding.integration_id, "custom_api")

            provider_path = root / "skills/pytest-yaml-api/provider.yaml"
            provider_path.write_text(
                "schema_version: 1\ncapability: api\nprepare: {}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                AutomationProviderError, "invalid automation provider"
            ):
                load_automation_provider(root=root, profile=profile, capability="api")
            report = run_doctor(profile_path, root)
            self.assertTrue(
                any("invalid automation provider" in error for error in report.errors),
                report.errors,
            )


if __name__ == "__main__":
    unittest.main()
