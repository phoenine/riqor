# Requirement Specification Contract

Read this reference only during the Feature Quality `Requirement Specification`
phase or when revising a `requirement_spec` artifact.

## Source fidelity

- `明确来源` (`source_explicit`): an authoritative source states the behavior.
- `用户确认` (`user_confirmed`): an authorized person resolved or added it.
- `待证假设` (`assumption`): no authoritative basis; keep it `待确认` and cite a
  `Q-###`.
- Code, configuration, logs, and runtime observations are implementation
  evidence, not normative requirements without an authoritative source or user
  confirmation.
- Coverage ideas belong in Risk Analysis or Test Points unless the source states
  them as requirements.

Render each Atomic Requirement as:

```markdown
**依据**：<明确来源 | 用户确认 | 待证假设> · <已确认 | 待确认 | 存在冲突> · <精确来源>
```

Use `SRC-###` plus the exact section or record when the source is defined in the
artifact's source table. Do not combine conflicting sources into a confirmed
statement.

## Atomic requirements

- One `REQ-###` describes one independently judgeable obligation or observable
  outcome. Split different triggers, actors, states, branches, outcomes,
  sources, or conclusion states.
- Test values and equivalent examples belong in Test Points and Test Cases.
- Use consecutive `REQ-###` IDs; preserve upstream Feature IDs in `依据` and the
  traceability table. Nested IDs such as `REQ-001-01` are invalid.
- Map every authoritative rule to a requirement or mark it explicitly out of
  scope, conflicting, or pending.
- A confirmed requirement must be based on an explicit source or user
  confirmation, never an assumption alone.

## Artifact workflow

Create the artifact from `templates/artifacts/requirement-spec.md.tmpl` with
`agent-next scaffold`. Before completing the phase, run:

```bash
agent-next gate --project <profile> --run-id <run-id> --mark-ready
```

The Gate validates the template, Atomic Requirement fields, source fidelity,
traceability, predecessors, and recorded evidence.
