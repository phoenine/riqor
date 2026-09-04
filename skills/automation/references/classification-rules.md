# Automation classification rules

Classify from the core oracle, not from the setup path or feature surface.

## Levels

| Level | Meaning | Next action |
|---|---|---|
| `A0` | Deterministic, observable, controllable, and repeatable with existing support | Implement or execute |
| `A1` | Suitable, but missing a verified contract, fixture, identity, selector, hook, or isolated data | Resolve the named dependency first |
| `M0` | Automation can collect evidence, but a human judgment remains essential | Automate evidence collection only |
| `N0` | Automation is unsafe, uneconomic, unstable, or has no reliable oracle | Keep manual or record `not_recommended` |

## Targets

- `api`: the decisive oracle is an HTTP contract, status, response field, backend
  rule, authorization result, or data transition observable through an API.
- `web`: the decisive oracle is DOM rendering, interaction behavior, navigation,
  accessibility, responsive layout, or browser-only state.
- `hybrid`: both API/network and browser oracles are essential. A UI-only setup
  step does not make an API case hybrid.
- `data_verification`: the decisive oracle is a datastore, event, file, or batch
  result and neither HTTP nor browser behavior is the subject.
- `manual_only`: a human judgment is essential and assisted evidence is enough.
- `not_recommended`: technically possible but its maintenance cost, instability,
  or risk exceeds its regression value.
- `blocked`: classification or implementation lacks required evidence or access.

An explicit test-case type is evidence, not an override. Prefer the core oracle
when the label and expected results conflict.

## Required decision evidence

For each `TC-###`, record:

- level and target;
- core oracle;
- missing dependencies or `none`;
- side effect and isolation/cleanup expectation;
- existing automation match;
- concise decision basis;
- selected destination repository or `none`.

Check existing coverage before proposing generation. Do not classify malformed
or untraceable cases as ready. Destructive behavior does not automatically make
a case `N0`; it may be `A1` when an isolated environment and verified cleanup
can make execution safe.
