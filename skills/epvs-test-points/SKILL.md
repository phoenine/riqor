---
name: epvs-test-points
description: Risk, impact, and test point design skill for agent-next. Use when creating feature risk analysis, bug impact analysis, release risk scope, coverage focus, risk matrices, test points, or requirement-to-risk traceability.
---

# epvs-test-points

Use this skill to turn requirements, code evidence, bug fixes, or release scope
into risks, impact areas, and test points.

Core boundary:

```text
epvs-test-points determines coverage.
epvs-test-cases implements coverage.
epvs-test-cases may detect gaps, but must not silently redefine coverage.
```

## Required Reading

- Current workflow file selected by `agent-next`
- `workflows/stage-gates.md`
- `references/test-analysis-methodology.md` when creating or revising test
  points, risk coverage, impact coverage, or requirement-to-test traceability.
- `references/test-point-examples.md` when the expected output shape or
  analysis depth is unclear.
- `references/source-code-verification.md` when risks, impacts, or test points
  depend on source behavior.
- `references/bug-regression-rules.md` when the workflow is bug regression or
  the task starts from a defect/fix.
- `references/permission-risk.md` when the change touches users, roles,
  authorities, scopes, visibility, permissions, or access-controlled data.
- Relevant knowledge under `knowledge/`

## Inputs

- Confirmed requirement specification, bug intake, or release scope.
- Repository evidence from `repositories/dev/`.
- Existing defect, risk, or acceptance context.
- Knowledge-used log.

## Outputs

- Change scope document (`change_scope` via `change-scope` template).
- Impact / risk analysis (`risk_analysis` via `risk-analysis` template).
- Coverage match is owned by `epvs-test-cases`; this skill supplies impact and
  regression risk inputs and may perform Coverage Scope Review.
- Test point document when the workflow phase requires it. Test points define
  coverage intent, not executable steps.
- Traceability from upstream requirement, bug, change, or release scope.

## Test Analysis Workflow

When producing test points or coverage focus:

1. Read `references/test-analysis-methodology.md`.
2. Select `analysis_depth: simple | standard | complex`.
3. Identify only applicable test dimensions.
4. Derive test conditions from requirements, bug facts, change scope, source
   evidence, and knowledge.
5. Select test design techniques at test point level when useful.
6. Produce test points as coverage classes / coverage intent.
7. Review Requirement / Risk / Condition / Test Point continuity.
8. Use a coverage matrix only when traceability is many-to-many or hard to
   verify directly.

When writing a `test_points` artifact, start from
`templates/artifacts/test-points.md.tmpl` and keep `analysis_depth` explicit.

Test point fields are intentionally conditional:

- Always include Source, Risk or Coverage Intent, and Priority.
- Include Dimension for Standard / Complex analysis.
- Include Condition when a condition space exists.
- Include Technique when using BVA, equivalence partitioning, decision table,
  state transition, scenario, combination, regression, or risk-based analysis.
- Include Evidence when claiming source-backed behavior.

## Bug Regression Deliverables

Record `bug_surface:` in Bug Intake (`frontend`, `backend`, or `other`), then
write Markdown under the matching output root — never under `runs/<run-id>/`:

| `bug_surface` | Root |
|---|---|
| `frontend` | `outputs/v1/` or `outputs/v2/` (match `product_line`) |
| `backend`, `other` | `outputs/shared/` |

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template change-scope \
  --producer-phase "Change Scope" \
  --artifact-id CHANGE-SCOPE-001 \
  --destination outputs/shared/regression/<bug-id>-change-scope.md
```

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template risk-analysis \
  --producer-phase "Impact Analysis" \
  --artifact-id IMPACT-001 \
  --destination outputs/shared/regression/<bug-id>-impact-analysis.md
```

Use `outputs/v2/regression/...` instead of `outputs/shared/...` when
`bug_surface: frontend` and `product_line: v2`.

## Do Not

- Do not create detailed test steps; use `epvs-test-cases`.
- Do not encode individual concrete values as separate test points unless they
  represent distinct business risks; concrete values belong to test cases.
- Do not write deliverable Markdown under `runs/`; `runs/` is for state only.
- Do not claim source-backed risk without repository evidence.
- Do not design only happy paths.
- Do not skip impact analysis for bug regression when change scope is available.
