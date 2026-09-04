---
name: reporting
description: Reporting and closeout skill for agent-next. Use when producing feature test reports, regression reports, acceptance reports, run summaries, bug report drafts, traceability summaries, exit criteria evaluations, or follow-up action lists.
---

# reporting

Use this skill to produce concise reports and closeout records from completed
workflow phases.

## Required Reading

- Current workflow file selected by `agent-next`
- `workflows/stage-gates.md`

## Inputs

- Upstream artifacts and artifact metadata.
- Traceability chain.
- Execution evidence.
- Issue or bug records.
- Exit criteria, release decision, or regression decision.

## Outputs

Workflow-specific closeout records (each maps to one template and artifact
type):

- Feature-testing closeout (`run_summary` via `run-summary` template). The
  business term *feature test report* refers to this closeout content; there is
  no separate `feature_test_report` artifact type.
- Regression report (`regression_report` via `regression-report` template).
- Acceptance report (`acceptance_report` via `acceptance-report` template).
- Bug report draft (`bug_report` via `bug-report` template).
- Execution evidence (`execution_record` via `execution-record` template).
- Automation classification (`automation_classification` via
  `automation-classification` template).

Supporting outputs (sections within closeout artifacts or run state):

- Traceability summary (`traceability[]` and/or run summary sections).
- Follow-up owners and actions (run summary or `notes[]`).

For automated runs, consume the normalized `execution_record` produced by
`test-execution`. Do not reinterpret raw console output as authoritative or
count `blocked`, `skipped`, `not_run`, or `infrastructure_error` as passed.

## Feature Testing Closeout

In `feature-quality`, produce the closeout with the `run-summary` template only:

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template run-summary \
  --producer-phase "Optional Test Report" \
  --artifact-id RUN-SUMMARY-001 \
  --destination <artifact-root>/<scope>/reports/<feature>-run-summary.md
```

Stage gates check artifact type `run_summary`, not a separate feature test
report type.

## Templates

Create report assets with `tools/copy_template.py`:

| Template | Artifact type | When |
|---|---|---|
| `execution-record` | `execution_record` | Manual / automation execution evidence |
| `bug-report` | `bug_report` | Confirmed failure draft before external sync |
| `run-summary` | `run_summary` | Feature-testing closeout (feature test report) |
| `automation-classification` | `automation_classification` | API / Web / manual routing decision |
| `regression-report` | `regression_report` | Bug-regression closeout |
| `acceptance-report` | `acceptance_report` | Release-acceptance closeout |

## Do Not

- Do not invent pass/fail evidence.
- Do not mark a workflow complete when required gates are not satisfied.
- Do not create or update external platform records; use the Project
  Profile-selected integration Skill.
- Do not hide unresolved questions, skipped scopes, or accepted known issues.
