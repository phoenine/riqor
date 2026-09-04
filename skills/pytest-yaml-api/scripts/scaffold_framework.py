#!/usr/bin/env python3
"""Create a minimal rigorpath-api-test consumer project without overwriting files."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
from typing import Any

import yaml


ASSETS = Path(__file__).resolve().parent.parent / "assets" / "project-template"
DEFAULT_RUNTIME_URL = "https://github.com/phoenine/rigorpath_api_test.git"


def settings_from_profile(
    profile_path: Path,
    workspace_root: Path,
    repository_id: str | None = None,
) -> tuple[Path, str, str, str]:
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("project profile must be a mapping")
    automation = profile.get("repositories", {}).get("automation", [])
    candidates = [
        repository
        for repository in automation
        if isinstance(repository, dict)
        and "api" in repository.get("capabilities", [])
        and (repository_id is None or repository.get("id") == repository_id)
    ]
    if len(candidates) != 1:
        raise ValueError("select exactly one API automation repository")
    repository: dict[str, Any] = candidates[0]
    integration = profile.get("integrations", {}).get("api_automation", {})
    if integration.get("skill") != "pytest-yaml-api":
        raise ValueError("integrations.api_automation.skill must be pytest-yaml-api")
    config = integration.get("config", {})
    revision = str(config.get("runtime_revision", "")).strip()
    runtime_url = str(config.get("runtime_url", DEFAULT_RUNTIME_URL)).strip()
    root = workspace_root.resolve()
    destination = (root / str(repository["path"])).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise ValueError("automation repository path escapes workspace root") from exc
    return destination, str(repository["id"]), runtime_url, revision


def scaffold(
    destination: Path,
    project_name: str,
    runtime_url: str,
    runtime_revision: str,
) -> list[Path]:
    destination = destination.resolve()
    if not runtime_url.startswith(("https://", "ssh://", "git@")):
        raise ValueError("runtime_url must be an HTTPS or SSH Git URL")
    if not runtime_revision or runtime_revision in {"main", "master", "HEAD"}:
        raise ValueError("runtime_revision must be an immutable tag or commit")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    replacements = {
        "{{PROJECT_NAME}}": project_name,
        "{{RUNTIME_DEPENDENCY}}": (
            f"rigorpath-api-test @ git+{runtime_url}@{runtime_revision}"
        ),
        "{{RUNTIME_REVISION}}": runtime_revision,
    }
    written: list[Path] = []
    for source in sorted(path for path in ASSETS.rglob("*") if path.is_file()):
        relative = source.relative_to(ASSETS)
        if relative.name.endswith(".tmpl"):
            relative = relative.with_name(relative.name.removesuffix(".tmpl"))
        target = destination / relative
        if target.exists():
            raise FileExistsError(f"refusing to overwrite: {target}")
        content = source.read_text(encoding="utf-8")
        for marker, value in replacements.items():
            content = content.replace(marker, value)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def install(destination: Path) -> None:
    subprocess.run(
        ["uv", "sync", "--project", str(destination.resolve())],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--destination", type=Path)
    source.add_argument("--project-profile", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--repository-id")
    parser.add_argument("--project-name")
    parser.add_argument("--runtime-url", default=DEFAULT_RUNTIME_URL)
    parser.add_argument("--runtime-revision")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if args.project_profile:
        destination, project_name, runtime_url, runtime_revision = settings_from_profile(
            args.project_profile,
            args.workspace_root,
            args.repository_id,
        )
    else:
        if not args.project_name or not args.runtime_revision:
            parser.error("explicit destination requires --project-name and --runtime-revision")
        destination = args.destination
        project_name = args.project_name
        runtime_url = args.runtime_url
        runtime_revision = args.runtime_revision
    for path in scaffold(
        destination,
        project_name,
        runtime_url,
        runtime_revision,
    ):
        print(path)
    if args.install:
        install(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
