"""Shared helpers for agent-next unit tests."""

from __future__ import annotations

import importlib.util
import re
import sys
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def load_tool(name: str):
    path = TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_template_artifact(
    *,
    template: str,
    destination: Path,
    artifact_id: str,
    producer_phase: str,
) -> Path:
    copy_template = load_tool("copy_template")
    path, _registered = copy_template.create_artifact(
        Namespace(
            run_id="demo",
            runs_root=destination.parent / ".runs",
            templates_root=ROOT / "templates",
            template=template,
            destination=destination,
            producer_phase=producer_phase,
            artifact_id=artifact_id,
            source_artifact=[],
            evidence=[],
            validation_status="pending",
            overwrite=True,
            allow_external_destination_for_tests=True,
        )
    )
    content = path.read_text(encoding="utf-8")
    content = re.sub(r"<[^>\n]+>", "completed", content)
    content = content.replace("TBD", "completed").replace("XXX", "001")
    if template == "requirement-spec":
        content = content.replace(
            "**依据类型**：completed", "**依据类型**：source_explicit"
        ).replace("**确认状态**：completed", "**确认状态**：confirmed")
    if template == "risk-analysis":
        content = content.replace(
            "**Risk Type**：completed", "**Risk Type**：functional"
        ).replace("**状态**：completed", "**状态**：pending_validation").replace(
            "**等级**：completed", "**等级**：P2"
        )
    path.write_text(content + "\nCompleted artifact content.\n", encoding="utf-8")
    return path
