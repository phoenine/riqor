# YAML case contract

Each suite uses `schema_version: 1`, declares `required_env`, and contains one or
more cases. Every case must have:

- unique `AUTO-###` ID and title;
- source lists including at least one `TP-###` and one `TC-###`;
- verified request method and absolute-path reference;
- one or more provenance-aware assertions;
- explicit `side_effect: none | isolated | cleanup`.

Assertion `type` is one of `requirement`, `business_rule`, `contract`,
`risk_derived`, or `hypothesis`. The `source` identifies the exact evidence.
A hypothesis failure is an observation until the product owner accepts it as a
requirement.
Use `${NAME}` only for names listed in `required_env`. Use `${cache.name}` only
after a prior capture defines it. Missing values are errors; they are never
replaced with empty strings.

Prefer one behavior model plus data rows to repeated cases. Record dataset IDs
as `DATA-###`. Cleanup must be explicit and is attempted even when the primary
assertion fails; cleanup failures remain visible.
