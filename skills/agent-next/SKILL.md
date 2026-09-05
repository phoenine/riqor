---
name: agent-next
description: Lightweight router for agent-next workflows. Use when any task involves agent-next feature testing, bug regression, release acceptance, workflow routing, run state, stage gates, local repositories, knowledge, or routing to project-selected downstream skills.
---

# agent-next

Mandatory router for `agent-next`. Declares downstream skills; does not write
test assets.

## Context Loading

Repo root = package root. Keep one copy of routing context in the conversation:

1. For a new run, read `workflows/index.md`, then only the Deliverable Routing
   section of the selected `workflows/<entry>/README.md`.
2. Create or update Run State, then use `agent-next explain --run-id <run-id>`
   for the current route, phase document, required Skills, artifacts, and blockers.
3. Read only the returned current phase document.
4. Use `agent-next gate --project <profile> --run-id <run-id>` for enforcement.
   Do not load `workflows/stage-gates.md` unless the user asks for a Gate audit.

```bash
python3 tools/phase_doc.py --entry <entry> --phase "<phase>"
```

Do not reopen the index or workflow README after Run State exists, and do not
read every `phases/*.md` file in one turn.

If no entrypoint applies, ask one short clarification before run state or artifacts.

## Routing

Choose exactly one entrypoint per `workflows/index.md`. Record
`state.workflow` as `workflows/<entry>/README.md`. Load only phase-required
skills from the skill index.

## Responsibilities

- Create or update run state under `runs/<run-id>/` with `tools/run_state.py`.
- Record `project_id`, `tracks`, `entry`, `workflow`, `phase`, `required_skills`,
  `loaded_skills`, and a `skill_receipts[]` entry per loaded skill.
- Declare repositories, knowledge, and environment groups for the current phase.
- Stop when `stage_gate.py` fails.

## Do Not

- Do not write requirement, test point, test case, acceptance, or report assets.
- Do not write external platforms, run automation, or mutate shared data, environments,
  repositories, or knowledge.
- Do not read the full workflow monolith or every `phases/*.md` in one turn.
- Do not navigate knowledge by wikilinks or filename guessing; use
  `related[].path`.

## Knowledge Loading

Start at the knowledge index declared by the Project Profile. For
operations, follow the profile-selected index. Follow `related[].path`. Record opened paths in `knowledge_used`.

## Confirmation Gates

Require explicit user confirmation immediately before remote writes, shared
environment execution, shared data or knowledge mutation, SSH, or deployment.

## Pitfalls

- **Bug Intake has no artifact** — only `notes[]` (`bug_intake:`, `bug_surface:`,
  etc.). Routing: `workflows/bug-regression/README.md` → Deliverable Routing.
- **No skip-ahead** — complete upstream phases before Execution or case-writing.
- **Read downstream references** before writing artifacts (e.g. `test-case-design`
  → `references/test-case-design-methodology.md`,
  `references/coverage-review-rules.md`, and
  `references/case-writing-rules.md`).
- **No remote repo mutation without confirmation** — no GitLab MR merge, force-push,
  branch checkout, or push in Project Profile repositories.
- **Skill updates** — sync profile from repo, re-read workflow, reset to Phase 1.
- **API verification** — confirm the selected track; trace real API path from user curl or
  browser network tab; reuse cookies — do not guess endpoints.
