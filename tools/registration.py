"""Register existing local source documents as inventory artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .contracts import validate_artifact
from .inventory import load_inventory
from .run_state import sha256_file


@dataclass(frozen=True)
class RegistrationResult:
    manifest_path: Path


class RegistrationError(ValueError):
    """Raised when an existing source cannot safely enter the inventory."""


def register_existing_artifact(
    *,
    root: Path,
    profile: dict,
    artifact_id: str,
    artifact_type: str,
    scope_id: str,
    content_path: Path,
    tracks: Sequence[str],
    source_artifacts: Sequence[str] = (),
    ready: bool = False,
    run_id: str | None = None,
) -> RegistrationResult:
    """Create a run artifact record for an existing repository-local source file."""
    root = root.resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", artifact_id):
        raise RegistrationError("artifact id contains unsafe characters")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", artifact_type):
        raise RegistrationError("artifact type contains unsafe characters")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", scope_id):
        raise RegistrationError("scope id contains unsafe characters")
    if not tracks or len(set(tracks)) != len(tracks):
        raise RegistrationError("artifact tracks must be unique and non-empty")
    unknown_tracks = sorted(set(tracks) - set(profile["project"]["tracks"]))
    if unknown_tracks:
        raise RegistrationError("unknown project tracks: " + ", ".join(unknown_tracks))
    if len(set(source_artifacts)) != len(source_artifacts):
        raise RegistrationError("source artifact references must be unique")

    absolute_content = content_path if content_path.is_absolute() else root / content_path
    absolute_content = absolute_content.resolve()
    if not absolute_content.is_file():
        raise RegistrationError(f"content file does not exist: {content_path}")
    try:
        logical_content = absolute_content.relative_to(root).as_posix()
    except ValueError as exc:
        raise RegistrationError("content file must be inside the repository root") from exc

    inventory = load_inventory(root, profile)
    if inventory.errors:
        raise RegistrationError("invalid inventory: " + "; ".join(inventory.errors))
    if any(record.artifact_id == artifact_id for record in inventory.records):
        raise RegistrationError(f"artifact id already exists: {artifact_id}")

    registry_run_id = run_id or f"import-{profile['project']['id']}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", registry_run_id):
        raise RegistrationError("run id contains unsafe characters")
    manifest_path = Path("runs") / registry_run_id / "artifacts" / f"{artifact_id}.json"
    absolute_manifest = root / manifest_path
    if absolute_manifest.exists():
        raise RegistrationError(f"artifact record already exists: {manifest_path}")

    status = "ready" if ready else "draft"
    validation_status = "passed" if ready else "pending"
    artifact = {
        "schema_version": 1,
        "id": artifact_id,
        "type": artifact_type,
        "project_id": profile["project"]["id"],
        "scope_id": scope_id,
        "tracks": list(tracks),
        "status": status,
        "revision": 1,
        "content_path": logical_content,
        "content_sha256": sha256_file(absolute_content),
        "source_artifacts": list(source_artifacts),
        "evidence": [{"type": "document", "reference": logical_content}],
        "validation": {"status": validation_status},
    }
    errors = validate_artifact(artifact)
    if errors:
        raise RegistrationError("generated metadata is invalid: " + "; ".join(errors))
    absolute_manifest.parent.mkdir(parents=True, exist_ok=True)
    absolute_manifest.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return RegistrationResult(manifest_path=manifest_path)
