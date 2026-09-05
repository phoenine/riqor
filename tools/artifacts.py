from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .artifact_frontmatter import ARTIFACT_SPECS
from .contracts import validate_artifact
from .copy_template import TEMPLATES, create_artifact_from_template, register_artifact
from .inventory import ArtifactRecord, artifact_root_for, load_inventory
from .planner import CapabilityRecord
from .run_state import load_state as load_run_state, sha256_file
from .stage_gate import check_state, write_gate_result
from .validate_artifact import validate_artifact_file
from .validate_test_cases import validate_test_case_file
from .workflow_registry import WorkflowRegistryError, load_workflow


@dataclass(frozen=True)
class TemplateRecord:
    template_id: str
    artifact_type: str
    path: Path
    validator: str


@dataclass
class TemplateRegistry:
    templates: dict[str, TemplateRecord] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScaffoldResult:
    manifest_path: Path
    content_path: Path


@dataclass
class GateResult:
    artifact_id: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    marked_ready: bool = False


class ArtifactActionError(ValueError):
    """Raised when a local artifact lifecycle action is unsafe or invalid."""


def attach_artifact_inputs(
    *, root: Path, run_id: str, records: Sequence[ArtifactRecord]
) -> None:
    """Expose ready inventory inputs to one Run State for gates and traceability."""
    state_path = root.resolve() / "runs" / run_id / "state.json"
    for record in records:
        if record.effective_status != "ready":
            raise ArtifactActionError(
                f"run input artifact is not ready: {record.artifact_id}@{record.revision}"
            )
        registered = register_artifact(
            state_path=state_path,
            artifact_id=record.artifact_id,
            artifact_type=record.artifact_type,
            destination=Path(str(record.metadata["content_path"])),
            producer_phase="Registered Ready Input",
            source_artifacts=list(record.metadata["source_artifacts"]),
            evidence=[],
            validation_status="passed",
        )
        if not registered:
            raise ArtifactActionError(f"run state does not exist: runs/{run_id}/state.json")


ARTIFACT_FILENAMES = {
    artifact_type: f"{template_id}.md"
    for template_id, (_path, artifact_type) in TEMPLATES.items()
}


def load_template_registry(root: Path) -> TemplateRegistry:
    root = root.resolve()
    registry = TemplateRegistry()
    artifact_types: set[str] = set()
    for template_id, (filename, artifact_type) in TEMPLATES.items():
        if template_id in registry.templates:
            registry.errors.append(f"duplicate artifact template id: {template_id}")
            continue
        if artifact_type in artifact_types:
            registry.errors.append(f"duplicate artifact template type: {artifact_type}")
            continue
        path = Path("templates") / filename
        if not (root / path).is_file():
            registry.errors.append(f"artifact template does not exist: {path}")
            continue
        if artifact_type != "test_cases" and artifact_type not in ARTIFACT_SPECS:
            registry.errors.append(f"artifact type has no validator: {artifact_type}")
            continue
        artifact_types.add(artifact_type)
        registry.templates[template_id] = TemplateRecord(
            template_id=template_id,
            artifact_type=artifact_type,
            path=path,
            validator="test_cases" if artifact_type == "test_cases" else "artifact",
        )
    return registry


