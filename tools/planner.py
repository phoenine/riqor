from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import ContractError, load_yaml, validate_capability
from .inventory import InventoryReport
from .phases import CANONICAL_PHASES, normalize_phase, phase_validation_error


@dataclass(frozen=True)
class CapabilityRecord:
    path: Path
    metadata: dict[str, Any]

    @property
    def capability_id(self) -> str:
        return str(self.metadata["id"])


@dataclass
class CapabilityRegistry:
    workflow: str = ""
    records: list[CapabilityRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class PlanStep:
    capability_id: str
    title: str
    workflow: str
    phase: str
    skill: str
    produces: tuple[str, ...]
    required: tuple[str, ...]
    optional_available: tuple[str, ...]
    optional_missing: tuple[str, ...]
    reason: str
    side_effect: bool
    action_class: str


@dataclass
class PlanReport:
    goal: str
    scope_id: str
    available_inputs: list[str] = field(default_factory=list)
    steps: list[PlanStep] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.blockers


@dataclass
class _PlanningState:
    selected: list[CapabilityRecord]
    available_types: set[str]

    def clone(self) -> _PlanningState:
        return _PlanningState(list(self.selected), set(self.available_types))


def load_capabilities(root: Path, workflow: str | None = None) -> CapabilityRegistry:
    root = root.resolve()
    registry = CapabilityRegistry()
    workflows_root = root / "workflows"
    if workflow is not None:
        if Path(workflow).name != workflow or workflow in {"", ".", ".."}:
            registry.errors.append(f"invalid workflow id: {workflow}")
            return registry
        search_root = workflows_root / workflow
        if not search_root.is_dir():
            registry.errors.append(f"workflow pack does not exist: {workflow}")
            return registry
        registry.workflow = workflow
    else:
        packs = sorted(
            path
            for path in workflows_root.iterdir()
            if path.is_dir() and any(path.glob("capabilities/*.yaml"))
        ) if workflows_root.is_dir() else []
        if len(packs) > 1:
            names = ", ".join(path.name for path in packs)
            registry.errors.append(
                f"multiple workflow packs found; select one of: {names}"
            )
            return registry
        if not packs:
            registry.errors.append("no workflow capabilities found")
            return registry
        search_root = packs[0]
        registry.workflow = search_root.name

    records_by_id: dict[str, CapabilityRecord] = {}
    for path in sorted(search_root.glob("capabilities/*.yaml")):
        relative_path = path.relative_to(root)
        try:
            capability = load_yaml(path)
        except ContractError as exc:
            registry.errors.append(str(exc))
            continue
        capability_errors = validate_capability(capability)
        if not capability_errors:
            phase_error = phase_validation_error(
                str(capability["workflow"]), str(capability["phase"])
            )
            if phase_error:
                capability_errors.append(f"phase {phase_error}")
            skill_path = root / "skills" / str(capability["skill"]) / "SKILL.md"
            if not skill_path.is_file():
                capability_errors.append(
                    f"skill does not exist: skills/{capability['skill']}/SKILL.md"
                )
        if capability_errors:
            registry.errors.extend(
                f"{relative_path}: {error}" for error in capability_errors
            )
            continue
        capability_id = capability["id"]
        if capability_id in records_by_id:
            first = records_by_id[capability_id].path
            registry.errors.append(
                f"duplicate capability id {capability_id}: {first} and {relative_path}"
            )
            continue
        record = CapabilityRecord(path=relative_path, metadata=capability)
        records_by_id[capability_id] = record
        registry.records.append(record)
    if not registry.records and not registry.errors:
        registry.errors.append(f"no capabilities found in workflow pack {registry.workflow}")
    return registry


def build_plan(
    *,
    goal: str,
    scope_id: str,
    inventory: InventoryReport,
    registry: CapabilityRegistry,
) -> PlanReport:
    report = PlanReport(goal=goal, scope_id=scope_id)
    if inventory.errors:
        report.blockers.extend(f"inventory: {error}" for error in inventory.errors)
        return report
    if registry.errors:
        report.blockers.extend(f"capability registry: {error}" for error in registry.errors)
        return report

    scope_records = [
        record for record in inventory.records if record.scope_id == scope_id
    ]
    ready_types = {
        record.artifact_type
        for record in scope_records
        if record.effective_status == "ready"
    }
    report.available_inputs = sorted(ready_types)
    producers: dict[str, list[CapabilityRecord]] = {}
    for capability in registry.records:
        for artifact_type in capability.metadata["produces"]:
            producers.setdefault(artifact_type, []).append(capability)

    def resolve(
        artifact_type: str,
        state: _PlanningState,
        stack: tuple[str, ...],
    ) -> list[str]:
        if artifact_type in state.available_types:
            return []
        if artifact_type in stack:
            return ["capability dependency cycle: " + " -> ".join((*stack, artifact_type))]
        candidates = producers.get(artifact_type, [])
        if not candidates:
            return [
                f"missing external input {artifact_type} for scope {scope_id}; "
                "no capability produces it"
            ]
        if len(candidates) > 1:
            names = ", ".join(sorted(item.capability_id for item in candidates))
            return [f"multiple capabilities produce {artifact_type}: {names}"]
        capability = candidates[0]
        next_stack = (*stack, artifact_type)
        requires = capability.metadata.get("requires", {})
        for required_type in requires.get("all", []):
            blockers = resolve(required_type, state, next_stack)
            if blockers:
                return blockers

        any_types = requires.get("any", [])
        if any_types and not (set(any_types) & state.available_types):
            successful_states: list[_PlanningState] = []
            alternative_blockers: list[str] = []
            for alternative in any_types:
                trial = state.clone()
                blockers = resolve(alternative, trial, next_stack)
                if blockers:
                    alternative_blockers.extend(blockers)
                else:
                    successful_states.append(trial)
            if not successful_states:
                options = ", ".join(any_types)
                details = "; ".join(dict.fromkeys(alternative_blockers))
                return [f"none of the alternative inputs are available ({options}): {details}"]
            best = min(successful_states, key=lambda item: len(item.selected))
            state.selected = best.selected
            state.available_types = best.available_types

        if capability.capability_id not in {
            item.capability_id for item in state.selected
        }:
            state.selected.append(capability)
        state.available_types.update(capability.metadata["produces"])
        return []

    state = _PlanningState(selected=[], available_types=set(ready_types))
    report.blockers.extend(resolve(goal, state, ()))
    if report.blockers:
        return report

    if state.selected:
        phases = CANONICAL_PHASES.get(registry.workflow, ())
        first_selected_phase = min(
            phases.index(normalize_phase(str(item.metadata["phase"]), registry.workflow))
            for item in state.selected
        )
        phase_prerequisites = [
            item
            for item in registry.records
            if not item.metadata["produces"]
            and phases.index(normalize_phase(str(item.metadata["phase"]), registry.workflow))
            < first_selected_phase
        ]
        state.selected = [*phase_prerequisites, *state.selected]

    available = set(ready_types)
    for capability in state.selected:
        metadata = capability.metadata
        outputs = tuple(metadata["produces"])
        existing = {
            record.artifact_type: record.effective_status
            for record in scope_records
            if record.artifact_type in outputs
        }
        non_ready = {
            artifact_type: status
            for artifact_type, status in existing.items()
            if status != "ready"
        }
        missing_outputs = [item for item in outputs if item not in existing]
        reason_parts: list[str] = []
        if non_ready:
            reason_parts.append("regenerate " + ", ".join(
                f"{artifact_type} ({status})"
                for artifact_type, status in sorted(non_ready.items())
            ))
        if missing_outputs:
            reason_parts.append("produce missing " + ", ".join(missing_outputs))
        reason = "; ".join(reason_parts) or "complete phase prerequisite"
        required = tuple(metadata.get("requires", {}).get("all", []))
        optional = tuple(metadata.get("optional", []))
        report.steps.append(
            PlanStep(
                capability_id=capability.capability_id,
                title=str(metadata["title"]),
                workflow=str(metadata["workflow"]),
                phase=str(metadata["phase"]),
                skill=str(metadata["skill"]),
                produces=outputs,
                required=required,
                optional_available=tuple(item for item in optional if item in available),
                optional_missing=tuple(item for item in optional if item not in available),
                reason=reason,
                side_effect=bool(metadata["side_effect"]),
                action_class=str(metadata["action_class"]),
            )
        )
        available.update(outputs)
    return report
