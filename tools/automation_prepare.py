from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .inventory import ArtifactRecord, load_inventory
from .validate_artifact import validate_artifact_file


MOVING_REVISIONS = {"main", "master", "HEAD"}


class AutomationPrepareError(ValueError):
    """Raised when automation preparation cannot proceed safely."""


@dataclass(frozen=True)
class AutomationPrepareResult:
    status: str
    destination: Path | None
    eligible_cases: tuple[str, ...]
    generated_files: tuple[Path, ...] = ()


@dataclass(frozen=True)
class AutomationSelection:
    classification: ArtifactRecord
    test_cases: ArtifactRecord
    run_inputs: tuple[ArtifactRecord, ...]
    eligible_cases: tuple[str, ...]
    repository: dict[str, Any] | None


def _classification_rows(text: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 9 or not cells[0].startswith("TC-"):
            continue
        rows.append((cells[0], cells[1], cells[2], cells[8]))
    return rows


def _select_api_repository(profile: dict[str, Any], repository_id: str | None) -> dict[str, Any]:
    candidates = [
        item
        for item in profile.get("repositories", {}).get("automation", [])
        if "api" in item.get("capabilities", [])
        and (repository_id is None or item.get("id") == repository_id)
    ]
    if len(candidates) != 1:
        raise AutomationPrepareError("select exactly one API automation repository")
    return candidates[0]


def _load_provider(root: Path, profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    integration = profile.get("integrations", {}).get("api_automation")
    if not isinstance(integration, dict) or not integration.get("skill"):
        raise AutomationPrepareError("integrations.api_automation.skill is required")
    skill = str(integration["skill"])
    if "/" in skill or ".." in skill:
        raise AutomationPrepareError("automation skill name is unsafe")
    provider_path = root / "skills" / skill / "provider.yaml"
    try:
        provider = yaml.safe_load(provider_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AutomationPrepareError(f"cannot load automation provider {provider_path}: {exc}") from exc
    if not isinstance(provider, dict) or provider.get("capability") != "api":
        raise AutomationPrepareError(f"automation provider {skill} does not declare api capability")
    return integration, provider


def _render_command(parts: list[Any], destination: Path) -> list[str]:
    return [str(part).replace("{destination}", str(destination)) for part in parts]


def render_automation_implementation(
    *,
    project_id: str,
    repository_id: str,
    runtime_revision: str,
    result: AutomationPrepareResult,
    classification_reference: str,
    test_cases_reference: str,
    installed: bool,
) -> str:
    file_rows = "\n".join(
        f"| {path.as_posix()} | generated consumer file | create or verify |"
        for path in result.generated_files
    )
    coverage_rows = "\n".join(
        f"| none | {case_id} | none | none | "
        f"{classification_reference} / {test_cases_reference} | not_applicable | "
        "framework prepared; case generation pending |"
        for case_id in result.eligible_cases
    )
    trace_rows = "\n".join(
        f"| {case_id} | none | automation_pending |"
        for case_id in result.eligible_cases
    )
    install_status = "passed" if installed else "not_run"
    install_evidence = "pinned dependency resolved" if installed else "--no-install selected"
    return f"""# 自动化实现记录

## 摘要

- 项目：{project_id}
- 自动化仓库：{repository_id}
- 框架与版本：rigorpath-api-test@{runtime_revision}
- 实现模式：bootstrap
- 目标环境：not_executed

## 来源覆盖

| AUTO ID | TC | DATA | TP | REQ / BR / RISK / Q | Assertion Type | 说明 |
|---|---|---|---|---|---|---|
{coverage_rows}

## 生成文件

| 文件 | 用途 | 变更类型 |
|---|---|---|
{file_rows}

## 静态校验

| 命令 | 结果 | 证据 |
|---|---|---|
| provider scaffold | passed | consumer project {result.status} |
| provider install | {install_status} | {install_evidence} |

## 执行边界

- 是否执行：no
- 确认记录：not_required_for_local_scaffold
- 副作用与清理：未执行测试，未修改共享环境或远端仓库

## 覆盖缺口

| Gap | 原因 | 后续动作 |
|---|---|---|
| API case generation | 当前步骤只准备框架 | 根据已验证 API contract 生成 AUTO YAML |

## 可追溯关系

| From | To | Relation |
|---|---|---|
{trace_rows}
"""


def select_automation_inputs(
    *,
    root: Path,
    profile: dict[str, Any],
    classification_artifact_id: str,
    test_cases_artifact_id: str,
    repository_id: str | None = None,
) -> AutomationSelection:
    inventory = load_inventory(root, profile)
    if inventory.errors:
        raise AutomationPrepareError("invalid inventory: " + "; ".join(inventory.errors))
    records = {record.artifact_id: record for record in inventory.records}
    classification = records.get(classification_artifact_id)
    test_cases = records.get(test_cases_artifact_id)
    for label, record, expected_type in (
        ("classification", classification, "automation_classification"),
        ("test cases", test_cases, "test_cases"),
    ):
        if record is None:
            raise AutomationPrepareError(f"{label} artifact does not exist")
        if record.artifact_type != expected_type:
            raise AutomationPrepareError(
                f"{label} artifact must have type {expected_type}, got {record.artifact_type}"
            )
        if record.effective_status != "ready":
            raise AutomationPrepareError(
                f"{label} artifact must be ready, got {record.effective_status}"
            )
    assert classification is not None and test_cases is not None
    if classification.scope_id != test_cases.scope_id:
        raise AutomationPrepareError("classification and test cases must belong to the same scope")
    classification_path = root / classification.metadata["content_path"]
    validation_errors = validate_artifact_file(
        classification_path,
        expected_artifact_type="automation_classification",
        expected_artifact_id=classification.artifact_id,
    )
    if validation_errors:
        raise AutomationPrepareError(
            "classification artifact validation failed: " + "; ".join(validation_errors)
        )
    rows = _classification_rows(classification_path.read_text(encoding="utf-8"))
    eligible = [row for row in rows if row[1] in {"A0", "A1"} and row[2] in {"api", "hybrid"}]
    records_by_reference = {
        f"{record.artifact_id}@{record.revision}": record
        for record in inventory.records
    }
    run_inputs: list[ArtifactRecord] = []
    visited: set[str] = set()

    def add_input(record: ArtifactRecord) -> None:
        reference = f"{record.artifact_id}@{record.revision}"
        if reference in visited:
            return
        visited.add(reference)
        for source_reference in record.metadata["source_artifacts"]:
            source = records_by_reference.get(source_reference)
            if source is None or source.effective_status != "ready":
                raise AutomationPrepareError(
                    f"source artifact is not ready or revision changed: {source_reference}"
                )
            add_input(source)
        run_inputs.append(record)

    add_input(test_cases)
    add_input(classification)
    if not eligible:
        return AutomationSelection(
            classification, test_cases, tuple(run_inputs), (), None
        )
    repository = _select_api_repository(profile, repository_id)
    mismatches = sorted({row[3] for row in eligible if row[3] != repository["id"]})
    if mismatches:
        raise AutomationPrepareError(
            f"eligible classification destination must be {repository['id']}, got: "
            + ", ".join(mismatches)
        )
    return AutomationSelection(
        classification,
        test_cases,
        tuple(run_inputs),
        tuple(row[0] for row in eligible),
        repository,
    )


def prepare_api_automation(
    *,
    root: Path,
    profile_path: Path,
    profile: dict[str, Any],
    selection: AutomationSelection,
    install: bool = True,
) -> AutomationPrepareResult:
    root = root.resolve()
    if not selection.eligible_cases:
        return AutomationPrepareResult("skipped", None, ())

    assert selection.repository is not None
    repository = selection.repository
    integration, provider = _load_provider(root, profile)
    config = integration.get("config", {})
    runtime_url = str(config.get("runtime_url", "")).strip()
    revision = str(config.get("runtime_revision", "")).strip()
    if not runtime_url.startswith(("https://", "ssh://", "git@")):
        raise AutomationPrepareError("runtime_url must be an HTTPS or SSH Git URL")
    if not revision or revision in MOVING_REVISIONS:
        raise AutomationPrepareError("runtime_revision must be an immutable tag or commit")

    destination = (root / str(repository["path"])).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise AutomationPrepareError("automation repository path escapes workspace root") from exc

    dependency = f"git+{runtime_url}@{revision}"
    pyproject = destination / "pyproject.toml"
    prepared = destination.is_dir() and pyproject.is_file()
    if prepared:
        if dependency not in pyproject.read_text(encoding="utf-8"):
            raise AutomationPrepareError(
                f"existing automation project is not pinned to {revision}: {pyproject}"
            )
        status = "reused"
    else:
        prepare = provider.get("prepare", {})
        script_value = prepare.get("script") if isinstance(prepare, dict) else None
        if not isinstance(script_value, str):
            raise AutomationPrepareError("automation provider prepare.script is required")
        skill_root = (root / "skills" / str(integration["skill"])).resolve()
        script = (skill_root / script_value).resolve()
        try:
            script.relative_to(skill_root)
        except ValueError as exc:
            raise AutomationPrepareError(
                "automation provider prepare.script escapes the Skill root"
            ) from exc
        if not script.is_file():
            raise AutomationPrepareError(f"automation provider script does not exist: {script}")
        command = [
            sys.executable,
            str(script),
            "--project-profile",
            str(profile_path.resolve()),
            "--workspace-root",
            str(root),
            "--repository-id",
            str(repository["id"]),
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            raise AutomationPrepareError(f"automation provider failed with exit code {exc.returncode}") from exc
        status = "created"

    if install:
        install_command = provider.get("prepare", {}).get("install_command")
        if not isinstance(install_command, list) or not install_command:
            raise AutomationPrepareError("automation provider install_command is required")
        try:
            subprocess.run(_render_command(install_command, destination), check=True)
        except subprocess.CalledProcessError as exc:
            raise AutomationPrepareError(f"automation dependency install failed with exit code {exc.returncode}") from exc
    generated_files = tuple(
        path.relative_to(root)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and ".venv" not in path.parts
    )
    return AutomationPrepareResult(
        status,
        destination,
        selection.eligible_cases,
        generated_files,
    )
