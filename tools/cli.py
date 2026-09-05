from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .artifacts import (
    ArtifactActionError,
    attach_artifact_inputs,
    gate_artifact,
    scaffold_artifact,
)
from .automation_prepare import (
    AutomationPrepareError,
    prepare_api_automation,
    render_automation_implementation,
    select_automation_inputs,
)
from .automation_provider import consumer_dependency
from .bootstrap import InitError, init_project
from .contracts import ContractError, load_yaml, validate_project_profile
from .doctor import run_doctor
from .environment import (
    ENV_GROUPS,
    EnvironmentFileError,
    environment_group_status,
    load_project_environment,
)
from .inventory import load_inventory
from .knowledge import KnowledgeError, confirm_proposals, pending_proposals
from .lifecycle import (
    LifecycleError,
    explain_run,
    gate_run,
    load_run,
    prepare_run,
    record_run_evidence,
    run_status,
)
from .planner import build_plan, load_capabilities
from .registration import RegistrationError, register_existing_artifact


def _project_profile(root: Path, project_file: Path) -> tuple[dict | None, list[str]]:
    if not project_file.is_absolute():
        project_file = root / project_file
    try:
        profile = load_yaml(project_file.resolve())
    except ContractError as exc:
        return None, [str(exc)]
    errors = validate_project_profile(profile)
    return (profile if not errors else None), errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-next")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="validate a project and local contracts")
    doctor.add_argument("--project", required=True, type=Path)
    doctor.add_argument("--root", type=Path, default=Path.cwd())

    environment = subparsers.add_parser(
        "env", help="show configured environment variables without values"
    )
    environment.add_argument("--group", choices=sorted(ENV_GROUPS))
    environment.add_argument("--root", type=Path, default=Path.cwd())

    initialize = subparsers.add_parser(
        "init", help="create a project and optional context storage"
    )
    initialize.add_argument("--project-id", required=True)
    initialize.add_argument("--name", required=True)
    initialize.add_argument("--track", action="append", dest="tracks")
    initialize.add_argument("--default-track")
    initialize.add_argument("--source", action="append", type=Path, default=[])
    initialize.add_argument(
        "--automation",
        action="append",
        default=[],
        help="configure a declared automation preset, such as api (repeatable)",
    )
    initialize.add_argument("--root", type=Path, default=Path.cwd())

    prepare_automation = subparsers.add_parser(
        "prepare-automation",
        help="prepare a Profile-selected automation project for eligible classified cases",
    )
    prepare_automation.add_argument("--project", required=True, type=Path)
    prepare_automation.add_argument("--classification-artifact", required=True)
    prepare_automation.add_argument("--test-cases-artifact", required=True)
    prepare_automation.add_argument("--implementation-artifact", required=True)
    prepare_automation.add_argument("--run-id", required=True)
    prepare_automation.add_argument("--workflow", default="feature-quality")
    prepare_automation.add_argument("--capability", default="automation-prepare")
    prepare_automation.add_argument("--repository-id")
    prepare_automation.add_argument(
        "--no-install",
        action="store_true",
        help="create or verify the consumer project without resolving dependencies",
    )
    prepare_automation.add_argument("--root", type=Path, default=Path.cwd())

    inventory = subparsers.add_parser("inventory", help="inspect current artifacts")
    inventory.add_argument("--project", required=True, type=Path)
    inventory.add_argument("--scope")
    inventory.add_argument("--root", type=Path, default=Path.cwd())

    register = subparsers.add_parser(
        "register", help="register an existing local source file as an artifact"
    )
    register.add_argument("--project", required=True, type=Path)
    register.add_argument("--artifact-id", required=True)
    register.add_argument("--type", required=True, dest="artifact_type")
    register.add_argument("--scope", required=True)
    register.add_argument("--content", required=True, type=Path)
    register.add_argument("--source-artifact", action="append", default=[])
    register.add_argument("--track", action="append", dest="tracks")
    register.add_argument(
        "--ready",
        action="store_true",
        help="explicitly mark the registered input ready for downstream planning",
    )
    register.add_argument("--run-id", help="registry run id; defaults to import-<project-id>")
    register.add_argument("--root", type=Path, default=Path.cwd())

    plan = subparsers.add_parser("plan", help="plan dependencies for an artifact goal")
    plan.add_argument("--project", required=True, type=Path)
    plan.add_argument("--scope", required=True)
    plan.add_argument("--goal", required=True)
    plan.add_argument("--workflow")
    plan.add_argument("--root", type=Path, default=Path.cwd())

    run = subparsers.add_parser("run", help="prepare Run State for a capability")
    run.add_argument("--project", required=True, type=Path)
    run.add_argument("--workflow", required=True)
    run.add_argument("--capability", required=True)
    run.add_argument("--run-id", required=True)
    run.add_argument("--track", action="append", dest="tracks")
    run.add_argument("--root", type=Path, default=Path.cwd())

    scaffold = subparsers.add_parser("scaffold", help="create a draft artifact")
    scaffold.add_argument("--project", required=True, type=Path)
    scaffold.add_argument("--workflow", required=True)
    scaffold.add_argument("--capability", required=True)
    scaffold.add_argument("--scope", required=True)
    scaffold.add_argument("--artifact-id", required=True)
    scaffold.add_argument("--run-id", required=True)
    scaffold.add_argument("--source-artifact", action="append", default=[])
    scaffold.add_argument("--track", action="append", dest="tracks")
    scaffold.add_argument("--root", type=Path, default=Path.cwd())

    gate = subparsers.add_parser("gate", help="validate an artifact's local content")
    gate.add_argument("--project", required=True, type=Path)
    gate.add_argument("--artifact-id")
    gate.add_argument("--run-id")
    gate.add_argument("--mark-ready", action="store_true")
    gate.add_argument("--root", type=Path, default=Path.cwd())

    record = subparsers.add_parser("record", help="record local phase evidence for a run")
    record.add_argument("--run-id", required=True)
    record.add_argument("--knowledge-used", action="append", default=[])
    record.add_argument("--knowledge-plan-status")
    record.add_argument("--knowledge-plan-summary")
    record.add_argument("--knowledge-plan-evidence", action="append", default=[])
    record.add_argument("--knowledge-proposal", action="append", type=Path, default=[])
    record.add_argument(
        "--repository",
        action="append",
        default=[],
        help="kind=dev,name=repo,path=repositories/dev/repo[,commit=...]",
    )
    record.add_argument(
        "--repository-evidence",
        action="append",
        default=[],
        help="repo=name,evidence_type=file,reference=path[,supports=id]",
    )
    record.add_argument("--required-env", action="append", default=[])
    record.add_argument("--checked-env", action="append", default=[])
    record.add_argument("--target")
    record.add_argument(
        "--confirmation",
        action="append",
        default=[],
        help="id=...,action=...,status=required|confirmed|rejected|not_required",
    )
    record.add_argument(
        "--trace",
        action="append",
        default=[],
        help="from=REQ-001,to=RISK-001,relation=mitigated_by",
    )
    record.add_argument("--note", action="append", default=[])
    record.add_argument("--root", type=Path, default=Path.cwd())

    status = subparsers.add_parser("status", help="show Run State and current gate blockers")
    status.add_argument("--run-id", required=True)
    status.add_argument("--root", type=Path, default=Path.cwd())

    explain = subparsers.add_parser("explain", help="explain the selected workflow route")
    explain.add_argument("--run-id", required=True)
    explain.add_argument("--root", type=Path, default=Path.cwd())

    knowledge = subparsers.add_parser(
        "knowledge", help="preview or confirm reusable knowledge proposals"
    )
    knowledge.add_argument("--project", required=True, type=Path)
    knowledge.add_argument("--run-id", required=True)
    knowledge.add_argument("--source-artifact")
    knowledge.add_argument("--confirm", action="store_true")
    knowledge.add_argument("--confirmed-by", default="user")
    knowledge.add_argument("--root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        load_project_environment(root)
    except EnvironmentFileError as exc:
        print(f"ERROR {exc}")
        return 1
    if args.command == "env":
        groups = [args.group] if args.group else sorted(ENV_GROUPS)
        for group in groups:
            configured = 0
            for name, is_set in environment_group_status(group):
                configured += int(is_set)
                print(f"{'SET' if is_set else 'EMPTY'} {name}")
            print(f"GROUP {group} configured={configured}/{len(ENV_GROUPS[group])}")
        return 0
    if args.command == "init":
        tracks = args.tracks or ["default"]
        default_track = args.default_track or tracks[0]
        try:
            result = init_project(
                root=root,
                project_id=args.project_id,
                name=args.name,
                tracks=tracks,
                default_track=default_track,
                sources=args.source,
                automations=args.automation,
            )
        except InitError as exc:
            print(f"ERROR {exc}")
            return 1
        print(f"OK created project profile {result.profile_path}")
        print(f"OK initialized optional project context {result.knowledge_root}")
        print(f"OK registered sources {result.source_count}")
        if args.automation:
            print("OK configured automation " + ", ".join(args.automation))
        return 0
    if args.command in {"status", "explain", "record"}:
        root = args.root.resolve()
        try:
            if args.command == "record":
                path = record_run_evidence(
                    root=root,
                    run_id=args.run_id,
                    knowledge_used=args.knowledge_used,
                    knowledge_plan_status=args.knowledge_plan_status,
                    knowledge_plan_summary=args.knowledge_plan_summary,
                    knowledge_plan_evidence=args.knowledge_plan_evidence,
                    notes=args.note,
                    knowledge_proposal_files=args.knowledge_proposal,
                    repositories=args.repository,
                    repository_evidence=args.repository_evidence,
                    required_environment=args.required_env,
                    checked_environment=args.checked_env,
                    environment_target=args.target,
                    confirmations=args.confirmation,
                    traceability=args.trace,
                )
                print(f"OK recorded evidence {path.relative_to(root)}")
                return 0
            if args.command == "status":
                state, blockers = run_status(root, args.run_id)
                print(
                    f"RUN {args.run_id} project={state.get('project_id')} "
                    f"tracks={','.join(state.get('tracks', []))} "
                    f"entry={state.get('entry')} phase={state.get('phase')}"
                )
                print(
                    f"ARTIFACTS {len(state.get('artifacts', []))} "
                    f"GATES {len(state.get('gate_results', []))}"
                )
                for blocker in blockers:
                    print(f"BLOCKED {blocker}")
                print(
                    "READY current phase gate can pass"
                    if not blockers
                    else f"BLOCKERS {len(blockers)}"
                )
                return 0 if not blockers else 1
            explanation = explain_run(root, args.run_id)
        except (LifecycleError, OSError, ValueError) as exc:
            print(f"ERROR {exc}")
            return 1
        print(
            f"ROUTE run={args.run_id} workflow={explanation['workflow']} "
            f"phase={explanation['phase']}"
        )
        print(f"PHASE_DOC {explanation['phase_doc']}")
        print("SKILLS " + ", ".join(explanation["required_skills"]))
        for artifact in explanation["artifacts"]:
            print(
                f"ARTIFACT {artifact.get('id')} type={artifact.get('type')} "
                f"path={artifact.get('path')}"
            )
        for blocker in explanation["blockers"]:
            print(f"BLOCKED {blocker}")
        return 0
    if args.command == "knowledge":
        profile, profile_errors = _project_profile(root, args.project)
        if profile_errors:
            for error in profile_errors:
                print(f"ERROR project profile: {error}")
            return 1
        assert profile is not None
        try:
            _path, state = load_run(root, args.run_id)
            proposals = pending_proposals(state, args.source_artifact)
            if not args.confirm:
                for proposal in proposals:
                    print(
                        f"PROPOSED {proposal['path']} type={proposal.get('type', 'unknown')} "
                        f"source={proposal.get('source_artifact', 'unknown')}"
                    )
                print(f"OK pending knowledge proposals {len(proposals)}")
                return 0
            if not args.source_artifact:
                print("BLOCKED --confirm requires --source-artifact")
                return 1
            written = confirm_proposals(
                root=root,
                profile=profile,
                run_id=args.run_id,
                source_artifact=args.source_artifact,
                confirmed_by=args.confirmed_by,
            )
        except (KnowledgeError, LifecycleError) as exc:
            print(f"BLOCKED {exc}")
            return 1
        for path in written:
            print(f"OK confirmed knowledge {path}")
        return 0
    if args.command == "prepare-automation":
        profile, profile_errors = _project_profile(root, args.project)
        if profile_errors:
            for error in profile_errors:
                print(f"ERROR project profile: {error}")
            return 1
        assert profile is not None
        try:
            selection = select_automation_inputs(
                root=root,
                profile=profile,
                classification_artifact_id=args.classification_artifact,
                test_cases_artifact_id=args.test_cases_artifact,
                repository_id=args.repository_id,
            )
            registry = load_capabilities(root, workflow=args.workflow)
            if registry.errors:
                raise AutomationPrepareError(
                    "invalid capability registry: " + "; ".join(registry.errors)
                )
            capability = next(
                (
                    item
                    for item in registry.records
                    if item.capability_id == args.capability
                ),
                None,
            )
            if capability is None:
                raise AutomationPrepareError(
                    f"capability {args.capability} does not exist in workflow {args.workflow}"
                )
            tracks = list(selection.classification.metadata["tracks"])
            prepare_run(
                root=root,
                profile=profile,
                capability=capability,
                run_id=args.run_id,
                tracks=tracks,
            )
            attach_artifact_inputs(
                root=root,
                run_id=args.run_id,
                records=selection.run_inputs,
            )
            result = prepare_api_automation(
                root=root,
                selection=selection,
                install=not args.no_install,
            )
            if result.status == "skipped":
                record_run_evidence(
                    root=root,
                    run_id=args.run_id,
                    knowledge_used=[],
                    knowledge_plan_status=None,
                    knowledge_plan_summary=None,
                    knowledge_plan_evidence=[],
                    notes=[
                        "optional_skip:Optional Case Sync Or Generation:"
                        "no eligible A0/A1 API or hybrid cases"
                    ],
                )
                print("SKIPPED no A0/A1 api or hybrid cases")
                return 0
            classification_reference = (
                f"{selection.classification.artifact_id}@{selection.classification.revision}"
            )
            test_cases_reference = (
                f"{selection.test_cases.artifact_id}@{selection.test_cases.revision}"
            )
            source_references = [test_cases_reference, classification_reference]
            current_inventory = load_inventory(root, profile)
            existing = next(
                (
                    item
                    for item in current_inventory.records
                    if item.artifact_id == args.implementation_artifact
                ),
                None,
            )
            if existing is not None:
                if (
                    existing.artifact_type != "automation_implementation"
                    or existing.scope_id != selection.classification.scope_id
                    or existing.metadata["source_artifacts"] != source_references
                ):
                    raise AutomationPrepareError(
                        "existing implementation artifact does not match current inputs"
                    )
                print(
                    f"OK automation project {result.status} "
                    f"{result.destination.relative_to(root)}"
                )
                print(f"OK automation implementation reused {existing.path}")
                print("CASES " + ", ".join(result.eligible_cases))
                return 0
            scaffold = scaffold_artifact(
                root=root,
                profile=profile,
                capability=capability,
                scope_id=selection.classification.scope_id,
                artifact_id=args.implementation_artifact,
                source_references=source_references,
                tracks=tracks,
                run_id=args.run_id,
            )
            assert selection.repository is not None
            assert selection.provider is not None
            implementation = render_automation_implementation(
                project_id=profile["project"]["id"],
                repository_id=str(selection.repository["id"]),
                runtime_dependency=consumer_dependency(selection.provider),
                result=result,
                classification_reference=classification_reference,
                test_cases_reference=test_cases_reference,
                installed=not args.no_install,
            )
            (root / scaffold.content_path).write_text(implementation, encoding="utf-8")
        except (AutomationPrepareError, ArtifactActionError, LifecycleError, OSError) as exc:
            print(f"BLOCKED {exc}")
            return 1
        assert result.destination is not None
        print(
            f"OK automation project {result.status} "
            f"{result.destination.relative_to(root)}"
        )
        print(f"OK created automation implementation {scaffold.content_path}")
        print("STATUS draft; review and gate the implementation artifact")
        print("CASES " + ", ".join(result.eligible_cases))
        return 0
    if args.command in {"inventory", "register", "plan", "run", "scaffold", "gate"}:
        root = args.root.resolve()
        profile, profile_errors = _project_profile(root, args.project)
        if profile_errors:
            for error in profile_errors:
                print(f"ERROR project profile: {error}")
            return 1
        assert profile is not None
        inventory_report = load_inventory(root, profile)
        if args.command == "inventory":
            records = inventory_report.records
            if args.scope:
                records = [record for record in records if record.scope_id == args.scope]
            for record in records:
                print(
                    f"{record.effective_status.upper()} {record.artifact_id} "
                    f"type={record.artifact_type} scope={record.scope_id} "
                    f"revision={record.revision} path={record.path}"
                )
                for reason in record.reasons:
                    print(f"  REASON {reason}")
            for error in inventory_report.errors:
                print(f"ERROR {error}")
            print(f"OK artifacts {len(records)}")
            return 0 if inventory_report.ok else 1

        if args.command == "register":
            tracks = args.tracks or [
                profile["project"].get("default_track")
                or profile["project"]["tracks"][0]
            ]
            try:
                result = register_existing_artifact(
                    root=root,
                    profile=profile,
                    artifact_id=args.artifact_id,
                    artifact_type=args.artifact_type,
                    scope_id=args.scope,
                    content_path=args.content,
                    tracks=tracks,
                    source_artifacts=args.source_artifact,
                    ready=args.ready,
                    run_id=args.run_id,
                )
            except RegistrationError as exc:
                print(f"BLOCKED {exc}")
                return 1
            print(f"OK registered artifact {args.artifact_id} record {result.manifest_path}")
            print(
                "STATUS ready"
                if args.ready
                else "STATUS draft; use gate --artifact-id ... --mark-ready after review"
            )
            return 0

        if args.command == "gate":
            if not args.artifact_id:
                if not args.run_id:
                    print("BLOCKED gate requires --run-id when --artifact-id is omitted")
                    return 1
                try:
                    errors = gate_run(root, args.run_id)
                except LifecycleError as exc:
                    print(f"BLOCKED {exc}")
                    return 1
                for error in errors:
                    print(f"BLOCKED {error}")
                if not errors:
                    print("OK current phase passed")
                return 0 if not errors else 1
            result = gate_artifact(
                root=root,
                profile=profile,
                artifact_id=args.artifact_id,
                mark_ready=args.mark_ready,
                run_id=args.run_id,
            )
            for error in result.errors:
                print(f"BLOCKED {error}")
            if result.passed:
                action = "marked ready" if result.marked_ready else "passed"
                print(f"OK artifact {result.artifact_id} {action}")
                if result.marked_ready and args.run_id:
                    try:
                        _path, state = load_run(root, args.run_id)
                    except LifecycleError:
                        state = {}
                    proposals = pending_proposals(state, result.artifact_id)
                    if proposals:
                        print(
                            f"KNOWLEDGE {len(proposals)} proposal(s) remain proposed; "
                            "confirm the requirement only, or preview and explicitly "
                            "confirm knowledge with `agent-next knowledge`"
                        )
            return 0 if result.passed else 1

        registry = load_capabilities(root, workflow=args.workflow)
        if args.command in {"run", "scaffold"}:
            if registry.errors:
                for error in registry.errors:
                    print(f"ERROR capability registry: {error}")
                return 1
            capability = next(
                (
                    item
                    for item in registry.records
                    if item.capability_id == args.capability
                ),
                None,
            )
            if capability is None:
                print(
                    f"ERROR capability {args.capability} does not exist in "
                    f"workflow {registry.workflow}"
                )
                return 1
            tracks = args.tracks or [
                profile["project"].get("default_track")
                or profile["project"]["tracks"][0]
            ]
            try:
                prepared = prepare_run(
                    root=root,
                    profile=profile,
                    capability=capability,
                    run_id=args.run_id,
                    tracks=tracks,
                )
            except LifecycleError as exc:
                print(f"BLOCKED {exc}")
                return 1
            if args.command == "run":
                print(f"OK prepared run state {prepared.state_path}")
                print(
                    f"ROUTE entry={prepared.state['entry']} phase={prepared.state['phase']} "
                    f"skill={capability.metadata['skill']}"
                )
                return 0
            try:
                result = scaffold_artifact(
                    root=root,
                    profile=profile,
                    capability=capability,
                    scope_id=args.scope,
                    artifact_id=args.artifact_id,
                    source_references=args.source_artifact,
                    tracks=tracks,
                    run_id=args.run_id,
                )
            except ArtifactActionError as exc:
                print(f"BLOCKED {exc}")
                return 1
            print(f"OK created artifact record {result.manifest_path}")
            print(f"OK created artifact content {result.content_path}")
            return 0

        plan_report = build_plan(
            goal=args.goal,
            scope_id=args.scope,
            inventory=inventory_report,
            registry=registry,
        )
        workflow_label = registry.workflow or args.workflow or "unresolved"
        print(
            f"PLAN goal={plan_report.goal} scope={plan_report.scope_id} "
            f"workflow={workflow_label}"
        )
        if plan_report.available_inputs:
            print("AVAILABLE " + ", ".join(plan_report.available_inputs))
        for position, step in enumerate(plan_report.steps, start=1):
            side_effect = f" side_effect={step.action_class}" if step.side_effect else ""
            outputs = ", ".join(step.produces) or "(phase gate)"
            print(
                f"{position}. {step.capability_id} -> {outputs} "
                f"phase={step.phase!r} skill={step.skill} "
                f"reason={step.reason}{side_effect}"
            )
            if step.optional_missing:
                print("   OPTIONAL MISSING " + ", ".join(step.optional_missing))
        for blocker in plan_report.blockers:
            print(f"BLOCKED {blocker}")
        if plan_report.ready and not plan_report.steps:
            print(f"READY {plan_report.goal} already available")
        return 0 if plan_report.ready else 1
    if args.command == "doctor":
        root = args.root.resolve()
        project_file = args.project
        if not project_file.is_absolute():
            project_file = root / project_file
        report = run_doctor(project_file.resolve(), root)
        for check in report.checks:
            print(f"OK {check}")
        for error in report.errors:
            print(f"ERROR {error}")
        return 0 if report.ok else 1
    raise AssertionError(f"unhandled command: {args.command}")
