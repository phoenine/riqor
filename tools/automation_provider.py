from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .contracts import ContractError, load_yaml, validate_schema


MOVING_REVISIONS = {"main", "master", "HEAD"}


class AutomationProviderError(ValueError):
    """Raised when a configured automation provider violates its contract."""


@dataclass(frozen=True)
class AutomationProviderBinding:
    integration_id: str
    integration: dict[str, Any]
    provider: dict[str, Any]
    provider_path: Path
    repository: dict[str, Any]

    @property
    def config(self) -> dict[str, Any]:
        return self.integration.get("config", {})


def _safe_skill_path(root: Path, skill: str) -> Path:
    if not skill or "/" in skill or ".." in skill:
        raise AutomationProviderError("automation provider skill name is unsafe")
    return root / "skills" / skill / "provider.yaml"


def _render(template: str, config: dict[str, Any]) -> str:
    result = template
    for key, value in config.items():
        result = result.replace("{" + str(key) + "}", str(value))
    return result


def _render_arguments(
    arguments: list[str], values: dict[str, Any], *, label: str
) -> list[str]:
    rendered = [_render(str(argument), values) for argument in arguments]
    if any("{" in argument or "}" in argument for argument in rendered):
        raise AutomationProviderError(
            f"automation provider {label} contains unresolved config"
        )
    return rendered


def render_prepare_arguments(
    binding: AutomationProviderBinding, destination: Path
) -> list[str]:
    values = {
        **binding.config,
        "destination": str(destination),
        "repository_id": str(binding.repository["id"]),
    }
    return _render_arguments(
        binding.provider["prepare"]["arguments"],
        values,
        label="arguments",
    )


def render_install_command(
    binding: AutomationProviderBinding, destination: Path
) -> list[str]:
    return _render_arguments(
        binding.provider["prepare"]["install_command"],
        {**binding.config, "destination": str(destination)},
        label="install command",
    )


def load_automation_provider(
    *,
    root: Path,
    profile: dict[str, Any],
    capability: str,
    repository_id: str | None = None,
) -> AutomationProviderBinding:
    matches: list[tuple[str, dict[str, Any], dict[str, Any], Path]] = []
    for integration_id, integration in profile.get("integrations", {}).items():
        if not isinstance(integration, dict) or not integration.get("skill"):
            continue
        provider_path = _safe_skill_path(root, str(integration["skill"]))
        if not provider_path.is_file():
            continue
        try:
            provider = load_yaml(provider_path)
        except ContractError as exc:
            raise AutomationProviderError(str(exc)) from exc
        errors = validate_schema(provider, "automation-provider")
        if errors:
            raise AutomationProviderError(
                f"invalid automation provider {provider_path.relative_to(root)}: "
                + "; ".join(errors)
            )
        if provider["capability"] == capability:
            matches.append((integration_id, integration, provider, provider_path))
    if len(matches) != 1:
        raise AutomationProviderError(
            f"select exactly one automation provider for capability {capability}"
        )

    integration_id, integration, provider, provider_path = matches[0]
    repositories = [
        item
        for item in profile.get("repositories", {}).get("automation", [])
        if capability in item.get("capabilities", [])
        and (repository_id is None or item.get("id") == repository_id)
    ]
    if len(repositories) != 1:
        raise AutomationProviderError(
            f"select exactly one automation repository for capability {capability}"
        )

    script_value = provider["prepare"]["script"]
    script = (provider_path.parent / script_value).resolve()
    if not script.is_relative_to(provider_path.parent.resolve()):
        raise AutomationProviderError("automation provider prepare.script escapes the Skill root")
    if not script.is_file():
        raise AutomationProviderError(f"automation provider script does not exist: {script}")

    config = integration.get("config", {})
    declaration = provider["configuration"]
    missing = [key for key in declaration["required"] if not str(config.get(key, "")).strip()]
    if missing:
        raise AutomationProviderError(
            f"automation provider config is missing: {', '.join(missing)}"
        )
    for key in declaration["url_fields"]:
        value = str(config.get(key, "")).strip()
        if not value.startswith(("https://", "ssh://", "git@")):
            raise AutomationProviderError(
                f"automation provider config {key} must be an HTTPS or SSH Git URL"
            )
    for key in declaration["immutable_revision_fields"]:
        value = str(config.get(key, "")).strip()
        if not value or value in MOVING_REVISIONS:
            raise AutomationProviderError(
                f"automation provider config {key} must be an immutable tag or commit"
            )
    manifest = PurePosixPath(provider["consumer"]["manifest"])
    if manifest.is_absolute() or ".." in manifest.parts:
        raise AutomationProviderError("automation provider consumer.manifest is unsafe")
    dependency = _render(provider["consumer"]["dependency"], config)
    if "{" in dependency or "}" in dependency:
        raise AutomationProviderError("automation provider dependency has unresolved config")
    binding = AutomationProviderBinding(
        integration_id, integration, provider, provider_path, repositories[0]
    )
    render_prepare_arguments(binding, Path("destination"))
    render_install_command(binding, Path("destination"))
    return binding


def consumer_dependency(binding: AutomationProviderBinding) -> str:
    return _render(binding.provider["consumer"]["dependency"], binding.config)
