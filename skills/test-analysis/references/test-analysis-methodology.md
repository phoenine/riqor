# Test Analysis Methodology

Use this reference to turn requirements, bugs, change scope, or release scope
into risk-based test conditions and test points.

Core principle:

```text
test-analysis determines coverage.
test-case-design implements coverage.
test-case-design may detect gaps, but must not silently redefine coverage.
```

In Chinese:

```text
测试点决定“覆盖什么”；测试用例决定“怎么执行这个覆盖”。
测试用例可以发现测试点缺口，但不能静默扩展测试范围。
```

## 1. Goal

Convert upstream scope into:

```text
Atomic Requirement / Bug / Change / Release
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
- Many-to-many Atomic Requirement / Risk / Condition / Test Point traceability ->
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

## 3.1 Risk Type, Subtype, and Tags

Risk Type describes the primary failure domain. It is not the same as a Test
Dimension or Technique. Select exactly one stable Primary Type:

| Risk Type | Meaning | Candidate strategies |
|---|---|---|
| `functional` | Required business behavior or result may be wrong | Scenario, branch, decision rule, negative path |
| `security` | Confidentiality, integrity, authorization, or abuse resistance may fail | Negative testing, abuse case, privilege bypass, enumeration, information leakage |
| `integration` | A boundary between components, services, or external systems may fail | Contract, timeout, error propagation, retry, idempotency |
| `data` | Data correctness, consistency, shape, or lifecycle may fail | Integrity, missing/duplicate data, precision, migration, reconciliation |
| `state` | State storage or transitions may be wrong | State transition, forbidden transition, repetition, recovery |
| `configuration` | Configuration values or their lifecycle may produce wrong behavior | Missing/invalid values, on/off combinations, cache, hot reload |
| `compatibility` | Existing clients, versions, configurations, or historical data may break | Upgrade, downgrade, old/new version, API/data/config compatibility |
| `performance` | Latency, throughput, capacity, or resource use may violate expectations | Load, latency, capacity, duration, degradation trend |
| `availability_resilience` | Failures may cause interruption or prevent recovery | Fault injection, timeout, fallback, restart, retry, recovery |
| `usability` | Users may be unable to discover, understand, or complete the flow | Discoverability, feedback, error messaging, accessibility |
| `observability` | Operators may be unable to detect, correlate, or diagnose behavior | Logs, metrics, alerts, correlation IDs, diagnostic context |

`Risk Subtype` is a concise failure mode such as `information_disclosure` or
`cache_invalidation`. `Risk Tags` are zero or more cross-cutting labels such as
`timing`, `concurrency`, `permission`, `boundary`, `recovery`, or `regression`.
Use `none` when no subtype or tag adds information.

The candidate strategies above are prompts for analysis, not mandatory output.
Only generate coverage that is reachable and justified by the risk's trigger,
impact, doubts, and evidence. For example, a `security` risk does not require
enumeration, privilege bypass, and information leakage tests unless those
failure modes are actually applicable.

## 3.2 Risk Status

Use one lifecycle status and keep decisions or evidence summaries in their own
fields:

| Status | Meaning |
|---|---|
| `identified` | Candidate risk recorded but not yet prepared for validation. |
| `pending_validation` | Validation is planned or still incomplete. |
| `validated` | Evidence confirms that the risk is real. |
| `accepted` | The risk is real and an authorized decision explicitly accepts it. |
| `mitigated` | A control or change reduces the risk, but closure is not yet established. |
| `closed` | Evidence shows the risk is resolved. |
| `dismissed` | Evidence shows the candidate risk does not apply or is not real. |

Test coverage does not by itself make a risk `closed`. An `accepted` or
`dismissed` risk must carry a Decision Note with its confirmation or evidence.

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
to `test-case-design`.

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

When a Requirement Spec exists, each `REQ-###` row is an Atomic Requirement and
must be reviewed independently. Do not substitute the `REQ-SPEC-*` artifact ID
or upstream Feature ID for these rows; an unmapped Atomic Requirement is a
Coverage Gap even when sibling requirements are covered.

Require a matrix only when traceability is many-to-many or coverage
relationships are difficult to verify directly. Permission, state-machine,
decision-table, combination, cross-module, or high-risk analysis may use other
structured aids when the traceability remains simple.

Minimum matrix columns:

| Atomic Requirement / Bug | Risk | Dimension | Condition | Technique | Test Point |
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

## 12. Traceability Lint

Test Points are the authoritative coverage artifact between analysis and case
implementation. Before finalizing Risk Analysis, Test Points, or Test Cases,
build a Run-scoped registry from the managed artifacts:

| ID | Definition |
|---|---|
| `REQ-###` | Atomic Requirement heading |
| `BR-###` | Requirement Spec business-rule table |
| `Q-###` | Requirement Spec open-question table |
| `RISK-###` | Risk detail heading |
| `TP-###` | Test Point list ID or TP heading |
| `TC-###` | Test Case heading |

Reject duplicate definitions and any internal reference that is absent from the
registry. Artifact-level Test Point validation must also ensure that every TP
used by Requirement Coverage, Risk Coverage, Coverage Matrix, Coverage Gap, or
traceability sections exists in the same Test Point artifact.

Report the source file, line, and missing ID, for example:

```text
dangling_reference test-points.md:42: TP-044 NOT FOUND
```

Do not auto-correct it to a nearby identifier. A missing ID may mean a typo, a
deleted item, or an omitted Test Point, and those cases require different fixes.
`RA-###` remains unsupported until its declaration and meaning are contracted.
