#!/usr/bin/env python3
"""Create an agent-next artifact from a managed template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (  # noqa: E402
    AGENT_NEXT_ROOT,
    as_logical_path,
    resolve_managed_repo_path,
    resolve_repo_path,
)


DEFAULT_RUNS_ROOT = AGENT_NEXT_ROOT / "runs"
DEFAULT_TEMPLATES_ROOT = AGENT_NEXT_ROOT / "templates"

TEMPLATES = {
    "requirement-spec": ("artifacts/requirement-spec.md.tmpl", "requirement_spec"),
    "risk-analysis": ("artifacts/risk-analysis.md.tmpl", "risk_analysis"),
    "change-scope": ("artifacts/change-scope.md.tmpl", "change_scope"),
    "coverage-match": ("artifacts/coverage-match.md.tmpl", "coverage_match"),
    "regression-plan": ("artifacts/regression-plan.md.tmpl", "regression_plan"),
    "test-points": ("artifacts/test-points.md.tmpl", "test_points"),
    "test-cases": ("artifacts/test-cases.md.tmpl", "test_cases"),
    "regression-report": ("artifacts/regression-report.md.tmpl", "regression_report"),
    "acceptance-plan": ("artifacts/acceptance-plan.md.tmpl", "acceptance_plan"),
    "acceptance-report": ("artifacts/acceptance-report.md.tmpl", "acceptance_report"),
    "execution-record": ("artifacts/execution-record.md.tmpl", "execution_record"),
    "bug-report": ("artifacts/bug-report.md.tmpl", "bug_report"),
    "run-summary": ("artifacts/run-summary.md.tmpl", "run_summary"),
    "automation-classification": (
        "artifacts/automation-classification.md.tmpl",
        "automation_classification",
    ),
    "automation-implementation": (
        "artifacts/automation-implementation.md.tmpl",
        "automation_implementation",
    ),
    "release-scope": ("artifacts/release-scope.md.tmpl", "release_scope"),
}


def default_artifact_id(artifact_type: str, destination: Path) -> str:
    return f"{artifact_type}:{destination.stem}"


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def register_artifact(
    state_path: Path,
    artifact_id: str,
    artifact_type: str,
    destination: Path,
    producer_phase: str,
    source_artifacts: list[str],
    evidence: list[str],
    validation_status: str,
) -> bool:
    state = load_state(state_path)
    if state is None:
        return False

    artifacts = state.setdefault("artifacts", [])
    record = {
        "id": artifact_id,
        "type": artifact_type,
        "path": str(destination),
        "producer_phase": producer_phase,
        "source_artifacts": source_artifacts,
        "evidence": evidence,
        "validation": {"status": validation_status},
    }

    for index, existing in enumerate(artifacts):
        if existing.get("id") == artifact_id:
            artifacts[index] = record
            break
    else:
        artifacts.append(record)

    with state_path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return True


def create_artifact_from_template(
    *,
    root: Path,
    run_id: str,
    template: str,
    destination: Path,
    producer_phase: str,
    artifact_id: str | None = None,
    source_artifacts: list[str] | None = None,
    evidence: list[str] | None = None,
    validation_status: str = "pending",
    overwrite: bool = False,
    templates_root: Path | None = None,
    runs_root: Path | None = None,
    allow_external_destination: bool = False,
    register_state: bool = True,
) -> tuple[Path, bool]:
    """Create a managed artifact using an explicit repository root.

    This is the reusable API used by the generic lifecycle facade.  The CLI
    wrapper below retains the legacy path-resolution behavior.
    """
    root = root.resolve()
    template_file, artifact_type = TEMPLATES[template]
    templates_root = (templates_root or root / "templates").resolve()
    template_path = templates_root / template_file
    if not template_path.exists():
        raise FileNotFoundError(f"template not found: {template_path}")
    destination = destination if destination.is_absolute() else root / destination
    if not allow_external_destination:
        try:
            destination.resolve().relative_to((root / "outputs").resolve())
        except ValueError as exc:
            raise ValueError(
                f"managed artifact destination must be under outputs/: {destination}"
            ) from exc
    if destination.exists() and not overwrite:
        raise FileExistsError(f"destination exists: {destination}")
    source_artifacts = source_artifacts or []
    evidence = evidence or []
    artifact_id = artifact_id or default_artifact_id(artifact_type, destination)
    content = template_path.read_text(encoding="utf-8")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")

    registered = False
    if register_state:
        state_path = (runs_root or root / "runs") / run_id / "state.json"
        registered = register_artifact(
            state_path=state_path,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            destination=Path(as_logical_path(destination, root=root)),
            producer_phase=producer_phase,
            source_artifacts=source_artifacts,
            evidence=evidence,
            validation_status=validation_status,
        )
    return destination, registered


def create_artifact(args: argparse.Namespace) -> tuple[Path, bool]:
    if getattr(args, "allow_external_destination_for_tests", False):
        destination = resolve_repo_path(args.destination)
        root = destination.parent
        while root.parent != root and root.name != "outputs":
            root = root.parent
        root = root.parent if root.name == "outputs" else AGENT_NEXT_ROOT
    else:
        destination = resolve_managed_repo_path(args.destination, "outputs")
        root = AGENT_NEXT_ROOT
    return create_artifact_from_template(
        root=root,
        run_id=args.run_id,
        template=args.template,
        destination=destination,
        producer_phase=args.producer_phase,
        artifact_id=args.artifact_id,
        source_artifacts=args.source_artifact,
        evidence=args.evidence,
        validation_status=args.validation_status,
        overwrite=args.overwrite,
        templates_root=resolve_repo_path(args.templates_root),
        runs_root=resolve_repo_path(args.runs_root),
        allow_external_destination=getattr(args, "allow_external_destination_for_tests", False),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--templates-root", type=Path, default=DEFAULT_TEMPLATES_ROOT)
    parser.add_argument("--template", choices=sorted(TEMPLATES), required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--producer-phase", required=True)
    parser.add_argument("--artifact-id")
    parser.add_argument("--source-artifact", action="append", default=[])
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--validation-status", default="pending")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    path, registered = create_artifact(parse_args())
    print(path)
    if not registered:
        print("state not found; artifact was not registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
