from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

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
WORKSPACE_RUNTIME_DIRECTORIES = ("config", "schemas", "skills", "templates", "workflows")


class InitError(ValueError):
    """Raised when project initialization cannot safely complete."""


@dataclass(frozen=True)
class InitResult:
    profile_path: Path
    knowledge_root: Path
    source_count: int


def load_automation_presets() -> dict[str, dict[str, Any]]:
    path = REPOSITORY_ROOT / "config" / "automation-presets.yaml"
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise InitError(f"cannot load automation presets: {exc}") from exc
    presets = document.get("presets") if isinstance(document, dict) else None
    if not isinstance(presets, dict):
        raise InitError("automation presets must contain a presets mapping")
    return presets


def _automation_configuration(
    project_id: str,
    selections: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(set(selections)) != len(selections):
        raise InitError("automation selections must be unique")
    presets = load_automation_presets()
    repositories: list[dict[str, Any]] = []
    integrations: dict[str, Any] = {}
    for selection in selections:
        preset = presets.get(selection)
        if not isinstance(preset, dict):
            raise InitError(
                f"unknown automation preset {selection!r}; available: "
                + ", ".join(sorted(presets))
            )
        required = ("repository_suffix", "capability", "integration", "skill", "config")
        missing = [key for key in required if key not in preset]
        if missing:
            raise InitError(
                f"automation preset {selection!r} is missing: " + ", ".join(missing)
            )
        repository_id = f"{project_id}-{preset['repository_suffix']}"
        repositories.append(
            {
                "id": repository_id,
                "path": f"repositories/automation/{repository_id}",
                "capabilities": [str(preset["capability"])],
            }
        )
        integration_id = str(preset["integration"])
        if integration_id in integrations:
            raise InitError(f"duplicate automation integration: {integration_id}")
        integrations[integration_id] = {
            "skill": str(preset["skill"]),
            "config": dict(preset["config"]),
        }
    return repositories, integrations


def _render_template(name: str, values: dict[str, str]) -> str:
    template = (
        REPOSITORY_ROOT / "templates" / "knowledge" / "standard-product" / name
    ).read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def _seed_workspace_runtime(root: Path) -> list[Path]:
    created: list[Path] = []
    for name in WORKSPACE_RUNTIME_DIRECTORIES:
        source = REPOSITORY_ROOT / name
        destination = root / name
        if destination.exists():
            continue
        shutil.copytree(source, destination)
        created.append(destination)
    return created


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
    automations: Sequence[str] = (),
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
    automation_repositories, automation_integrations = _automation_configuration(
        project_id, automations
    )
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
        "repositories": {
            "product": [],
            "automation": automation_repositories,
            "tools": [],
        },
        "policies": {
            "require_confirmation": [
                "remote_write",
                "shared_environment_execution",
                "shared_data_mutation",
            ]
        },
    }
    if automation_integrations:
        profile["integrations"] = automation_integrations
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
    created_runtime: list[Path] = []
    try:
        created_runtime = _seed_workspace_runtime(root)
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
        for directory in reversed(created_runtime):
            shutil.rmtree(directory)
        raise InitError(f"cannot initialize project: {exc}") from exc

    return InitResult(
        profile_path=profile_relative,
        knowledge_root=knowledge_relative,
        source_count=len(registered_sources),
    )
