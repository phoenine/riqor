# Test Analysis Methodology

Use this reference to turn requirements, bugs, change scope, or release scope
into risk-based test conditions and test points.

Core principle:

```text
epvs-test-points determines coverage.
epvs-test-cases implements coverage.
epvs-test-cases may detect gaps, but must not silently redefine coverage.
```

In Chinese:

```text
测试点决定“覆盖什么”；测试用例决定“怎么执行这个覆盖”。
测试用例可以发现测试点缺口，但不能静默扩展测试范围。
```

## 1. Goal

Convert upstream scope into:

```text
Requirement / Bug / Change / Release
  -> Change Scope
  -> Risk Analysis
  -> Test Dimensions
  -> Test Conditions
  -> Technique Selection
  -> Test Points
```

Test points describe coverage intent. They do not describe executable steps.

## 2. Analysis Depth

Choose the lightest depth that prevents missed coverage. Record the selected
depth as `analysis_depth`.

Depth triggers are hierarchical:

```text
Complex > Standard > Simple
```

If any Complex trigger applies, use Complex. Otherwise, if any Standard trigger
applies, use Standard. Use Simple only when neither Standard nor Complex
conditions apply.

### Simple

Use for:

- Single-field display.
- Simple CRUD.
- Single switch or UI path.
- Clear low-risk changes.

Required output:

- Source.
- Risk or coverage intent.
- Priority.
- Test point.

`Dimension`, `Condition`, and `Technique` can be omitted when they add no real
clarity.

### Standard

Use for most feature requirements and normal bug regression:

- Input ranges.
- Multiple business conditions.
- Data filtering.
- Configuration affects calculation or display.
- Moderate state change.
- Normal regression around a bug fix.

Add:

- Applicable dimensions.
- Test conditions.
- Technique when using BVA, equivalence partitioning, scenario analysis, or
  another explicit method.

### Complex

Use for:

- Multi-condition business rules.
- Permissions, roles, authorities, or scopes.
- State machines.
- Complex configuration combinations.
- Cross-module or cross-service changes.
- High-risk regression.
- Algorithms, reports, statistics, or shared components.

Require the relevant analysis aid:

- Decision table.
- State transition model.
- Coverage matrix.
- Combination analysis.

Complex analysis requires at least one appropriate structured analysis aid when
natural-language test points are insufficient. Do not automatically add every
aid. Select the aid that matches the risk:

- Multi-condition business rule -> Decision Table.
- State lifecycle -> State Transition Model.
- Parameter interaction -> Combination Analysis.
- Many-to-many Requirement / Risk / Condition / Test Point traceability ->
  Coverage Matrix.

## 3. Test Dimensions

Evaluate dimensions internally, but output only applicable dimensions unless a
Complex analysis or audit explicitly needs the full assessment.

Common dimensions:

- Functional
- Input
- Boundary
- Business Rule
- State
- Workflow
- Data
- Permission
- Time
- Configuration
- Integration
- Concurrency
- Compatibility
- Recovery
- Regression

When `Permission` applies, read `permission-risk.md`.

## 4. Test Condition Identification

Derive concrete, verifiable conditions from applicable dimensions:

- Business rule branches.
- Input classes.
- Boundary regions.
- State transitions and forbidden transitions.
- Role, authority, and scope combinations.
- Workflow branches.
- Data presence, absence, consistency, aggregation, and filtering.
- Time windows, schedules, and date boundaries.
- Configuration on/off or value combinations.

Do not invent expected behavior. If a condition cannot be confirmed from the
requirement, source evidence, bug record, or knowledge base, record an open
question or coverage gap.

## 5. Test Condition Validity

Every test condition must represent at least one of:

1. A state, input, path, configuration, data shape, or business flow reachable
   through a supported user, API, integration, configuration, or data entry.
2. A business-invalid action that a real actor can attempt through a supported
   entry.
3. A risk explicitly requiring lower-level API, integration, data, or component
   testing.

Do not create test points solely for:

- Compiler or type-system guarantees.
- Framework binding behavior with no business-visible risk.
- Impossible internal states.
- Defensive guard clauses unreachable through supported flows.
- Fabricated backend failures unless fault handling is explicitly in scope.
- Invalid combinations created only to satisfy a technique.