def scaffold_artifact(
    *,
    root: Path,
    profile: dict[str, Any],
    capability: CapabilityRecord,
    scope_id: str,
    artifact_id: str,
    source_references: Sequence[str],
    tracks: Sequence[str],
    run_id: str | None = None,
) -> ScaffoldResult:
    root = root.resolve()
    metadata = capability.metadata
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", artifact_id):
        raise ArtifactActionError("artifact id contains unsafe characters")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", scope_id):
        raise ArtifactActionError("scope id contains unsafe characters")
    if len(set(source_references)) != len(source_references):
        raise ArtifactActionError("source artifact references must be unique")
    if metadata["side_effect"]:
        raise ArtifactActionError("scaffold only supports local, side-effect-free capabilities")
    outputs = metadata["produces"]
    if len(outputs) != 1:
        raise ArtifactActionError("scaffold requires a capability with exactly one output")
    template_id = metadata.get("template")
    if not template_id:
        raise ArtifactActionError(f"capability {capability.capability_id} has no template")
    registry = load_template_registry(root)
    if registry.errors:
        raise ArtifactActionError("invalid template registry: " + "; ".join(registry.errors))
    template = registry.templates.get(template_id)
    if template is None:
        raise ArtifactActionError(f"unknown artifact template: {template_id}")
    artifact_type = outputs[0]
    if template.artifact_type != artifact_type:
        raise ArtifactActionError(
            f"template {template_id} produces {template.artifact_type}, expected {artifact_type}"
        )
    if template_id not in TEMPLATES or TEMPLATES[template_id][1] != artifact_type:
        raise ArtifactActionError(
            f"template {template_id} is not managed by copy_template.py for {artifact_type}"
        )

    project_tracks = set(profile["project"]["tracks"])
    if not tracks or len(set(tracks)) != len(tracks) or set(tracks) - project_tracks:
        raise ArtifactActionError("artifact tracks must be declared by the project")
    inventory = load_inventory(root, profile)
    if inventory.errors:
        raise ArtifactActionError("invalid inventory: " + "; ".join(inventory.errors))
    if any(item.artifact_id == artifact_id for item in inventory.records):
        raise ArtifactActionError(f"artifact id already exists: {artifact_id}")
    records_by_reference = {
        f"{item.artifact_id}@{item.revision}": item for item in inventory.records
    }
    sources = []
    for reference in source_references:
        record = records_by_reference.get(reference)
        if record is None:
            raise ArtifactActionError(f"source artifact is missing or revision changed: {reference}")
        if record.effective_status != "ready":
            raise ArtifactActionError(f"source artifact is not ready: {reference}")
        if not metadata.get("cross_scope_inputs", False) and record.scope_id != scope_id:
            raise ArtifactActionError(
                f"cross-scope source is not allowed: {reference} belongs to {record.scope_id}"
            )
        sources.append(record)
    source_types = {item.artifact_type for item in sources}
    requires = metadata.get("requires", {})
    missing = sorted(set(requires.get("all", [])) - source_types)
    if missing:
        raise ArtifactActionError("missing required source types: " + ", ".join(missing))
    any_types = set(requires.get("any", []))
    if any_types and not (any_types & source_types):
        raise ArtifactActionError(
            "one of these source types is required: " + ", ".join(sorted(any_types))
        )

    artifact_root = artifact_root_for(profile)
    try:
        workflow = load_workflow(root, str(metadata["workflow"]))
    except WorkflowRegistryError as exc:
        raise ArtifactActionError(str(exc)) from exc
    scope_directory = workflow.scope_directory
    relative_directory = artifact_root / scope_directory / scope_id
    content_path = relative_directory / ARTIFACT_FILENAMES[artifact_type]
    registry_run_id = run_id or "inventory-only"
    manifest_path = Path("runs") / registry_run_id / "artifacts" / f"{artifact_id}.json"
    absolute_manifest = root / manifest_path
    absolute_content = root / content_path
    if absolute_manifest.exists() or absolute_content.exists():
        raise ArtifactActionError(f"artifact output already exists for {artifact_id}")
    artifact = {
        "schema_version": 1,
        "id": artifact_id,
        "type": artifact_type,
        "project_id": profile["project"]["id"],
        "scope_id": scope_id,
        "tracks": list(tracks),
        "status": "draft",
        "revision": 1,
        "content_path": content_path.as_posix(),
        "source_artifacts": list(source_references),
        "evidence": [],
        "validation": {"status": "pending", "errors": []},
    }
    if run_id:
        artifact["run_id"] = run_id
    artifact_errors = validate_artifact(artifact)
    if artifact_errors:
        raise ArtifactActionError("generated artifact is invalid: " + "; ".join(artifact_errors))
    created_files: list[Path] = []
    try:
        absolute_manifest.parent.mkdir(parents=True, exist_ok=True)
        create_artifact_from_template(
            root=root,
            run_id=run_id or "inventory-only",
            template=template_id,
            destination=content_path,
            producer_phase=str(metadata["phase"]),
            artifact_id=artifact_id,
            source_artifacts=list(source_references),
            register_state=False,
        )
        created_files.append(absolute_content)
        absolute_manifest.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        created_files.append(absolute_manifest)
        if run_id:
            registered = register_artifact(
                state_path=root / "runs" / run_id / "state.json",
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                destination=content_path,
                producer_phase=str(metadata["phase"]),
                source_artifacts=list(source_references),
                evidence=[],
                validation_status="pending",
            )
            if not registered:
                raise OSError(f"run state does not exist: runs/{run_id}/state.json")
    except (OSError, ValueError) as exc:
        for created_file in created_files:
            created_file.unlink(missing_ok=True)
        raise ArtifactActionError(f"cannot scaffold artifact: {exc}") from exc
    return ScaffoldResult(manifest_path=manifest_path, content_path=content_path)


