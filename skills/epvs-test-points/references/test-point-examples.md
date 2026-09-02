# Test Point Examples

Use these examples to keep output size proportional to risk. They are examples
only; source evidence and product behavior still come from the active workflow.

## Simple

```markdown
analysis_depth: simple

### TP-001: Enabled status is visible after turning on the setting

Source: REQ-001
Priority: P2
Risk / Coverage Intent: Confirm the user-visible status reflects the enabled
setting.
Evidence: requirement_spec: REQ-001
```

Use Simple when extra dimensions, conditions, or techniques do not add useful
clarity.

## Standard

```markdown
analysis_depth: standard

### TP-003: Cycle Time minimum boundary behavior

Source: REQ-002 / RISK-001
Priority: P1
Dimension: Boundary
Condition: Cycle Time is near the minimum allowed value.
Technique: Boundary Value Analysis
Risk / Coverage Intent: Cover below minimum, the minimum value, and a nearby
valid value. Concrete values belong in test cases.
Evidence: risk_analysis: RISK-001
```

Use Standard for most feature testing and normal bug regression.

## Complex

```markdown
analysis_depth: complex

### TP-007: Synchronization rule priority across interacting conditions

Source: REQ-005 / RISK-004
Priority: P0
Dimension: Business Rule / Configuration / Integration
Condition: Device-group sync, action-group sync, sync word, and baseline/general
value relationship interact.
Technique: Decision Table + Combination Analysis
Risk / Coverage Intent: Cover each business rule branch and high-value
condition combination without expanding concrete data into separate test points.
Evidence: repository_evidence: sync-rule-handler
```

Use Complex only when the condition space would be easy to miss with ordinary
natural-language test points.