If a condition is important but not reachable through the current test surface,
record it as `Coverage Gap` or `Open Question` instead of turning it into a
manual test point.

## 6. Technique Selection

Select techniques at test point level; instantiate concrete data at test case
level.

| Trigger | Technique | Test point responsibility |
|---|---|---|
| Input range or numeric limit | Equivalence Partitioning + Boundary Value Analysis | Identify valid and invalid classes plus boundary regions |
| Multi-condition business rule | Decision Table | Identify rules that need coverage |
| State lifecycle | State Transition | Identify legal, illegal, repeated, and recovery transitions |
| Business workflow | Scenario | Identify meaningful user or business paths |
| Parameter interaction | Combination Analysis | Identify high-value combinations without exhaustive explosion |
| Historical failure | Error Guessing / Regression | Identify original failure condition and nearby regressions |
| High-impact area | Risk-based Testing | Prioritize coverage by impact and likelihood |

Example boundary split:

```text
TP layer: Cycle Time minimum boundary behavior; cover below min, min, and nearby valid value.
TC layer: choose concrete values such as min-1, min, min+1.
```

## 7. Test Point Granularity

`TP = coverage class / coverage intent`.

`TC = executable instance`.

Do not create separate test points for individual values unless each value
represents a distinct business risk.

Good:

```text
TP-003: Cycle Time minimum boundary behavior
Coverage Intent: cover below minimum, minimum, and nearby valid value.
Technique: Boundary Value Analysis.
```

Avoid:

```text
TP-003: Cycle Time = 9
TP-004: Cycle Time = 10
TP-005: Cycle Time = 11
```

Those concrete values belong in test cases.

## 8. Test Point Field Rules

Do not force every field onto every simple test point.

Always include:

- Source.
- Risk or Coverage Intent.
- Priority.

Conditionally include:

- Dimension: required for Standard and Complex analysis.
- Condition: required when a condition space exists.
- Technique: required when using BVA, equivalence partitioning, decision table,
  state transition, scenario, combination, regression, or risk-based methods.
- Evidence: required when claiming source-backed behavior.

Suggested shape:

```markdown
### TP-001: Business outcome or coverage intent

Source: REQ-123 / BUG-456 / RISK-001
Priority: P1
Dimension: Boundary / Business Rule
Risk / Coverage Intent: ...
Condition: ...
Technique: Boundary Value Analysis
Evidence: repository_evidence: ...
```

Do not include preconditions, steps, or detailed expected results. Those belong
to `epvs-test-cases`.

## 9. Priority

Use priority to communicate execution order and business risk:

| Priority | Meaning |
|---|---|
| P0 | Release-blocking or safety-critical coverage; failure means the change cannot ship. |
| P1 | Core business flow, high-risk regression, or important cross-module behavior. |
| P2 | Normal coverage for secondary flows, boundaries, compatibility, or moderate regression risk. |
| P3 | Low-risk exploratory, performance, usability, or nice-to-have coverage. |

Prefer the highest priority justified by source evidence and risk. Do not use
P0 only because a condition is technically complex.

## 10. Coverage Matrix

Coverage matrix is a complexity management tool, not a mandatory template.

Do not require a matrix when the relationship is simple:

```text
REQ-001 -> TP-001, TP-002, TP-003
```

Recommend a matrix when requirements, risks, conditions, and test points start
crossing.

Require a matrix only when traceability is many-to-many or coverage
relationships are difficult to verify directly. Permission, state-machine,
decision-table, combination, cross-module, or high-risk analysis may use other
structured aids when the traceability remains simple.

Minimum matrix columns:

| Requirement / Bug | Risk | Dimension | Condition | Technique | Test Point |
|---|---|---|---|---|---|

## 11. Gap Handling

Use explicit gaps instead of inventing behavior:

- Unknown requirement.
- Unknown implementation.
- Missing condition.
- Missing evidence.
- Unsupported assumption.
- Coverage mismatch.

Write these as `Open Question` or `Coverage Gap`, and let the workflow decide
whether to ask the user, inspect more source, or defer coverage.
