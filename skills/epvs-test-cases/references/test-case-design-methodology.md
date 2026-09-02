# Test Case Design Methodology

Use this reference to instantiate upstream test points into executable test
cases.

Core principle:

```text
epvs-test-points determines coverage.
epvs-test-cases implements coverage.
```

Test cases must not silently redefine coverage. Requirement, risk, source
evidence, and knowledge are supporting execution context. Test Points are the
authoritative coverage scope when they exist.

If the active workflow includes Test Analysis / Test Points, new case generation
requires upstream test points. If the workflow explicitly omits a Test Point
phase, the workflow-defined requirement, risk, impact, bug, or acceptance scope
acts as the coverage authority.

## 1. Lifecycle

Convert upstream coverage into executable cases:

```text
Test Point / Coverage Gap
  -> Validate TP Context
  -> Read Technique and Coverage Intent
  -> Select Representative Data
  -> Build Executable Scenario
  -> Split or Merge Cases
  -> Write Observable Expected Results
  -> Deduplicate
  -> Review TP-to-TC Coverage
```

If a required value, rule, transition, data shape, or expected behavior cannot
be established from available evidence, record `Coverage Gap` or `Open
Question`. Do not invent test data or expand scope.

## 2. Technique Instantiation

Instantiate the technique selected by `epvs-test-points`; do not re-select the
technique unless the test point is internally inconsistent.

| TP Technique | Case responsibility |
|---|---|
| Equivalence Partitioning | Pick representative values for each required valid and invalid class. |
| Boundary Value Analysis | Pick boundary-near values such as min-1, min, min+1 or max-1, max, max+1. |
| Decision Table | Create at least one executable instance for each required rule. |
| State Transition | Create initial state, trigger action, and observable target state for each required transition. |
| Scenario | Convert basic, alternative, and recovery flows into business steps. |
| Combination Analysis | Instantiate the high-value combinations already selected by test points. |
| Regression / Error Guessing | Reproduce the original failure condition and nearby risk conditions. |
| Risk-based Testing | Prioritize case order and depth by risk; do not create extra scope without a TP or gap. |

Concrete data belongs in test cases. Coverage class and coverage intent belong
in test points.

## 3. Representative Data

Choose the smallest data set that proves the intended business outcome.

Rules:

- Use source-backed limits, options, states, roles, and relationships.
- Prefer realistic product data over artificial values.
- Include invalid data only when a real user, API, integration, configuration,
  or business process can attempt it.
- Keep data stable and repeatable enough for manual execution or later
  automation.
- If the value is unknown, record a gap instead of guessing.

Examples:

```text
TP class: valid range 10-300
TC representative values: 100, 9, 301
```

```text
TP boundary: minimum Cycle Time
TC representative values: min-1, min, min+1 after the minimum is confirmed.
```

## 4. Case Granularity

One case should validate one primary business outcome.

Keep continuous steps in one case when they serve the same outcome and share
the same setup, action path, and expected result.

Split cases when any of these differ materially:

- Primary risk.
- Failure reason.
- Preconditions or starting state.
- Actor, role, scope, or data ownership.
- Expected result.
- Test surface, such as UI vs API vs data verification.
- Recovery behavior.

Avoid over-splitting single business actions into separate input, click, and
save cases. Avoid over-merging create, edit, execute, disable, and delete into
one large case unless the test point explicitly defines an end-to-end scenario.

## 5. Split, Merge, and Deduplicate

Use parameterized or data-driven cases only when the operation path and expected
result are essentially the same.

When a case is parameterized, multi-combination, or data-heavy, put the data in
the `测试数据` field. Keep single simple values in steps when that is clearer.

Prefer separate cases when:

- One value succeeds and another fails.
- Expected messages or state changes differ.
- Different evidence or risk IDs must be traced.
- One case is P0/P1 and another is lower priority.

Merge or remove duplicates when two cases have the same traceability, setup,
action, observation, and expected result.

When preserving historical cases, mark them as existing coverage instead of
renumbering or rewriting them unnecessarily.

## 6. Expected Results

Expected results must be observable and deterministic.

Avoid vague expectations:

```text
System works normally.
Data is correct.
Save succeeds.
```

Prefer concrete observations:

```text
After saving, the page still shows Cycle Time as 10 seconds.
Reopening the configuration shows Cycle Time remains 10 seconds.
```

Observation level follows the test entry:

| Test entry | Default observation |
|---|---|
| UI | Visible UI state, persisted page value, user-facing message, business downstream result. |
| API | HTTP status, response field, documented error, persisted business state. |
| Data / integration | Queryable record, job output, integration payload, downstream business result. |

Do not assert internal implementation details such as SQL updates, Redis keys,
React state, private method calls, or framework bindings unless the case type is
explicitly API, data, integration, or component-level and the risk requires it.

## 7. Gap Handling

Report a gap instead of guessing when:

- A TP requires boundary instantiation but the boundary value is unknown.
- A TP references a decision rule but the rule condition or expected outcome is
  missing.
- A TP requires a state transition but the supported entry or initial state is
  unclear.
- A TP requires a role, scope, or ownership combination not supported by
  available evidence.
- A TC appears necessary but has no upstream TP, risk, requirement, bug, or
  acceptance item.

Gap format:

```text
Coverage Gap: TP-003 requires minimum-boundary instantiation, but the minimum
Cycle Time value cannot be established from available evidence.
```

Do not silently add new test points or redefine the scope while writing cases.

## 8. Coverage Review

Before finalizing cases, apply `coverage-review-rules.md`.

At minimum:

- Every required TP has at least one TC or a recorded Coverage Gap.
- Required decision rules, state transitions, equivalence classes, boundary
  regions, and selected combinations are instantiated.
- When upstream test points exist, each new TC traces to at least one TP.
- When the workflow explicitly omits a Test Point phase, each new TC traces to
  the workflow-defined requirement, risk, impact item, bug, or acceptance item.
- Duplicate or unplanned cases are removed, preserved with a reason, or sent
  back as Coverage Gap.
