# Bug Regression Workflow

Use when the task starts from a bug, issue, fix, or regression request.

**Triggers:** bug or issue ID, fix MR/commit, explicit regression request.

## Outcomes

Primary: bug context, change scope, impact analysis, coverage match, decision,
plan, execution record, report.

Optional: supplement cases, automation, test-management update, or
`optional_skip:Execution:`.

## Deliverable Routing

`runs/<run-id>/` is **run state only**. Use `tools/run_state.py`; do not hand-edit
`state.json`.

Record `bug_surface:` in Bug Intake `notes[]` for risk classification. `{root}`
comes from the Project Profile `artifacts.root`, bug scope, and owning track;
surface no longer selects a fixed Core directory.

| Phase | Template | Artifact type | Destination (example) |
|---|---|---|---|
| Bug Intake | — | — | `bug_surface:` in `notes[]` |
| Change Scope | `change-scope` | `change_scope` | `{root}regression/bug-<id>-change-scope.md` |
| Impact Analysis | `risk-analysis` | `risk_analysis` | `{root}regression/bug-<id>-impact-analysis.md` |
| Coverage Match | `coverage-match` | `coverage_match` | `{root}regression/bug-<id>-coverage-match.md` |
| Decision Gate | — | — | `decision_path:` in `notes[]` |
| Regression Plan | `regression-plan` | `regression_plan` | `{root}regression/bug-<id>-regression-plan.md` |
| Regression Plan (supplement) | `test-cases` | `test_cases` | `{root}test-cases/bug-<id>-regression-cases.md` |
| Execution | `execution-record` | `execution_record` | `{root}execution-records/bug-<id>-execution.md` |
| Regression Report | `regression-report` | `regression_report` | `{root}reports/bug-<id>-regression-report.md` |

## Lazy-load phase docs

Read **only** the current phase file. Resolve its path:

```bash
python3 tools/phase_doc.py --entry bug-regression --phase "<phase>"
```

List all phase paths: `python3 tools/phase_doc.py --entry bug-regression --list-phases`

Set `state.workflow` to `workflows/bug-regression/README.md` for new runs.

| # | Phase | Doc |
|---|---|---|
| 1 | Bug Intake | `phases/01-bug-intake.md` |
| 2 | Change Scope | `phases/02-change-scope.md` |
| 3 | Impact Analysis | `phases/03-impact-analysis.md` |
| 4 | Coverage Match | `phases/04-coverage-match.md` |
| 5 | Decision Gate | `phases/05-decision-gate.md` |
| 6 | Regression Plan | `phases/06-regression-plan.md` |
| 7 | Execution | `phases/07-execution.md` |
| 8 | Regression Report | `phases/08-regression-report.md` |
