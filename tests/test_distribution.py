from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def test_runtime_resources_are_declared_for_wheel(self) -> None:
        configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        setuptools = configuration["tool"]["setuptools"]
        self.assertTrue(
            {"config*", "schemas*", "skills*", "templates*", "workflows*"}.issubset(
                setuptools["packages"]["find"]["include"]
            )
        )
        for package in ("config", "schemas", "skills", "templates", "workflows"):
            self.assertIn(package, setuptools["package-data"])

    def test_wheel_can_initialize_and_doctor_a_fresh_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            distribution = temporary_root / "dist"
            distribution.mkdir()
            uv = shutil.which("uv")
            if uv is None:
                self.skipTest("uv is required for the wheel smoke test")
            build_environment = os.environ.copy()
            build_environment["UV_CACHE_DIR"] = str(temporary_root / "uv-cache")
            build = subprocess.run(
                [
                    uv,
                    "build",
                    "--wheel",
                    "--out-dir",
                    str(distribution),
                ],
                cwd=ROOT,
                env=build_environment,
                check=False,
                capture_output=True,
                text=True,
            )
            if build.returncode != 0 and any(
                marker in build.stdout + build.stderr
                for marker in ("Failed to fetch", "dns error", "network")
            ):
                self.skipTest("wheel build dependencies are unavailable offline")
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            wheels = list(distribution.glob("*.whl"))
            self.assertEqual(len(wheels), 1)
            wheel = wheels[0]
            installed = temporary_root / "installed"
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
                self.assertIn("schemas/project-profile.schema.json", names)
                self.assertIn("templates/artifacts/requirement-spec.md.tmpl", names)
                self.assertIn("workflows/feature-quality/README.md", names)
                self.assertIn("skills/pytest-yaml-api/provider.yaml", names)
                self.assertIn("config/automation-presets.yaml", names)
                archive.extractall(installed)

            workspace = temporary_root / "workspace"
            workspace.mkdir()
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(installed)
            init = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.agent_next",
                    "init",
                    "--root",
                    str(workspace),
                    "--project-id",
                    "wheel-smoke",
                    "--name",
                    "Wheel Smoke",
                    "--automation",
                    "api",
                ],
                cwd=workspace,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            doctor = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.agent_next",
                    "doctor",
                    "--root",
                    str(workspace),
                    "--project",
                    "config/projects/wheel-smoke.yaml",
                ],
                cwd=workspace,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            self.assertIn("OK capabilities 18", doctor.stdout)


if __name__ == "__main__":
    unittest.main()
