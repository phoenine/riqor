---
name: epvs-automation
description: Automation classification, generation, validation, and execution coordination skill for agent-next. Use when matching automated coverage, generating API or Web/UI automation drafts, validating generated automation, planning commands, or executing confirmed automation.
---

# epvs-automation

Use this skill for automation routing and execution coordination. It works with
automation repositories under `repositories/test/`.

## Required Reading

- Current workflow file selected by `agent-next`
- `workflows/stage-gates.md`
- `docs/repositories.md`
- `docs/environment.md`
- `references/automation-conversion-rules.md` when classifying cases,
  converting manual cases, planning automation, or generating automation drafts.
- `references/webtest-patterns.md` when working on Web/UI automation,
  Playwright/pytest, PageObject, SPA flows, shift selection, or chart assertions.
- `skills/envision-apitest/SKILL.md` when generating, changing, validating, or
  executing API automation in `repositories/test/envision-apitest`.
- `skills/envision-webtest/SKILL.md` when generating, changing, validating, or
  executing Web/UI or hybrid automation in `repositories/test/envision-webtest`.

## Inputs

- Test cases, risks, impact analysis, or acceptance plan.
- Run state `product_line` (`v1` or `v2`) to select the automation branch.
- Existing automation repository under `repositories/test/`.
- Shared pipeline test data via `repositories/tools/epvs-perf-eval/` — delegate
  preparation to `epvs-data-injection` before automation execution.
- Target environment and required credentials.
- User confirmation for execution or shared data mutation.

## Repository And Branch Rules

- Writable automation code lives only under `repositories/test/`.
- Do not clone or edit automation under `outputs/`.
- Read the ePVS Project Profile automation repository configuration and its
  `branches` map before writing or running Web/UI cases.
- For `envision-webtest`, switch the local mirror to the branch that matches
  run state `product_line`:
  - `v1` → `hermes-cases`
  - `v2` → `hermes-2.0`
- For `envision-apitest`, check out `dev` before writing or running API cases.
  Do not commit, push, or merge directly to `main`.
- Record the checked-out branch in run state `repositories.test[]` and
  repository evidence before changing cases or executing tests.

## Outputs

- Automation coverage match.
- Automation classification.
- Generated automation case plan or draft.
- Automation validation result before execution.
- Automation command and execution result summary.
- Release acceptance automation execution plan covering API and Web/UI targets
  that are in scope.

## Repository-Specific Skill Routing

After classification selects a target repository:

- `target: api` -> load `envision-apitest`, then create or update YAML-driven
  API cases in `repositories/test/envision-apitest`.
- `target: web` or `target: hybrid` -> load `envision-webtest`, then create or
  update Playwright/pytest PageObject or case files in
  `repositories/test/envision-webtest`.
- `target: manual`, `M0`, or `N0` -> do not force repository code; record manual
  or assisted evidence requirements.

For release acceptance execution, do not stop at classification or generic
execution evidence. Build an `automation_execution_plan:` that routes all
covered release items:

- API coverage -> `envision-apitest` / `repositories/test/envision-apitest`.
- Web/UI or hybrid coverage -> `envision-webtest` /
  `repositories/test/envision-webtest`.
- Manual-only, blocked, or unsupported targets -> `automation_execution_skip:`
  with reason, impact, and follow-up.

Do not move directly from classification to execution for newly classified
cases. Generate a conversion plan, write the repository draft, and validate it
before `Optional Case Execute`.

## Tool Commands

Parse Markdown cases before classification:

```bash
python3 tools/parse_markdown_cases.py \
  --case-file outputs/v2/test-cases/<feature>-test-cases.md \
  --output runs/<run-id>/specs/raw
```

Classify raw specs:

```bash
python3 tools/classify_specs.py \
  --input runs/<run-id>/specs/raw/<case-file>.json \
  --output runs/<run-id>/specs/classified/<case-file>.json
```

Generate a conversion plan before writing automation code:

```bash
python3 tools/generate_automation_plan.py \
  --input runs/<run-id>/specs/classified/<case-file>.json \
  --output runs/<run-id>/automation-plan \
  --page <page> \
  --target web \
  --cases-dir repositories/test/envision-webtest/cases
```

Record the active test repository branch after checkout:

```bash
python3 tools/run_state.py \
  --run-id <run-id> \
  --repository kind=test,name=envision-webtest,path=repositories/test/envision-webtest,branch=hermes-2.0
```

For API automation on `envision-apitest`:

```bash
python3 tools/run_state.py \
  --run-id <run-id> \
  --repository kind=test,name=envision-apitest,path=repositories/test/envision-apitest,branch=dev
```

## Do Not

- Do not execute automation without confirmation when it targets shared or
  production-like environments.
- Do not mutate test data without confirmation.
- Do not build or send PLC cycle injection directly; use `epvs-data-injection`
  for `repositories/tools/epvs-perf-eval/`.
- Do not generate automation that lacks upstream test case or risk traceability.
- Do not skip validation before executing generated automation.
- Do not push or merge `envision-apitest` changes directly to `main`; use `dev`.
