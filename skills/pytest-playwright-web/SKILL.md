---
name: pytest-playwright-web
description: Generate and validate traceable project-level Playwright pytest automation using the rigorpath_web_test runtime. Use when Web test points or cases should become executable browser automation and the active Project Profile selects this Skill or runtime.
---

# pytest-playwright-web

Use this implementation Skill only after `automation` classifies coverage as
Web automation and the active Project Profile selects this Skill or explicitly
selects the `rigorpath_web_test` runtime.

## Required inputs

- Verified user flow and observable UI evidence. Never invent selectors or
  navigation paths from requirement wording alone.
- `test_points` and `test_cases`; retain their exact IDs in test metadata or
  docstrings.
- Target automation repository, product repository evidence, and environment
  policy from the Project Profile.
- An immutable `rigor-test` runtime revision selected by the Project Profile.

Read [references/framework-contract.md](references/framework-contract.md) before
creating or restructuring a Web automation repository. Read
[references/testcase-patterns.md](references/testcase-patterns.md) before writing
or changing Playwright tests.

## Workflow

1. Classify the requested operation as `bootstrap`, `generate`, `validate`, or
   `execute`. A request may contain more than one operation.
2. Reuse the declared Web automation repository and its Page/Component Objects.
   Bootstrap only when the Project Profile declares an empty Web automation
   repository and explicitly selects this implementation. Run `agent-next
   prepare-automation --automation-target web` with the ready classification,
   test-case, implementation, and Run IDs; Core resolves this Skill's
   `provider.yaml` and selected repository. When invoking the scaffold directly,
   pass explicit
   `--destination`, `--project-name`, `--runtime-url`, and immutable
   `--runtime-revision` values; it refuses to overwrite a non-empty destination.
3. For `generate`, implement the smallest observable browser flow that proves
   the testcase oracle. Preserve `REQ/BR/RISK/TP/TC` provenance and keep product
   selectors, authentication, data preparation, and routes in the generated
   business repository.
4. Use the runtime's `web_page` fixture for ordinary pages. Register manually
   created pages with `web_observer.observe(page)` before fallible setup so
   failures retain screenshots, redacted URL metadata, console logs, and page
   errors.
5. For `validate`, collect the narrow test selection, run framework unit tests
   that do not require a shared environment, and inspect failure artifacts.
   Collection success alone is not execution evidence.
6. For `execute`, load endpoints and credentials only from the declared
   environment. Ask for confirmation immediately before using a shared
   environment or mutating shared data.
7. Record implementation files, source coverage, validation commands, runtime
   revision, execution boundary, and remaining gaps in the
   `automation_implementation` artifact.

## MVP boundary

- Use Playwright's locators and assertions rather than creating a parallel UI
  automation DSL.
- Do not copy product-specific Page Objects or cases from a reference project
  into the runtime or this Skill.
- Treat Allure, visual-model canvas interaction, component-library helpers, and
  CI providers as optional project extensions.
- A missing required element, failed click, unexpected navigation, or failed
  assertion is a failure, not an environmental skip.
