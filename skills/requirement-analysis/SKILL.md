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
- Requirement ID or local requirement handle.
- Open questions and missing inputs.
- Knowledge-used log.
- Knowledge update proposal and explicit user confirmation prompt when reusable
  terms, view rules, calculation rules, or workflow knowledge are missing or
  changed.
- Source-read or repository-evidence log when code was inspected.

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
