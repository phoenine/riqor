from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .artifacts import load_template_registry
from .contracts import (
    ContractError,
    load_markdown_frontmatter,
    load_yaml,
    validate_schema,
    validate_project_profile,
)
from .planner import load_capabilities


MOVING_REVISIONS = {"main", "master", "HEAD"}


@dataclass
class DoctorReport:
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _check_api_automation(profile: dict, root: Path, report: DoctorReport) -> None:
    error_count = len(report.errors)
    integration = profile.get("integrations", {}).get("api_automation")
    if integration is None:
        return
    if not isinstance(integration, dict) or not integration.get("skill"):
        report.errors.append("api automation: integrations.api_automation.skill is required")
        return
    repositories = [
        item
        for item in profile.get("repositories", {}).get("automation", [])
        if "api" in item.get("capabilities", [])
    ]
    if len(repositories) != 1:
        report.errors.append("api automation: exactly one api-capable repository is required")
        return
    skill = str(integration["skill"])
    provider = root / "skills" / skill / "provider.yaml"
    if not provider.is_file():
        report.errors.append(f"api automation: provider does not exist: {provider}")
        return
    try:
        provider_config = load_yaml(provider)
    except ContractError as exc:
        report.errors.append(f"api automation: {exc}")
        return
    prepare = provider_config.get("prepare")
    if provider_config.get("capability") != "api" or not isinstance(prepare, dict):
        report.errors.append("api automation: provider must declare api capability and prepare")
        return
    script_value = prepare.get("script")
    if not isinstance(script_value, str):
        report.errors.append("api automation: provider prepare.script is required")
        return
    skill_root = provider.parent
    script = (skill_root / script_value).resolve()
    try:
        script.relative_to(skill_root.resolve())
    except ValueError:
        report.errors.append("api automation: provider prepare.script escapes the Skill root")
        return
    if not script.is_file():
        report.errors.append(f"api automation: provider script does not exist: {script}")
        return
    config = integration.get("config", {})
    runtime_url = str(config.get("runtime_url", "")).strip()
    revision = str(config.get("runtime_revision", "")).strip()
    if not runtime_url.startswith(("https://", "ssh://", "git@")):
        report.errors.append("api automation: runtime_url must be an HTTPS or SSH Git URL")
    if not revision or revision in MOVING_REVISIONS:
        report.errors.append("api automation: runtime_revision must be an immutable tag or commit")
    if len(report.errors) > error_count:
        return
    repository = repositories[0]
    report.checks.append(
        f"api automation {repository['id']} skill={skill} revision={revision}"
    )
    destination = root / repository["path"]
    if not destination.exists():
        report.checks.append(f"api automation pending preparation {repository['path']}")
        return
    pyproject = destination / "pyproject.toml"
    if not pyproject.is_file():
        report.errors.append(
            f"api automation: prepared repository lacks pyproject.toml: {destination}"
        )
        return
    expected = f"git+{runtime_url}@{revision}"
    if expected not in pyproject.read_text(encoding="utf-8"):
        report.errors.append(
            f"api automation: consumer dependency is not pinned to {revision}: {pyproject}"
        )
        return
    report.checks.append(f"api automation prepared {repository['path']}")


def run_doctor(project_file: Path, root: Path) -> DoctorReport:
    report = DoctorReport()
    try:
        profile = load_yaml(project_file)
    except ContractError as exc:
        report.errors.append(str(exc))
        return report

    profile_errors = validate_project_profile(profile)
    if profile_errors:
        report.errors.extend(f"project profile: {error}" for error in profile_errors)
        return report

    project_id = profile["project"]["id"]
    report.checks.append(f"project {project_id}")
    _check_api_automation(profile, root, report)

    index_path = root / profile["knowledge"]["index"]
    if index_path.is_file():
        try:
            frontmatter = load_markdown_frontmatter(index_path)
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            knowledge_errors = validate_schema(frontmatter, "knowledge-page")
            if knowledge_errors:
                report.errors.extend(
                    f"knowledge index: {error}" for error in knowledge_errors
                )
            else:
                report.checks.append(f"knowledge index {index_path.relative_to(root)}")
    else:
        report.errors.append(f"knowledge index does not exist: {index_path}")

    sources_path = (root / profile["knowledge"]["root"]) / "_sources.yaml"
    if sources_path.is_file():
        try:
            sources = load_yaml(sources_path)
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            report.errors.extend(
                f"knowledge sources: {error}"
                for error in validate_schema(sources, "knowledge-sources")
            )

    capabilities_root = root / "workflows"
    workflow_packs = sorted(
        path for path in capabilities_root.iterdir()
        if path.is_dir() and any(path.glob("capabilities/*.yaml"))
    ) if capabilities_root.is_dir() else []
    if not workflow_packs:
        report.errors.append(f"no capabilities found under {capabilities_root}")
        return report

    capabilities: list[tuple[Path, dict]] = []
    for pack in workflow_packs:
        registry = load_capabilities(root, workflow=pack.name)
        report.errors.extend(registry.errors)
        capabilities.extend((root / record.path, record.metadata) for record in registry.records)

    if not report.errors:
        report.checks.append(f"capabilities {len(capabilities)}")
    templates = load_template_registry(root)
    if templates.errors:
        report.errors.extend(f"artifact templates: {error}" for error in templates.errors)
    else:
        report.checks.append(f"artifact templates {len(templates.templates)}")
        for capability_file, capability in capabilities:
            template_id = capability.get("template")
            if not template_id:
                continue
            template = templates.templates.get(template_id)
            relative = capability_file.relative_to(root)
            if template is None:
                report.errors.append(f"{relative}: unknown artifact template {template_id}")
            elif template.artifact_type not in capability["produces"]:
                report.errors.append(
                    f"{relative}: template {template_id} produces "
                    f"{template.artifact_type}, not {capability['produces']}"
                )
    return report
