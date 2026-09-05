---
name: automation
description: Classify, plan, generate, and validate API, Web, and hybrid test automation using repositories declared by the active Project Profile. Use test-execution for confirmed runner execution and evidence normalization.
---

# automation

Use this skill after requirements, risks, test points, or test cases establish
the intended coverage. The Project Profile selects repositories, frameworks,
tracks, branches, and environment policy; this skill does not assume any
product or framework.

## Required context

- Current route and blockers from `agent-next explain`; do not reopen router
  documents or the full Stage Gate audit guide.
- If no routed Run exists, return to `agent-next` to create one.
- Project Profile repository entries with the required automation capability.
- Existing manual and automated coverage.
- Target environment and its confirmation policy.

Read [references/classification-rules.md](references/classification-rules.md)
when classifying test cases or reviewing an existing classification.

## Workflow

1. Classify each case by automation level and target using its core oracle. Do
   not infer the target from setup steps or from the existence of a UI.
2. Prefer an existing matching case before generating new automation.
3. Resolve the repository and command from the Project Profile or its selected
   project Skill. Do not infer branches, endpoints, credentials, or framework
   conventions.
4. Produce an `automation_classification` or execution plan before changing an
   automation repository or running against a shared environment.
5. For eligible `A0/A1` API or hybrid rows, use `agent-next
   prepare-automation`; it resolves the repository and implementation provider
   from the Project Profile. Treat this explicit command as authorization for
   the declared local scaffold only.
6. Request confirmation immediately before remote repository mutation.
7. Record implementation files, revision, validation, and remaining blockers in
   Run State and the relevant artifact. Hand executable selectors and commands
   to `test-execution`; do not interpret runner results here.

When API coverage needs a new YAML-driven pytest implementation and the Project
Profile selects `rigorpath-api-test`, load `pytest-yaml-api`. It owns bootstrap,
case generation, strict validation, and the `automation_implementation` record;
this generic Skill continues to own classification and confirmation boundaries.

## Project extensions

Load a project-specific automation Skill only when the Project Profile selects
one. It may provide framework commands, repository layout, branch mapping, or
data-preparation rules, but it must preserve the confirmation and evidence
boundaries above.

## Do not

- Do not create a new automation framework when a declared repository already
  provides one.
- Do not guess API routes from source names; verify the real client or network
  path.
- Do not execute runners; use `test-execution` after implementation validation.
- Do not mutate shared state without explicit confirmation.
- Do not upload cases to a test-management system; use its selected sync Skill.
