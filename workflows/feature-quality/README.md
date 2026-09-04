# Feature Quality Workflow

Use when the task starts from a new or changed feature.

**Triggers:** PRD, requirement/task record, MR/branch/commit, explicit feature description.

## Outcomes

Primary: requirement specification from PRD, selected integrations, and code evidence.

Optional: test points, test cases, automation plan, test-management sync, run summary.

## Deliverable Routing

`{root}` = the active Project Profile `artifacts.root` plus scope and owning
track. Never write deliverables under `runs/`.

| Phase | Template | Artifact type | Example path |
|---|---|---|---|
| Requirement Specification | `requirement-spec` | `requirement_spec` | `{root}requirements/<feature>-requirement-spec.md` |
| Risk Analysis | `risk-analysis` | `risk_analysis` | `{root}risks/<feature>-risk-analysis.md` |
| Test Design | `test-points` | `test_points` | `{root}test-points/<feature>-test-points.md` |
| Test Design | `test-cases` | `test_cases` | `{root}test-cases/<feature>-test-cases.md` |
| Optional Case Sync Or Generation | `automation-classification` | `automation_classification` | `{root}automation/<feature>-classification.md` |
| Optional Case Sync Or Generation | `automation-implementation` | `automation_implementation` | `{root}automation/<feature>-implementation.md` |
| Optional Case Execute | `execution-record` | `execution_record` | `{root}execution/<feature>-execution-record.md` |
| Optional Bug Report | `bug-report` | `bug_report` | `{root}reports/<feature>-bug-report.md` |
| Optional Test Report | `run-summary` | `run_summary` | `{root}reports/<feature>-run-summary.md` |

Validate: `validate_artifact.py`, `validate_test_cases.py` (cases),
`traceability_lint.py`, `stage_gate.py`.

## Lazy-load phase docs

```bash
python3 tools/phase_doc.py --entry feature-quality --phase "<phase>"
```

Set `state.workflow` to `workflows/feature-quality/README.md`.

| # | Phase | Doc |
|---|---|---|
| 1 | Intake | `phases/01-intake.md` |
| 2 | Requirement Specification | `phases/02-requirement-specification.md` |
| 3 | Risk Analysis | `phases/03-risk-analysis.md` |
| 4 | Test Design | `phases/04-test-design.md` |
| 5 | Optional Case Sync Or Generation | `phases/05-optional-case-sync-or-generation.md` |
| 6 | Optional Case Execute | `phases/06-optional-case-execute.md` |
| 7 | Optional Bug Report | `phases/07-optional-bug-report.md` |
| 8 | Optional Test Report | `phases/08-optional-test-report.md` |
