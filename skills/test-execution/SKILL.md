---
name: test-execution
description: Plan confirmed test runs, execute Project Profile-selected runners, normalize JUnit evidence, and produce traceable execution records. Use for manual or automated test execution and result collection, not for designing cases or deciding automation suitability.
---

# test-execution

Use this Skill after test scope and executable cases are ready. `automation`
classifies and implements automation; this Skill owns the execution boundary and
evidence normalization.

Read [references/execution-contract.md](references/execution-contract.md) before
running cases or interpreting runner output.

## Workflow

1. Resolve repository, immutable revision, selector, command, environment, and
   report paths from the Project Profile and implementation artifact. Do not
   infer credentials or commands.
2. Preview scope, side effects, cleanup, target environment, and expected
   evidence. Obtain confirmation immediately before shared-environment
   execution or shared-data mutation.
3. Run the narrowest declared selector. Preserve the exact command, exit code,
   revision, start/end time, JUnit XML, logs, and attachments.
4. Normalize JUnit results with
   `python3 scripts/normalize_junit.py --junit <xml> --cases <yaml-or-dir> --output <execution-record> ...`.
5. Validate the generated `execution_record` and traceability before reporting
   results or drafting bugs.

## Boundaries

- Never infer `passed` from process exit code alone.
- Missing planned cases are `not_run`, never passed.
- JUnit `<failure>`, `<error>`, and `<skipped>` remain distinct.
- A runner crash is `infrastructure_error`; it is not a product failure.
- Do not retry failed tests automatically. A retry requires an explicit reason
  and both attempts remain evidence.
- Do not create external bugs or reports; route the normalized record to
  `reporting` and the selected issue-tracker Skill.
