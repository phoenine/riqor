from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

try:
    from .contracts import ContractError, load_yaml, validate_schema
except ImportError:  # pragma: no cover - compatibility for direct script imports
    try:
        from tools.contracts import ContractError, load_yaml, validate_schema
    except ImportError:
        from contracts import ContractError, load_yaml, validate_schema


@dataclass(frozen=True)
class WorkflowPhase:
    name: str
    document: str
    gate: dict


@dataclass(frozen=True)
class WorkflowRecord:
    workflow_id: str
    readme: str
    scope_directory: str
    phases: tuple[WorkflowPhase, ...]
    path: Path


@dataclass
class WorkflowRegistry:
    records: dict[str, WorkflowRecord] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class WorkflowRegistryError(ValueError):
    """Raised when a workflow pack cannot be loaded safely."""


def _safe_pack_path(pack: Path, value: str) -> Path | None:
    logical = PurePosixPath(value)
    if logical.is_absolute() or ".." in logical.parts or value in {"", "."}:
        return None
    return pack / logical


def load_workflows(root: Path) -> WorkflowRegistry:
    root = root.resolve()
    registry = WorkflowRegistry()
    workflows_root = root / "workflows"
    for pack in sorted(path for path in workflows_root.glob("*") if path.is_dir()):
        if any(pack.glob("capabilities/*.yaml")) and not (pack / "workflow.yaml").is_file():
            registry.errors.append(
                f"{pack.relative_to(root)}: workflow.yaml is required"
            )
    for path in sorted(workflows_root.glob("*/workflow.yaml")):
        relative = path.relative_to(root)
        try:
            document = load_yaml(path)
        except ContractError as exc:
            registry.errors.append(str(exc))
            continue
        errors = validate_schema(document, "workflow")
        if errors:
            registry.errors.extend(f"{relative}: {error}" for error in errors)
            continue
        workflow_id = str(document["id"])
        if path.parent.name != workflow_id:
            registry.errors.append(
                f"{relative}: id must match directory name {path.parent.name}"
            )
            continue
        if workflow_id in registry.records:
            registry.errors.append(f"duplicate workflow id: {workflow_id}")
            continue
        names: set[str] = set()
        phases: list[WorkflowPhase] = []
        readme = _safe_pack_path(path.parent, str(document["readme"]))
        if readme is None or not readme.is_file():
            registry.errors.append(f"{relative}: workflow readme does not exist")
            continue
        for phase in document["phases"]:
            name = str(phase["name"])
            phase_document = str(phase["document"])
            target = _safe_pack_path(path.parent, phase_document)
            if name in names:
                registry.errors.append(f"{relative}: duplicate phase name {name}")
            elif target is None or not target.is_file():
                registry.errors.append(
                    f"{relative}: phase document does not exist: {phase_document}"
                )
            else:
                names.add(name)
                phases.append(WorkflowPhase(name, phase_document, dict(phase["gate"])))
        if len(phases) != len(document["phases"]):
            continue
        registry.records[workflow_id] = WorkflowRecord(
            workflow_id=workflow_id,
            readme=(Path("workflows") / workflow_id / str(document["readme"])).as_posix(),
            scope_directory=str(document["scope_directory"]),
            phases=tuple(phases),
            path=relative,
        )
    return registry


def load_workflow(root: Path, workflow_id: str) -> WorkflowRecord:
    registry = load_workflows(root)
    if registry.errors:
        raise WorkflowRegistryError("invalid workflow registry: " + "; ".join(registry.errors))
    record = registry.records.get(workflow_id)
    if record is None:
        raise WorkflowRegistryError(f"unknown workflow: {workflow_id}")
    return record
