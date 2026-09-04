from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ELIGIBLE_ROW = re.compile(
    r"^\|\s*(TC-\d+)\s*\|\s*(A0|A1)\s*\|\s*(api|hybrid)\s*\|",
    re.MULTILINE,
)
MOVING_REVISIONS = {"main", "master", "HEAD"}


class AutomationPrepareError(ValueError):
    """Raised when automation preparation cannot proceed safely."""


@dataclass(frozen=True)
class AutomationPrepareResult:
    status: str
    destination: Path | None
    eligible_cases: tuple[str, ...]


def _select_api_repository(profile: dict[str, Any], repository_id: str | None) -> dict[str, Any]:
    candidates = [
        item
        for item in profile.get("repositories", {}).get("automation", [])
        if "api" in item.get("capabilities", [])
        and (repository_id is None or item.get("id") == repository_id)
    ]
    if len(candidates) != 1:
        raise AutomationPrepareError("select exactly one API automation repository")
    return candidates[0]


def _load_provider(root: Path, profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    integration = profile.get("integrations", {}).get("api_automation")
    if not isinstance(integration, dict) or not integration.get("skill"):
        raise AutomationPrepareError("integrations.api_automation.skill is required")
    skill = str(integration["skill"])
    if "/" in skill or ".." in skill:
        raise AutomationPrepareError("automation skill name is unsafe")
    provider_path = root / "skills" / skill / "provider.yaml"
    try:
        provider = yaml.safe_load(provider_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AutomationPrepareError(f"cannot load automation provider {provider_path}: {exc}") from exc
    if not isinstance(provider, dict) or provider.get("capability") != "api":
        raise AutomationPrepareError(f"automation provider {skill} does not declare api capability")
    return integration, provider


def _render_command(parts: list[Any], destination: Path) -> list[str]:
    return [str(part).replace("{destination}", str(destination)) for part in parts]


def prepare_api_automation(
    *,
    root: Path,
    profile_path: Path,
    profile: dict[str, Any],
    classification_path: Path,
    repository_id: str | None = None,
    install: bool = True,
) -> AutomationPrepareResult:
    root = root.resolve()
    classification = classification_path.read_text(encoding="utf-8")
    eligible_cases = tuple(match.group(1) for match in ELIGIBLE_ROW.finditer(classification))
    if not eligible_cases:
        return AutomationPrepareResult("skipped", None, ())

    repository = _select_api_repository(profile, repository_id)
    integration, provider = _load_provider(root, profile)
    config = integration.get("config", {})
    runtime_url = str(config.get("runtime_url", "")).strip()
    revision = str(config.get("runtime_revision", "")).strip()
    if not runtime_url.startswith(("https://", "ssh://", "git@")):
        raise AutomationPrepareError("runtime_url must be an HTTPS or SSH Git URL")
    if not revision or revision in MOVING_REVISIONS:
        raise AutomationPrepareError("runtime_revision must be an immutable tag or commit")

    destination = (root / str(repository["path"])).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise AutomationPrepareError("automation repository path escapes workspace root") from exc

    dependency = f"git+{runtime_url}@{revision}"
    pyproject = destination / "pyproject.toml"
    prepared = destination.is_dir() and pyproject.is_file()
    if prepared:
        if dependency not in pyproject.read_text(encoding="utf-8"):
            raise AutomationPrepareError(
                f"existing automation project is not pinned to {revision}: {pyproject}"
            )
        status = "reused"
    else:
        prepare = provider.get("prepare", {})
        script_value = prepare.get("script") if isinstance(prepare, dict) else None
        if not isinstance(script_value, str):
            raise AutomationPrepareError("automation provider prepare.script is required")
        skill_root = (root / "skills" / str(integration["skill"])).resolve()
        script = (skill_root / script_value).resolve()
        try:
            script.relative_to(skill_root)
        except ValueError as exc:
            raise AutomationPrepareError(
                "automation provider prepare.script escapes the Skill root"
            ) from exc
        if not script.is_file():
            raise AutomationPrepareError(f"automation provider script does not exist: {script}")
        command = [
            sys.executable,
            str(script),
            "--project-profile",
            str(profile_path.resolve()),
            "--workspace-root",
            str(root),
            "--repository-id",
            str(repository["id"]),
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            raise AutomationPrepareError(f"automation provider failed with exit code {exc.returncode}") from exc
        status = "created"

    if install:
        install_command = provider.get("prepare", {}).get("install_command")
        if not isinstance(install_command, list) or not install_command:
            raise AutomationPrepareError("automation provider install_command is required")
        try:
            subprocess.run(_render_command(install_command, destination), check=True)
        except subprocess.CalledProcessError as exc:
            raise AutomationPrepareError(f"automation dependency install failed with exit code {exc.returncode}") from exc
    return AutomationPrepareResult(status, destination, eligible_cases)
