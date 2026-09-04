---
name: test-case-design
description: Detailed test case design, maintenance, and coverage matching skill for agent-next. Use when generating executable test cases, matching existing cases, supplementing case coverage, or maintaining test case traceability.
---

# test-case-design

Use this skill to create, match, or maintain executable test cases after
upstream requirement, risk, impact, or acceptance scope is available.

Core boundary:

```text
test-analysis determines coverage.
test-case-design implements coverage.
test-case-design may detect gaps, but must not silently redefine coverage.
```

## Required Reading (mandatory before writing cases)

Read these in order every time you generate or supplement test cases:

1. Current phase doc from `python3 tools/phase_doc.py --entry <entry> --phase "<phase>"`
2. `workflows/stage-gates.md`
3. **`references/test-case-design-methodology.md`** — TP-to-TC instantiation,
   representative data, split/merge, expected-result, and gap rules.
4. **`references/coverage-review-rules.md`** — TP-to-TC coverage checks,
   unplanned coverage handling, and coverage match statuses.
5. **`references/case-writing-rules.md`** — title format, business language,
   validity rules. Record this path in `knowledge_used` before writing cases.
6. `references/test-case-examples.md` when the expected case shape is unclear.
7. `templates/artifacts/test-cases.md.tmpl` — heading and field layout

Do not write test cases from memory or chat prose alone. The reference defines
the required title format and forbids API parameter names in titles.

When test points are available, treat them as the coverage authority. Generate
cases to instantiate those test points with representative data, executable
steps, observable expected results, and TP-to-TC mapping.

If the active workflow includes Test Analysis / Test Points, new case generation
requires upstream test points. Do not silently bypass a required Test Analysis
phase. Requirement, risk, impact, bug, and acceptance IDs may be additional
traceability, but they do not replace TP traceability.

If the active workflow explicitly omits a Test Point phase, use the
workflow-defined requirement, risk, impact, bug, or acceptance scope as the
coverage authority.

For bug regression Coverage Match, consume Test Points / Coverage Gaps from
`test-analysis` as upstream scope. Match them to existing manual cases and
automation; do not redefine the scope during matching.

## Case Generation Workflow

1. Read `references/test-case-design-methodology.md`,
   `references/coverage-review-rules.md`, and `references/case-writing-rules.md`.
2. Record knowledge use:

```bash
python3 tools/run_state.py \
  --run-id <run-id> \
  --knowledge-used path=skills/test-case-design/references/test-case-design-methodology.md,purpose=tp-to-tc-instantiation-rules \
  --knowledge-used path=skills/test-case-design/references/coverage-review-rules.md,purpose=tp-to-tc-coverage-review \
  --knowledge-used path=skills/test-case-design/references/case-writing-rules.md,purpose=case-title-and-format-rules
```

3. Validate upstream context: TP is authoritative coverage scope; requirement,
   risk, source evidence, and knowledge are supporting execution context.

4. Instantiate TP technique and coverage intent into representative data,
   executable scenario, and observable expected result. Record Coverage Gap
   instead of guessing missing values, rules, states, roles, or expected
   behavior.

5. Split, merge, and deduplicate cases so each case validates one primary
   business outcome. Prefer one behavior model plus `DATA-###` parameter rows
   over one TC per input value, but merge only when setup, operation path,
   observation surface, expected result, assertion basis, priority, and
   traceability are materially the same. Every parameter row must be separately
   executable and reportable.

6. Create the file from template (never blank files, never `runs/`). **Machine
   validation rejects hand-written Markdown** — the file must have YAML
   template sections from `copy_template.py`; identity and lineage stay in the Run Artifact record:

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template test-cases \
  --producer-phase "<phase>" \
  --artifact-id TC-SET-001 \
  --destination <bug-output-root>/test-cases/<bug-id>-regression-cases.md
```

7. Write cases using **`### TC-001：业务描述`** headings (full-width colon `：`
   or half-width `:` both parse). Do not use `VC-01`, `VERIFY-`, or markdown
   `#` section titles as case IDs.

8. Review TP-to-TC coverage before marking the phase complete:

- Every required TP has at least one TC or Coverage Gap.
- Coverage summaries retain the Atomic Requirement IDs carried by upstream Test
  Points, so partial coverage cannot be hidden behind a `REQ-SPEC-*` artifact or
  upstream Feature ID.
