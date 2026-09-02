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


@dataclass
class DoctorReport:
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


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
