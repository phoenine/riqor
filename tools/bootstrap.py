from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml

from .contracts import REPOSITORY_ROOT, validate_project_profile


PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TRACK_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")
KNOWLEDGE_DIRECTORIES = (
    "glossary",
    "business-rules",
    "user-flows",
    "architecture",
    "interfaces",
    "data-model",
    "test-strategy",
    "operations",
)


class InitError(ValueError):
    """Raised when project initialization cannot safely complete."""


@dataclass(frozen=True)
class InitResult:
    profile_path: Path
    knowledge_root: Path
    source_count: int


def _render_template(name: str, values: dict[str, str]) -> str:
    template = (
        REPOSITORY_ROOT / "templates" / "knowledge" / "standard-product" / name
    ).read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def _relative_source(root: Path, source: Path) -> str:
    resolved = source if source.is_absolute() else root / source
    resolved = resolved.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise InitError(f"source must be located under the repository root: {source}") from exc
    if not resolved.is_file():
        raise InitError(f"source does not exist or is not a file: {source}")
    return relative.as_posix()


def _validate_inputs(
    project_id: str,
    name: str,
    tracks: Sequence[str],
    default_track: str,
) -> None:
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise InitError(
            "project id must use lowercase letters, numbers, and single hyphens"
        )
    if not name.strip():
        raise InitError("project name must not be empty")
    if not tracks:
        raise InitError("at least one track is required")
    if len(set(tracks)) != len(tracks):
        raise InitError("tracks must be unique")
    invalid_tracks = [track for track in tracks if not TRACK_PATTERN.fullmatch(track)]
    if invalid_tracks:
        raise InitError("invalid tracks: " + ", ".join(invalid_tracks))
    if default_track not in tracks:
        raise InitError("default track must be listed in tracks")


def init_project(
    *,
    root: Path,
    project_id: str,
    name: str,
    tracks: Sequence[str],
    default_track: str,
    sources: Sequence[Path] = (),
) -> InitResult:
    root = root.resolve()
    if not root.is_dir():
        raise InitError(f"repository root does not exist: {root}")
    _validate_inputs(project_id, name, tracks, default_track)

    profile_relative = Path("config") / "projects" / f"{project_id}.yaml"
    knowledge_relative = Path("knowledge") / project_id
    artifacts_relative = Path("outputs") / project_id
    profile_path = root / profile_relative
    knowledge_root = root / knowledge_relative
    if profile_path.exists():
        raise InitError(f"project profile already exists: {profile_relative}")
    if knowledge_root.exists():
        raise InitError(f"knowledge root already exists: {knowledge_relative}")

    registered_sources = [_relative_source(root, source) for source in sources]
    profile = {
        "schema_version": 1,
        "project": {
            "id": project_id,
            "name": name.strip(),
            "tracks": list(tracks),
            "default_track": default_track,
        },
        "knowledge": {
            "root": knowledge_relative.as_posix(),
            "template": "standard-product",
            "index": (knowledge_relative / "_index.md").as_posix(),
        },
        "artifacts": {"root": artifacts_relative.as_posix()},
        "repositories": {"product": [], "automation": [], "tools": []},
        "policies": {
            "require_confirmation": [
                "remote_write",
                "shared_environment_execution",
                "shared_data_mutation",
            ]
        },
    }
    profile_errors = validate_project_profile(profile)
    if profile_errors:
        raise InitError("generated profile is invalid: " + "; ".join(profile_errors))

    gaps_summary = (
        "Background sources are registered but have not been synthesized into "
        "confirmed knowledge."
        if registered_sources
        else "No background sources have been provided."
    )
    template_values = {
        "project_id": project_id,
        "project_name": name.strip(),
        "gaps_summary": gaps_summary,
    }

    created_knowledge = False
    created_profile = False
    try:
        knowledge_root.mkdir(parents=True, exist_ok=False)
        created_knowledge = True
        for directory in KNOWLEDGE_DIRECTORIES:
            category = knowledge_root / directory
            category.mkdir()
            (category / ".gitkeep").write_text("", encoding="utf-8")
        (knowledge_root / "_index.md").write_text(
            _render_template("index.md.tmpl", template_values), encoding="utf-8"
        )
        (knowledge_root / "_gaps.md").write_text(
            _render_template("gaps.md.tmpl", template_values), encoding="utf-8"
        )
        sources_document = {
            "schema_version": 1,
            "project_id": project_id,
            "sources": [
                {"type": "document", "reference": source, "status": "registered"}
                for source in registered_sources
            ],
        }
        (knowledge_root / "_sources.yaml").write_text(
            yaml.safe_dump(sources_document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            yaml.safe_dump(profile, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        created_profile = True
    except OSError as exc:
        if created_profile:
            profile_path.unlink(missing_ok=True)
        if created_knowledge:
            shutil.rmtree(knowledge_root)
        raise InitError(f"cannot initialize project: {exc}") from exc

    return InitResult(
        profile_path=profile_relative,
        knowledge_root=knowledge_relative,
        source_count=len(registered_sources),
    )