- Required decision rules, transitions, equivalence classes, boundary regions,
  and selected combinations are instantiated or recorded as gaps.
- When upstream test points exist, every newly generated TC traces to at least
  one TP. Requirement, risk, impact, bug, and acceptance IDs may be additional
  traceability only.
- When the workflow explicitly omits a Test Point phase, every newly generated
  TC traces to the workflow-defined requirement, risk, impact item, bug, or
  acceptance item that acts as the coverage authority.
- No duplicate case covers the same setup, action, and expected result without
  a reason.
- Every expected result has a matching `断言依据` entry in `<type> | <source>`
  form. Tester-derived checks remain `risk_derived` or `hypothesis`; they are
  not presented as requirement assertions.
- Unplanned `TC without TP` is preserved only when justified by historical,
  bug-regression, acceptance, or coverage-gap evidence.

9. Validate before marking the phase complete:

```bash
python3 tools/validate_test_cases.py --case-file <path-to-case-file>
python3 tools/traceability_lint.py --state runs/<run-id>/state.json
```

10. Fix all validation and traceability errors; then run `stage_gate.py`. Never
    silently replace a dangling ID, even when a nearby ID looks likely.

## Coverage Sanity Check

Before writing or supplementing cases:

- If test points exist, check that each planned new case traces to at least one
  TP and does not silently add coverage outside them.
- If no test points exist, confirm the current workflow explicitly allows direct
  case generation from requirement, risk, impact item, bug, or acceptance scope.
- If a test point has an obvious internal gap, report `Coverage Gap` and ask for
  test analysis to be updated instead of inventing new test points.

Example:

```text
Coverage Gap: TP-007 declares Boundary coverage, but its Coverage Intent only
mentions the minimum boundary. Return to Test Analysis to confirm maximum and
out-of-range coverage before generating extra cases.
```

## Title Rules (summary)

Full rules live in `references/case-writing-rules.md`. Quick checks:

| Wrong | Right |
|---|---|
| `VC-01: ignore3xRule=true → Records 减少` | `TC-001：开启三倍基线过滤后参与计算的周期数应减少` |
| `TC-001：fetch_cycle_times 返回过滤结果` | `TC-001：勾选周期少于三倍基线后基线计算排除离群周期` |
| `TC-002：ignore3xRule=false 不受影响` | `TC-002：未勾选三倍基线过滤时周期统计结果与修复前一致` |

Titles describe **observable business outcomes**, not API flags, SQL, or code
symbols. Prefer titles that state the business condition, object, and expected
result; avoid using “验证 / 测试 / 检查 / 评估” as the main predicate when a
more specific outcome can be named.

## Inputs

- Requirement specification.
- Risk analysis or impact analysis.
- Test points.
- Existing manual cases or coverage inventory.
- Execution scope and environment, when needed for executable case design.

## Outputs

- Detailed test case document (`test_cases` via `test-cases` template).
- Coverage match document (`coverage_match` via `coverage-match` template).
- Matched case list.
- Coverage summary and gaps.
- Traceability to requirement, risk, impact, and test point IDs.

## Bug Regression Output Routing

See `workflows/bug-regression/README.md` → Deliverable Routing for `{root}` paths and
templates. Resolve the current phase with `tools/phase_doc.py`. Never place
deliverable Markdown under `runs/`.

## Do Not

- Do not skip `references/case-writing-rules.md` when generating cases.
- Do not use `VC-` / `VERIFY-` headings or API parameter names in case titles.
- Do not create cases before upstream requirement/risk/impact context exists.
- Do not create cases before upstream test points when the active workflow
  includes a Test Analysis / Test Points phase.
- Do not silently redefine test scope when test points exist; report coverage
  gaps instead.
- Do not write cases for unreachable or unobservable behavior.
- Do not use vague expected results such as “system works normally” or
  “data is correct”; expected results must be observable and deterministic.
- Do not optimize for TC count or create one case per data value when a
  reportable parameter set proves the same behavior model.
- Do not label tester-derived security, reliability, performance, or
  compatibility hypotheses as PRD requirements.
- Do not write deliverable Markdown under `runs/`; `runs/` is for state only.
- Do not sync cases to a test-management platform; use `zentao-sync`.
- Do not execute automation; use `automation`.
