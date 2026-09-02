from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPOSITORY_ROOT / "schemas"


class ContractError(ValueError):
    """Raised when a public Agent-next contract is invalid."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ContractError(f"cannot read YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected a YAML object in {path}")
    return value


def load_markdown_frontmatter(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read Markdown {path}: {exc}") from exc
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise ContractError(f"missing YAML frontmatter in {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ContractError(f"unterminated YAML frontmatter in {path}") from exc
    try:
        value = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ContractError(f"invalid YAML frontmatter in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected a YAML object in frontmatter of {path}")
    return value


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_ROOT / f"{name}.schema.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read schema {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected a JSON object in {path}")
    return value


def validate_schema(document: dict[str, Any], schema_name: str) -> list[str]:
    validator = Draft202012Validator(load_schema(schema_name))
    errors: list[str] = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "$"
        errors.append(f"{location}: {error.message}")
    return errors


def _is_safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and value not in {"", "."}


def validate_project_profile(profile: dict[str, Any]) -> list[str]:
    errors = validate_schema(profile, "project-profile")
    if errors:
        return errors

    project = profile["project"]
    tracks = project["tracks"]
    default_track = project.get("default_track")
    if default_track is not None and default_track not in tracks:
        errors.append("project.default_track: must be listed in project.tracks")

    knowledge = profile["knowledge"]
    root = knowledge["root"]
    index = knowledge["index"]
    for location, value in (("knowledge.root", root), ("knowledge.index", index)):
        if not _is_safe_relative_path(value):
            errors.append(f"{location}: must be a safe repository-relative path")
    if _is_safe_relative_path(root) and _is_safe_relative_path(index):
        root_path = PurePosixPath(root)
        index_path = PurePosixPath(index)
        if index_path != root_path and root_path not in index_path.parents:
            errors.append("knowledge.index: must be located under knowledge.root")

    artifacts_root = profile.get("artifacts", {}).get(
        "root", f"outputs/{project['id']}"
    )
    if not _is_safe_relative_path(artifacts_root):
        errors.append("artifacts.root: must be a safe repository-relative path")

    repositories = profile.get("repositories", {})
    for group, items in repositories.items():
        for position, item in enumerate(items):
            value = item["path"]
            if not _is_safe_relative_path(value):
                errors.append(
                    f"repositories.{group}.{position}.path: "
                    "must be a safe repository-relative path"
                )
    return errors


def validate_artifact(artifact: dict[str, Any]) -> list[str]:
    errors = validate_schema(artifact, "artifact")
    if errors:
        return errors

    artifact_id = artifact["id"]
    if not _is_safe_relative_path(artifact["content_path"]):
        errors.append("content_path: must be a safe repository-relative path")
    for reference in artifact["source_artifacts"]:
        source_id, _, _revision = reference.rpartition("@")
        if source_id == artifact_id:
            errors.append("source_artifacts: an artifact cannot depend on itself")
    if artifact["status"] == "ready" and artifact["validation"]["status"] != "passed":
        errors.append("validation.status: a ready artifact must have passed validation")
    return errors


def validate_capability(capability: dict[str, Any]) -> list[str]:
    errors = validate_schema(capability, "capability")
    if errors:
        return errors

    produced = set(capability["produces"])
    required = set(capability.get("requires", {}).get("all", []))
    optional = set(capability.get("optional", []))
    overlap = produced & (required | optional)
    if overlap:
        errors.append(
            "produces: cannot also be declared as an input: " + ", ".join(sorted(overlap))
        )

    side_effect = capability["side_effect"]
    action_class = capability["action_class"]
    if side_effect and action_class in {"local_read", "local_write"}:
        errors.append("action_class: side effects require a non-local action class")
    if not side_effect and action_class not in {"local_read", "local_write"}:
        errors.append("side_effect: must be true for remote or shared actions")
    return errors
