#!/usr/bin/env python3
"""Create a minimal rigorpath Web test consumer without overwriting files."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


ASSETS = Path(__file__).resolve().parent.parent / "assets" / "project-template"


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
            f"rigorpath-api-test[web] @ git+{runtime_url}@{runtime_revision}"
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
    subprocess.run(["uv", "sync", "--project", str(destination.resolve())], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--runtime-url", required=True)
    parser.add_argument("--runtime-revision", required=True)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    for path in scaffold(
        args.destination,
        args.project_name,
        args.runtime_url,
        args.runtime_revision,
    ):
        print(path)
    if args.install:
        install(args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
