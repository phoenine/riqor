# Coverage Review Rules

Use this reference to review whether executable test cases correctly implement
upstream coverage without redefining it.

Core boundary:

```text
Test Points define required coverage.
Test Cases instantiate required coverage.
Coverage Review checks the mapping between them.
```

## 1. Inputs

Use the available upstream scope:

- Test Points and Coverage Gaps from `epvs-test-points`.
- Requirement, risk, impact, bug, or acceptance artifacts.
- Existing manual cases.
- Automation inventory from `repositories/test/`, when the phase includes
  automation matching.
- Historical regression cases that must be preserved.

Do not invent missing test points during coverage review. Record a gap and hand
back to Test Analysis when required coverage is missing or unclear.

## 2. Coverage Authority

When upstream Test Points exist, they are the coverage authority:

- Every newly generated TC must trace to at least one TP.
- Requirement, risk, impact, bug, and acceptance IDs may be additional
  traceability, but they do not replace TP traceability.
- A TC that only traces to a requirement, risk, impact item, bug, or acceptance
  item is treated as `TC without TP` and reviewed as unplanned coverage.

When the active workflow explicitly omits a Test Point phase, the
workflow-defined requirement, risk, impact, bug, or acceptance scope acts as the
coverage authority. `epvs-test-cases` must not silently bypass a required Test
Analysis phase.

## 3. Required Checks

Before finalizing a `test_cases` or `coverage_match` artifact, check:

- Every required TP has at least one TC, existing manual case, automation match,
  or recorded Coverage Gap.
- Every required decision-table rule has at least one executable instance.
- Every required state transition has at least one executable instance.
- Every required equivalence class has a representative value or recorded gap.
- Every required boundary region has representative data or recorded gap.
- Every selected combination has an executable instance or recorded gap.
- Every newly generated TC follows the coverage authority rule above.
- Duplicate cases are merged or justified.

## 4. TC Without TP

Treat `TC without TP` as unplanned coverage by default.

Keep it only when one of these applies:

- Existing historical case that must remain in the suite.
- Required bug-regression case for the original failure.
- Acceptance or compliance case required by release scope.
- Evidence shows a real coverage gap that should return to Test Analysis.

Otherwise remove it or mark it as duplicate / invalid coverage.

## 5. Coverage Gap Format

Use explicit, actionable gaps:

```text
Coverage Gap: TP-003 requires minimum-boundary instantiation, but the minimum
Cycle Time value cannot be established from available evidence.
```

```text
Coverage Gap: TC-012 covers role-scope denial behavior but no upstream TP,
requirement, risk, bug, or acceptance item defines that coverage.
```

Do not resolve gaps by guessing values, adding new test points, or silently
expanding case scope.

## 6. Coverage Match Status

Use stable statuses:

| Status | Meaning |
|---|---|
| covered_manual | Covered by an existing or newly written manual case. |
| covered_automation | Covered by automation. |
| partial | Some required coverage is implemented, but part remains uncovered. |
| gap | Required coverage cannot be instantiated or matched. |
| duplicate | Same setup, action, observation, and expected result as another case. |
| out_of_scope | Explicitly excluded by the active workflow scope. |

When both manual and automated coverage exist, record both and prefer automation
for repeatable regression only when the automation directly observes the same
business outcome.

## 7. Review Output

For `test_cases`, summarize coverage in `## 覆盖摘要` and record unresolved
items in `## 覆盖缺口`.

For `coverage_match`, fill the upstream Test Points / Coverage Gaps section and
map each item to existing manual cases, automation, supplement action, or gap.
