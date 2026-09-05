# Web framework contract

The generated business repository owns executable Playwright tests. Reusable
configuration and failure-evidence behavior lives in the independently versioned
`rigorpath_web_test` package in the `rigor-test` runtime repository.

Generated or adapted repositories contain:

- `pyproject.toml` with the `rigor-test` Git dependency pinned to an immutable tag
  or commit and installed with its `web` extra;
- project-owned Page/Component Objects and pytest cases;
- `.env.example` containing variable names and non-sensitive placeholders only;
- repository-local authentication fixtures and test data rules;
- README commands for collection, local validation, and confirmed execution.

Boundary rules:

- The Project Profile selects the Web-capable automation repository, runtime URL,
  immutable revision, environment, and implementation Skill.
- The runtime contains no product routes, selectors, credentials, accounts,
  tenants, browser policies, or environment defaults.
- Existing non-empty repositories are supplemented rather than replaced.
- Static collection must not contact the application under test.
- A missing execution environment may cause an explicit skip at the environment
  gate. Once execution starts, product interaction failures must fail.
- Shared-environment execution and shared-data mutation remain explicit
  confirmation boundaries.
