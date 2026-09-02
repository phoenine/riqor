---
name: agent-next
description: Lightweight router for agent-next workflows. Use when any task involves agent-next feature testing, bug regression, release acceptance, workflow routing, run state, stage gates, local repositories, knowledge, or routing to project-selected downstream skills.
---

# agent-next

Mandatory router for `agent-next`. Declares downstream skills; does not write
test assets.

## Required Reading

Repo root = package root. Read in order:

1. `workflows/index.md` — entrypoint routing and skill index
2. Selected workflow README: `workflows/<entry>/README.md` (Deliverable Routing)
3. **Current phase only** — resolve path with `phase_doc.py`, then read that file
4. `workflows/stage-gates.md` (Global Gates + Machine Rules; skip unrelated phases)

```bash
python3 tools/phase_doc.py --entry <entry> --phase "<phase>"
```

Do **not** read every `phases/*.md` file in one turn — use `phase_doc.py` for the current phase only.

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

Require explicit user confirmation before side-effect actions in
`workflows/stage-gates.md` Global Blocking Actions.

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
