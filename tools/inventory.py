from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import validate_artifact
from .run_state import sha256_file


@dataclass
class ArtifactRecord:
    path: Path
    metadata: dict[str, Any]
    effective_status: str = ""
    reasons: list[str] = field(default_factory=list)

    @property
    def artifact_id(self) -> str:
        return str(self.metadata["id"])

    @property
    def artifact_type(self) -> str:
        return str(self.metadata["type"])

    @property
    def scope_id(self) -> str:
        return str(self.metadata["scope_id"])

    @property
    def revision(self) -> int:
        return int(self.metadata["revision"])


@dataclass
class InventoryReport:
    artifact_root: Path
    records: list[ArtifactRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def artifact_root_for(profile: dict[str, Any]) -> Path:
    project_id = profile["project"]["id"]
    return Path(profile.get("artifacts", {}).get("root", f"outputs/{project_id}"))


def _source_reference(value: str) -> tuple[str, int]:
    artifact_id, separator, revision = value.rpartition("@")
    if not separator:
        raise ValueError(f"invalid artifact reference: {value}")
    return artifact_id, int(revision)


def load_inventory(root: Path, profile: dict[str, Any]) -> InventoryReport:
    root = root.resolve()
    artifact_root = artifact_root_for(profile)
    report = InventoryReport(artifact_root=artifact_root)
    project_id = profile["project"]["id"]
    project_tracks = set(profile["project"]["tracks"])
    records_by_id: dict[str, ArtifactRecord] = {}
    for path in sorted((root / "runs").glob("*/artifacts/*.json")):
        relative_path = path.relative_to(root)
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report.errors.append(f"cannot read artifact record {relative_path}: {exc}")
            continue
        if not isinstance(artifact, dict):
            report.errors.append(f"expected JSON object in {relative_path}")
            continue
        record_project_id = str(artifact.get("project_id", "")).strip()
        if record_project_id and record_project_id != project_id:
            continue
        artifact_errors = validate_artifact(artifact)
        if artifact_errors:
            report.errors.extend(f"{relative_path}: {error}" for error in artifact_errors)
            continue
        unknown_tracks = sorted(set(artifact["tracks"]) - project_tracks)
        if unknown_tracks:
            report.errors.append(
                f"{relative_path}: unknown project tracks: {', '.join(unknown_tracks)}"
            )
            continue
        artifact_id = artifact["id"]
        if artifact_id in records_by_id:
            first = records_by_id[artifact_id].path
            report.errors.append(
                f"duplicate artifact id {artifact_id}: {first} and {relative_path}"
            )
            continue
        record = ArtifactRecord(path=relative_path, metadata=artifact)
        records_by_id[artifact_id] = record
        report.records.append(record)

    cycle_errors: set[str] = set()

    def calculate(record: ArtifactRecord, stack: tuple[str, ...]) -> str:
        if record.effective_status:
            return record.effective_status
        declared_status = str(record.metadata["status"])
        if declared_status != "ready":
            record.effective_status = declared_status
            return record.effective_status
        content_path = root / str(record.metadata["content_path"])
        if not content_path.is_file():
            record.reasons.append(
                f"artifact content is missing: {record.metadata['content_path']}"
            )
        expected_hash = str(record.metadata.get("content_sha256", "")).strip()
        if record.metadata.get("run_id") and not expected_hash:
            record.reasons.append("managed ready artifact is missing content_sha256; revalidate it")
        elif expected_hash and content_path.is_file() and sha256_file(content_path) != expected_hash:
            record.reasons.append("artifact content changed after validation")
        if record.artifact_id in stack:
            cycle = " -> ".join((*stack, record.artifact_id))
            message = f"artifact dependency cycle: {cycle}"
            cycle_errors.add(message)
            record.effective_status = "stale"
            record.reasons.append(message)
            return record.effective_status

        next_stack = (*stack, record.artifact_id)
        for reference in record.metadata["source_artifacts"]:
            source_id, expected_revision = _source_reference(reference)
            source = records_by_id.get(source_id)
            if source is None:
                record.reasons.append(f"missing source artifact {reference}")
                continue
            if source.revision != expected_revision:
                record.reasons.append(
                    f"source revision changed: expected {reference}, "
                    f"current {source_id}@{source.revision}"
                )
                continue
            source_status = calculate(source, next_stack)
            if source_status != "ready":
                record.reasons.append(
                    f"source artifact {source_id}@{source.revision} is {source_status}"
                )
        record.effective_status = "stale" if record.reasons else "ready"
        return record.effective_status

    for record in report.records:
        calculate(record, ())
    report.errors.extend(sorted(cycle_errors))
    report.records.sort(
        key=lambda item: (item.scope_id, item.artifact_type, item.artifact_id)
    )
    return report
