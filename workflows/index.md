# Workflow Index

This file is the entry router for `agent-next` workflows. Every run starts here
before any asset is written or any external tool is executed.

## Entrypoints

| Entrypoint | Use When | Workflow index |
|---|---|---|
| `feature-quality` | The task starts from a PRD, requirement record, feature MR, branch, commit, or explicit feature description. | `workflows/feature-quality/README.md` |
| `bug-regression` | The task starts from a bug ID, issue number, fix MR, fix commit, or regression request. | `workflows/bug-regression/README.md` |
| `release-acceptance` | The task starts from a release version, tag, deployment environment, full regression request, or validation window. | `workflows/release-acceptance/README.md` |

Phase documents are lazy-loaded per turn:

```bash
python3 tools/phase_doc.py --entry <entry> --phase "<phase>"
```

## Skill Index

Load `agent-next` on every run. Load downstream skills only when the current
workflow phase requires them. Each skill file lives at `skills/<skill>/SKILL.md`.

| Skill | Purpose | Typical phases |
|---|---|---|
| `agent-next` | Workflow routing, run state, stage gates, skill loading | Every phase (router) |
| `requirement-analysis` | Requirement intake, PRD/issue/bug context, requirement specs | feature-quality: Intake, Requirement Specification; bug-regression: Bug Intake; release-acceptance: Scope Collection |
| `test-analysis` | Risk analysis, impact analysis, test point design, coverage scope review | feature-quality: Risk Analysis, Test Design; bug-regression: Change Scope, Impact Analysis; release-acceptance: Scope Collection |
| `test-case-design` | Test case design, TP-to-TC instantiation, case maintenance, coverage match | feature-quality: Test Design; bug-regression: Coverage Match, Regression Plan; release-acceptance: Acceptance Plan |
| `automation` | Automation classification, generation, and implementation validation | feature-quality: Optional Case Sync Or Generation; bug-regression: Coverage Match–Regression Plan; release-acceptance: Acceptance Plan and selector routing |
| `test-execution` | Confirmed execution, runner evidence collection, JUnit normalization, execution records | feature-quality: Optional Case Execute; bug-regression: Execution; release-acceptance: Acceptance Execution |
| `zentao-sync` | Bundled optional ZenTao integration using `zentao-cli`; selected through Project Profile | Phases that read or write ZenTao after confirmation |
| `reporting` | Reports, closeout records, bug drafts, exit criteria | feature-quality: Optional Bug Report, Optional Test Report; bug-regression: Regression Plan, Regression Report; release-acceptance: Release Decision, Optional Post-release Observation |
| `release-acceptance` | Release baseline, scope, acceptance plan, release decision | release-acceptance: all phases |

Conditional integration Skills (such as `zentao-sync`) and implementation Skills apply
only when the phase action and Project Profile need them. The selected Workflow manifest
defines when they are in scope.

## Routing Rules

Choose exactly one primary entrypoint.

If multiple entrypoints appear to apply:

1. Use `release-acceptance` when the user asks for a version-level plan,
   version-level automation, or release validation.
2. Use `bug-regression` when the task is centered on a specific bug or fix.
3. Use `feature-quality` when the task is centered on a new or changed feature.

If the entrypoint is unclear, ask one short clarification question before
creating run state or writing assets.

## Minimum Input By Entrypoint

| Entrypoint | Minimum Input |
|---|---|
| `feature-quality` | At least one of: PRD link/document, requirement/task ID, MR, branch, commit, or explicit feature description. |
| `bug-regression` | At least one of: bug ID, issue number, fix MR, fix commit, or explicit defect description. |
| `release-acceptance` | At least one of: release version, tag, deployment environment, release branch, or explicit validation scope. Record `release_scope_tracks` before completing baseline/scope. |

## Gate Enforcement

Use `agent-next explain --run-id <run-id>` for current blockers and
`agent-next gate --project <profile> --run-id <run-id>` for enforcement. The
Workflow manifest is authoritative; `workflows/stage-gates.md` is the human
audit guide and is not required phase context.
