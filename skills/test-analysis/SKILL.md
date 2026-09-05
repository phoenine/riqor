---
name: test-analysis
description: Risk, impact, and test point design skill for agent-next. Use when creating feature risk analysis, bug impact analysis, release risk scope, coverage focus, risk matrices, test points, or requirement-to-risk traceability.
---

# test-analysis

Use this skill to turn requirements, code evidence, bug fixes, or release scope
into risks, impact areas, and test points.

Core boundary:

```text
test-analysis determines coverage.
test-case-design implements coverage.
test-case-design may detect gaps, but must not silently redefine coverage.
```

## Required Reading

- Use the route and blockers already returned by `agent-next explain`; do not
  reopen the workflow index, selected README, or full Stage Gate audit guide.
- If no routed Run exists, return to `agent-next` to create one.
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
- Repository evidence from Project Profile product repositories.
- Existing defect, risk, or acceptance context.
- Knowledge-used log.

## Outputs

- Change scope document (`change_scope` via `change-scope` template).
- Impact / risk analysis (`risk_analysis` via `risk-analysis` template).
- Coverage match is owned by `test-case-design`; this skill supplies impact and
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

Requirement coverage is evaluated against Atomic Requirement IDs inside the
Requirement Spec, not only against the `REQ-SPEC-*` artifact or an upstream
Feature ID. Map every Atomic Requirement to one or more Test Points or an
explicit Coverage Gap; never mark a coarse parent as covered when only some of
its rules are represented.

## Risk Analysis Contract

Use the risk matrix as a compact index and `## 风险详情` as the authoritative
content for each risk. Every `RISK-###` detail must record:

- Source, Primary Risk Type, optional Subtype, and optional Tags.
- Stable Status and Level.
- Problem Essence, Trigger Conditions, Impact, Doubts, and Validation Method.
- Code Evidence when a product repository was provided and the risk makes a
  source-backed claim. Cite repository, revision, path, symbol or line, and the
  supported conclusion. If no repository was provided, write `not_available`;
  never invent evidence.
- A separate Decision Note when a risk is accepted or dismissed. Do not embed
  lifecycle decisions inside the Status value.

Select exactly one Primary Risk Type from the stable taxonomy in
`references/test-analysis-methodology.md`. Use Subtype for the concrete failure
mode and Tags for cross-cutting conditions such as timing, concurrency,
permission, recovery, boundary, or regression. When several categories apply,
choose the type that best describes the failure's primary nature and retain the
others as Tags.

Risk Type selects candidate analysis dimensions and techniques; it does not
automatically create Test Points or Test Cases. Derive coverage from the risk's
reachable trigger, impact, doubts, and evidence.

For platform or shared-framework scope involving authentication, authorization,
sessions, tenant context, routing, shared configuration, or common client
infrastructure, explicitly assess `security`, `availability_resilience`,
`performance`, and `compatibility`. For each category, either link justified
Risk / Test Point IDs or record `not_applicable` with a scope-specific reason.
Assessment is mandatory; generating coverage remains conditional on reachable,
evidence-backed risk.

Do not invent performance thresholds, supported browsers, viewports, storage
modes, or failure-injection capabilities. Source concrete targets from the
Project Profile or authoritative project evidence. Without a normative target,
write a characterization objective, Risk, Coverage Gap, or Open Question rather
than a pass/fail requirement. Route concurrency, timeout, partial-failure, and
recovery checks to API, component, integration, or fault-injection surfaces when
manual UI execution cannot produce or observe them reliably.

When writing a `test_points` artifact, start from
`templates/artifacts/test-points.md.tmpl` and keep `analysis_depth` explicit.

Test point fields are intentionally conditional:

- Always include Source, Risk or Coverage Intent, and Priority.
- Include Dimension for Standard / Complex analysis.
- Include Condition when a condition space exists.
- Include Technique when using BVA, equivalence partitioning, decision table,
  state transition, scenario, combination, regression, or risk-based analysis.
- Include Evidence when claiming source-backed behavior.

## Traceability Lint

Test Points are the coverage authority. Before presenting Risk Analysis or Test
Design as complete, run the Run-scoped lint after artifact validation:

```bash
python3 tools/traceability_lint.py --state runs/<run-id>/state.json
```

The lint must resolve internal `REQ`, `RISK`, `TP`, `TC`, `BR`, and `Q`
references against definitions in the current Run artifacts. Duplicate
definitions and dangling references are errors; do not complete the phase or
silently replace a missing ID. A likely nearby ID may be reported as a hint only.

`RA-###` is not supported until the repository defines what RA represents and
where it is declared. Treat an RA reference as an error instead of guessing its
meaning. External platform identifiers such as Bug or task IDs remain evidence
references and are not required to have local Markdown definitions.

## Bug Regression Deliverables

Record `bug_surface:` in Bug Intake, then write Markdown below the active
Project Profile `artifacts.root` and scope. Use the owning track recorded in Run
State; never route from a product name embedded in this Skill.

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template change-scope \
  --producer-phase "Change Scope" \
  --artifact-id CHANGE-SCOPE-001 \
  --destination <artifact-root>/<scope>/regression/<bug-id>-change-scope.md
```

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template risk-analysis \
  --producer-phase "Impact Analysis" \
  --artifact-id IMPACT-001 \
  --destination <artifact-root>/<scope>/regression/<bug-id>-impact-analysis.md
```

## Do Not

- Do not create detailed test steps; use `test-case-design`.
- Do not encode individual concrete values as separate test points unless they
  represent distinct business risks; concrete values belong to test cases.
- Do not write deliverable Markdown under `runs/`; `runs/` is for state only.
- Do not claim source-backed risk without repository evidence.
- Do not use multiple Primary Risk Types to avoid choosing the risk's main
  failure domain; use Subtype and Tags for secondary characteristics.
- Do not generate a fixed suite of tests from Risk Type alone.
- Do not complete Risk Analysis or Test Design while Traceability Lint reports
  duplicate, dangling, or unsupported internal references.
- Do not design only happy paths.
- Do not skip impact analysis for bug regression when change scope is available.
