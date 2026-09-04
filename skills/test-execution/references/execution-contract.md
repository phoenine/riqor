# Execution contract

Canonical statuses:

| Status | Meaning |
|---|---|
| `passed` | All represented executions passed |
| `failed` | At least one product assertion failed |
| `blocked` | A prerequisite prevented meaningful execution |
| `skipped` | Runner intentionally skipped the case |
| `not_run` | Planned case has no runner result |
| `infrastructure_error` | Harness, collection, environment, or transport failed before a trustworthy product assertion |

For parameterized executions sharing one `AUTO-###`, aggregate conservatively:
`infrastructure_error > failed > blocked > skipped > passed`. One passing row
cannot hide an unexecuted or skipped row.

Every automated result must resolve to a known `AUTO-###` from the supplied YAML
case inventory. That inventory carries `TC-###`, `TP-###`, requirement, rule,
risk, question, and dataset provenance. Unknown result IDs and duplicate case
definitions are contract errors.

JUnit is evidence, not the decision itself. Preserve its path and runner
command. `reporting` computes summaries only from normalized statuses and must
not count `blocked`, `skipped`, `not_run`, or `infrastructure_error` as passed.
