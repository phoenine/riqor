---
name: requirement-analysis
description: Read PRDs, requirement sources, feature descriptions, bug context, release inputs, and repository evidence to produce testable requirement specifications and intake summaries.
---

# requirement-analysis

Use this skill for requirement and context intake. Keep it focused on source
understanding and requirement specification; route test design to other skills.

## Required Reading

- `workflows/index.md`
- Current workflow file selected by `agent-next`
- `workflows/stage-gates.md`
- `references/intake-sources.md` when the task starts from Feishu/Lark, ZenTao,
  GitLab MR, bug context, or mixed external sources.
- `references/multi-source-change-analysis.md` when one feature, bug, or
  release scope spans multiple repositories, MRs, commits, services, or source
  systems.
- Relevant files under `knowledge/`

## Inputs

- PRD or project-selected document source.
- Requirement, task, bug, or version context from a selected integration Skill.
- User-provided feature, bug, or release scope.
- Repository evidence from Project Profile product repositories when code context is
  required.

## Outputs

- Requirement specification or intake summary.
- Requirement Spec artifact ID plus stable Atomic Requirement IDs.
- Open questions and missing inputs.
- Knowledge-used log.
- Knowledge update proposal and explicit user confirmation prompt when reusable
  terms, view rules, calculation rules, or workflow knowledge are missing or
  changed.
- Source-read or repository-evidence log when code was inspected.

## Source Fidelity

Keep normative requirements separate from test-design derivations and
implementation observations.

- `source_explicit`: the behavior is stated by an authoritative requirement
  source. Cite the exact document, section, record, or message.
- `user_confirmed`: the user or another authorized decision maker explicitly
  resolved or added the behavior. Cite the confirmation.
- `assumption`: the behavior is not established by an authoritative source.
  Keep it `pending`, link it to an open question, and do not present it as a
  confirmed requirement.
- Code, configuration, logs, and runtime observations are implementation
  evidence. They may support a requirement or expose a difference, but they do
  not become normative product requirements without an authoritative source or
  explicit confirmation.
- Boundaries, combinations, negative paths, and other coverage ideas derived by
  test analysis belong in Risk Analysis or Test Points. Do not merge them into
  a source requirement unless the source actually specifies the behavior.

For every Atomic Requirement, record `依据类型`, `确认状态`, and an exact
`来源定位`. Put source-versus-implementation conflicts in `实现差异 / 待确认设计点`.
Do not synthesize conflicting sources into one apparently confirmed statement.

## Atomic Requirements

A Requirement Spec is one artifact for the active Feature or scope. Inside it,
create as many Atomic Requirements as needed; never force one upstream feature
record such as `F-SYS` into one `REQ`.

An Atomic Requirement describes one independently judgeable obligation or
observable outcome. Split requirements when behaviors have different triggers,
actors, states, branches, outcomes, source locations, or confirmation status,
or when one behavior could pass while another fails. Do not split individual
test values or equivalent examples into requirements; those belong in Test
Points and Test Cases.

Use consecutive IDs such as `REQ-001`, `REQ-002`, and `REQ-003`. Preserve the
upstream Feature ID in `来源定位` and the traceability table. Do not use nested
IDs such as `REQ-001-01`, because downstream parsers and coverage records use
the standard `REQ-###` reference form.

Before completing the artifact, verify:

- Every Atomic Requirement has one primary statement, basis type, confirmation
  status, exact source locator, priority, and independently judgeable acceptance
  criterion.
- Every authoritative source rule is mapped to an Atomic Requirement or listed
  explicitly as out of scope, conflicting, or pending.
- Every downstream Risk and Test Point references the applicable Atomic
  Requirement IDs rather than only the Requirement Spec artifact ID.
- A confirmed requirement is based on `source_explicit` or `user_confirmed`,
  never on `assumption` alone.

## Artifact Workflow

Create requirement specifications from template (never blank Markdown):

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template requirement-spec \
  --producer-phase "Requirement Specification" \
  --artifact-id REQ-SPEC-001 \
  --destination <artifact-root>/<scope>/requirements/<feature>-requirement-spec.md
```

Validate before completing the phase:

```bash
python3 tools/validate_artifact.py \
  --artifact-file <artifact-root>/<scope>/requirements/<feature>-requirement-spec.md \
  --artifact-type requirement_spec \
  --artifact-id REQ-SPEC-001
```

## Do Not

- Do not invent missing business rules.
- Do not combine source facts, implementation behavior, test-design derivations,
  and assumptions into one requirement statement.
- Do not group independently judgeable behaviors into one coarse requirement.
- Do not write test points or test cases.
- Do not update shared knowledge without a proposed update and confirmation.
- Do not treat knowledge as source evidence.

## Knowledge Update Prompt

When a requirement specification identifies reusable domain knowledge that is
missing from `knowledge/`, or existing knowledge whose meaning changed:

1. Mark the affected terms or rules in the requirement artifact, for example in
   `领域术语` or `待确认问题`.
2. Record a `knowledge_proposed_updates[]` entry in run state with target path,
   summary, and `status=proposed`.
3. In the final response for the Requirement Specification phase, explicitly ask
   the user to choose between confirming only the requirement and confirming the
   requirement plus the listed knowledge proposals.
4. Record structured candidates with `agent-next record --knowledge-proposal`.
   Requirement Gate success alone must leave them as `proposed`.
5. Only after the combined choice explicitly includes knowledge, use
   `agent-next knowledge --confirm --source-artifact <requirement-id>`.
6. Do not silently overwrite an existing knowledge page; it requires a separate
   content review.
