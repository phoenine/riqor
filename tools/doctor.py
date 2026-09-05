from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .automation_provider import (
    AutomationProviderError,
    consumer_dependency,
    load_automation_provider,
)
from .artifacts import load_template_registry
from .contracts import (
    ContractError,
    load_markdown_frontmatter,
    load_yaml,
    validate_schema,
    validate_project_profile,
)
from .planner import load_capabilities
from .workflow_registry import load_workflows


@dataclass
class DoctorReport:
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _check_automation_provider(
    profile: dict, root: Path, report: DoctorReport, capability: str
) -> None:
    try:
        binding = load_automation_provider(
            root=root, profile=profile, capability=capability
        )
    except AutomationProviderError as exc:
        report.errors.append(f"{capability} automation: {exc}")
        return
    repository = binding.repository
    skill = str(binding.integration["skill"])
    dependency = consumer_dependency(binding)
    report.checks.append(
        f"{capability} automation {repository['id']} skill={skill}"
    )
    destination = root / repository["path"]
    if not destination.exists():
        report.checks.append(
            f"{capability} automation pending preparation {repository['path']}"
        )
        return
    manifest = destination / binding.provider["consumer"]["manifest"]
    if not manifest.is_file():
        report.errors.append(
            f"{capability} automation: prepared repository lacks consumer manifest: "
            f"{manifest}"
        )
        return
    if dependency not in manifest.read_text(encoding="utf-8"):
        report.errors.append(
            f"{capability} automation: consumer dependency is not configured: {manifest}"
        )
        return
    report.checks.append(f"{capability} automation prepared {repository['path']}")


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
    automation_capabilities = {
        str(capability)
        for repository in profile.get("repositories", {}).get("automation", [])
        for capability in repository.get("capabilities", [])
    }
    for capability in sorted(automation_capabilities):
        _check_automation_provider(profile, root, report, capability)

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

    workflows = load_workflows(root)
    if workflows.errors:
        report.errors.extend(f"workflows: {error}" for error in workflows.errors)
        return report
    if not workflows.records:
        report.errors.append(f"no workflow manifests found under {root / 'workflows'}")
        return report

    capabilities: list[tuple[Path, dict]] = []
    for workflow_id in sorted(workflows.records):
        registry = load_capabilities(root, workflow=workflow_id)
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
