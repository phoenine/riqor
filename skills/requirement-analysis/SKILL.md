---
name: requirement-analysis
description: Read PRDs, requirement sources, feature descriptions, bug context, release inputs, and repository evidence to produce testable requirement specifications and intake summaries.
---

# requirement-analysis

Use this skill for requirement and context intake. Keep it focused on source
understanding and requirement specification; route test design to other skills.

## Phase Context

Use the route and blockers already returned by `agent-next explain`; do not
reopen the workflow index, selected README, or full Stage Gate audit guide.
If no routed Run exists, return to `agent-next` to create one instead of
reconstructing routing context here.

Read only what the current task needs:

- For Feature Intake, Bug Intake, or release source collection, read
  [references/intake-sources.md](references/intake-sources.md) only when the
  input comes from external or mixed sources.
- For Requirement Specification, read
  [references/requirement-specification.md](references/requirement-specification.md)
  and `templates/artifacts/requirement-spec.md.tmpl`.
- Read
  [references/multi-source-change-analysis.md](references/multi-source-change-analysis.md)
  only when the scope spans multiple sources or repositories.
- Read [references/knowledge-proposals.md](references/knowledge-proposals.md)
  only when stable reusable knowledge is missing or changed.
- Read only relevant Project Profile knowledge pages.

## Responsibilities

- Separate normative source facts, implementation evidence, test-design
  derivations, and assumptions.
- Produce the current phase's intake summary or requirement specification, open
  questions, and source or repository-evidence log.
- Preserve stable Atomic Requirement IDs and exact source locations.
- Route risks and test design to their owning Skills.

## Boundaries

- Do not invent missing business rules or treat knowledge as current-task
  source evidence.
- Do not write test points or test cases.
- Do not update shared knowledge without a proposal and explicit confirmation.
