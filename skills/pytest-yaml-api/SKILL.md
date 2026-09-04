---
name: pytest-yaml-api
description: Bootstrap, generate, validate, and execute traceable YAML-driven API automation projects using the rigorpath-api-test runtime. Use when API test points or cases should become executable automation, or when a new API automation repository is requested.
---

# pytest-yaml-api

Use this implementation Skill only after `automation` classifies coverage as
API automation and the active Project Profile selects this Skill or explicitly
selects the `rigorpath-api-test` runtime.

## Required inputs

- Verified API contract or observed request evidence. Never invent routes.
- `test_points` and `test_cases`; retain their exact IDs.
- Requirement, business-rule, risk, question, and dataset IDs used as assertion
  sources.
- Target repository and environment policy from the Project Profile.

Read [references/framework-contract.md](references/framework-contract.md) before
bootstrapping a repository. Read [references/case-contract.md](references/case-contract.md)
before generating or changing YAML cases.

## Workflow

1. Classify the requested operation as `bootstrap`, `generate`, `validate`, or
   `execute`. A request may include more than one operation.
2. For `bootstrap`, confirm that no declared API automation repository already
   provides the required capability. Preview the target, then run
   `python3 scripts/scaffold_framework.py --destination <path> --project-name <name>`.
   The script refuses a non-empty destination and never overwrites files.
3. For `generate`, map one behavior model to one `AUTO-###` case. Prefer datasets
   over duplicating structurally identical cases. Copy source IDs and assertion
   provenance into the YAML; do not silently promote a hypothesis to a
   requirement assertion.
4. For `validate`, run the runtime contract validator before collection or
   execution. Any malformed YAML, unknown field, duplicate AUTO ID, missing
   environment declaration, or dangling traceability reference is an error.
5. For `execute`, resolve credentials only from the declared environment and
   ask for confirmation immediately before shared-environment or shared-data
   mutation. TLS verification remains enabled by default.
6. Produce an `automation_implementation` artifact with generated files,
   source coverage, validation evidence, execution boundary, and gaps.

## MVP boundary

- Generate functional API automation with strict contracts, capture, cleanup,
  and provenance-aware assertions.
- Do not generate load tests merely because a response-time assertion exists.
- Treat Locust/performance suites as a separately selected extension.
- Do not copy product-specific authentication, endpoints, tenants, or cleanup
  rules from a reference implementation into Core or this Skill.