def gate_artifact(
    *,
    root: Path,
    profile: dict[str, Any],
    artifact_id: str,
    mark_ready: bool = False,
    run_id: str | None = None,
) -> GateResult:
    root = root.resolve()
    inventory = load_inventory(root, profile)
    if inventory.errors:
        return GateResult(artifact_id, False, [f"inventory: {item}" for item in inventory.errors])
    record = next((item for item in inventory.records if item.artifact_id == artifact_id), None)
    if record is None:
        return GateResult(artifact_id, False, [f"artifact does not exist: {artifact_id}"])
    errors: list[str] = []
    records = {f"{item.artifact_id}@{item.revision}": item for item in inventory.records}
    for reference in record.metadata["source_artifacts"]:
        source = records.get(reference)
        if source is None:
            errors.append(f"source artifact is missing or revision changed: {reference}")
        elif source.effective_status != "ready":
            errors.append(f"source artifact is not ready: {reference}")

    content_path = root / record.metadata["content_path"]
    if not content_path.is_file():
        errors.append(f"artifact content does not exist: {record.metadata['content_path']}")
    elif record.artifact_type == "test_cases":
        errors.extend(
            validate_test_case_file(
                content_path,
                source_root=root,
                expected_artifact_id=record.artifact_id,
            )
        )
    elif record.artifact_type in ARTIFACT_SPECS:
        errors.extend(
            validate_artifact_file(
                content_path,
                expected_artifact_type=record.artifact_type,
                expected_artifact_id=record.artifact_id,
            )
        )
    if errors:
        return GateResult(artifact_id, False, errors)

    artifact_run_id = str(record.metadata.get("run_id", "")).strip()
    if artifact_run_id and artifact_run_id != run_id:
        return GateResult(
            artifact_id,
            False,
            [f"artifact belongs to run {artifact_run_id}, not {run_id}"],
        )
    effective_run_id = run_id or artifact_run_id
    state_path: Path | None = None
    state: dict[str, Any] | None = None
    if effective_run_id:
        state_path = root / "runs" / str(effective_run_id) / "state.json"
        if not state_path.is_file():
            return GateResult(
                artifact_id,
                False,
                [f"run state does not exist: runs/{effective_run_id}/state.json"],
            )
        try:
            state = load_run_state(state_path, str(effective_run_id))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return GateResult(artifact_id, False, [f"invalid run state: {exc}"])
        state_artifact = next(
            (
                item
                for item in state.get("artifacts", [])
                if item.get("id") == artifact_id
                and item.get("path") == record.metadata["content_path"]
            ),
            None,
        )
        if state_artifact is None:
            return GateResult(
                artifact_id,
                False,
                [f"run {effective_run_id} does not register artifact {artifact_id}"],
            )
        stage_errors = check_state(state, strict_phase=True, repo_root=root)
        if stage_errors:
            write_gate_result(state_path, state, stage_errors)
            return GateResult(
                artifact_id,
                False,
                [f"stage gate: {message}" for message in stage_errors],
            )
    if mark_ready:
        record.metadata["status"] = "ready"
        record.metadata["content_sha256"] = sha256_file(content_path)
        record.metadata["validation"] = {
            "status": "passed",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "errors": [],
        }
        (root / record.path).write_text(
            json.dumps(record.metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if state_path is not None and state is not None:
            for item in state.get("artifacts", []):
                if item.get("id") == artifact_id:
                    item["validation"] = {"status": "passed"}
                    break
            write_gate_result(state_path, state, [])
    return GateResult(artifact_id, True, marked_ready=mark_ready)
