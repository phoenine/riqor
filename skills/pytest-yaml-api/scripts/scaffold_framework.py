#!/usr/bin/env python3
"""Create a minimal rigorpath-api-test consumer project without overwriting files."""

from __future__ import annotations

import argparse
from pathlib import Path


ASSETS = Path(__file__).resolve().parent.parent / "assets" / "project-template"


def scaffold(destination: Path, project_name: str, runtime_version: str) -> list[Path]:
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    replacements = {
        "{{PROJECT_NAME}}": project_name,
        "{{RUNTIME_VERSION}}": runtime_version,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--runtime-version", default="0.1.0")
    args = parser.parse_args()
    for path in scaffold(args.destination, args.project_name, args.runtime_version):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
