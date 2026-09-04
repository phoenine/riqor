# Stage Gates

Stage gates define the minimum evidence required before a workflow phase can be
presented as complete or allowed to continue. Gates are fail-closed: missing
state, missing evidence, missing skill records, or missing confirmation blocks
the next phase.

## Machine Enforcement

Pass conditions in workflow files are **human guidance only**.
`tools/stage_gate.py` checks **whether the gate passes**. When prose and machine
rules differ, **`stage_gate.py` wins** for pass/fail.

Run the gate before presenting a phase as complete:

```bash
python3 tools/stage_gate.py --state runs/<run-id>/state.json
```

Use `--global-only` to run only cross-phase checks. By default, the tool also
applies the phase rule for the current `entry` + `phase`.

Every phase also inherits [Global Gates](#global-gates) (router skill, skill
receipts, confirmations, and so on). The table below lists **phase-specific**
machine rules only.

The global gate runs `tools/traceability_lint.py` against current Run artifacts.
Duplicate definitions, dangling `REQ/RISK/TP/TC/AUTO/BR/Q` references, and undefined
`RA` references fail closed.

### Machine Rules By Phase

Authoritative implementation: `tools/stage_gate.py` → `PHASE_RULES`.

| Entry | Phase | Machine-enforced (phase-specific) |
|---|---|---|
| feature-quality | Intake | `requirement-analysis`; `intake_input:`; `knowledge_plan` resolved; knowledge |
| feature-quality | Requirement Specification | `requirement-analysis`; artifact `requirement_spec`; knowledge |
| feature-quality | Risk Analysis | `test-analysis`; artifact `risk_analysis`; knowledge; repository evidence |
| feature-quality | Test Design | `test-analysis`, `test-case-design`; artifact `test_points`; test cases must cite ready test points; knowledge |
| feature-quality | Optional Case Sync Or Generation | Optional; Project Profile integration Skill, `automation`, or selected implementation Skill; `external_sync:`, `automation_classification`, `automation_implementation`, or skip |
| feature-quality | Optional Case Execute | Optional; `test-execution` when cases run, plus `automation` or `test-case-design`; normalized `execution_record` or `data_injection:` or skip |
| feature-quality | Optional Bug Report | Optional; `reporting`; `bug_report` or skip |
| feature-quality | Optional Test Report | Optional; `reporting`; artifact `run_summary`; traceability or skip |
| bug-regression | Bug Intake | `requirement-analysis`; `bug_intake:`; `bug_surface:`; knowledge |
| bug-regression | Change Scope | `test-analysis`; artifact `change_scope`; knowledge; repository evidence |
| bug-regression | Impact Analysis | `test-analysis`; artifact `risk_analysis`; knowledge; repository evidence |
| bug-regression | Coverage Match | `test-case-design`, `automation`; artifact `coverage_match`; knowledge |
| bug-regression | Decision Gate | `test-case-design`, `automation`; `decision_path:` |
| bug-regression | Regression Plan | `test-case-design`, `automation`, `reporting`; artifact `regression_plan`; `regression_strategy:`; `test_cases` when `decision_path: supplement_cases` |
| bug-regression | Execution | Optional; `test-execution` when cases run, plus `automation` or `test-case-design`; normalized `execution_record` or `data_injection:` or skip |
| bug-regression | Regression Report | `reporting`; artifact `regression_report`; traceability |
| release-acceptance | Release Baseline | `release-acceptance`; `release_baseline:`; `release_scope_tracks`; `environment.target`; knowledge; repository evidence |
| release-acceptance | Scope Collection | `release-acceptance`, `requirement-analysis`, `test-analysis`; `release_scope:`; `release_scope_tracks`; knowledge |
| release-acceptance | Acceptance Plan | `release-acceptance`, `test-case-design`, `automation`; artifact `acceptance_plan`; knowledge |
| release-acceptance | Acceptance Execution | `automation`, `release-acceptance`, and `test-execution` when cases run; `automation_execution_plan:` or `automation_execution_skip:`; normalized `execution_record` or `execution_evidence:` / `data_injection:` / `optional_skip:` |
| release-acceptance | Release Decision | `release-acceptance`, `reporting`; artifact `acceptance_report`; `release_decision:`; traceability |
| release-acceptance | Optional Post-release Observation | Optional; `release-acceptance`, `reporting`; or skip |

Skip optional phases with `optional_skip:<phase>: <reason>` in `notes[]`.

Some phases also require note prefixes in `notes[]` — for example
Machine: `intake_input:` on feature-quality Intake; `bug_intake:` /
`bug_surface:` on bug-regression Bug Intake; `decision_path:` on Decision Gate.

### Note Prefixes

Evidence not yet modeled as structured fields can be recorded in `notes[]`:

| Prefix | Use |
|---|---|
| `intake_input:` | Feature-testing intake source |
| `bug_intake:` | Bug-regression intake source |
| `bug_surface:` | Bug risk/coverage classification; output routing comes from Project Profile artifact root, scope, and owning track |
| `knowledge_not_applicable:` | Phase read no knowledge files |
| `repository_not_applicable:` | Phase inspected no repositories |
| `decision_path:` | Bug-regression decision gate selection |
| `regression_strategy:` | Bug-regression execution strategy |
| `data_injection:` | Project-selected test-data preparation evidence |
| `external_sync:` | Result from a Project Profile-selected test-management integration Skill |
| `case_design_receipt:` | Confirms `test-case-design-methodology.md` was read before writing test cases |
| `coverage_review_receipt:` | Confirms `coverage-review-rules.md` was read before finalizing test cases or coverage match |
| `case_rules_receipt:` | Confirms `case-writing-rules.md` was read before writing test cases |
| `release_baseline:` | Release version/environment lock record |
| `release_scope:` | Release scope collection summary |
| `scope_gap:` | Release scope mismatch between declared scope, tag diff, deployment/config, migration, or external records |
| `automation_execution_plan:` | Release acceptance API/Web automation routing and planned/confirmed commands |
| `automation_execution_skip:` | Explicit reason a release automation target cannot be executed |
| `execution_evidence:` | Acceptance or regression execution evidence |
| `external_acceptance_order:` | External test-management acceptance order and linked existing test cases |
| `release_decision:` | Final release decision record |
| `optional_skip:<phase>:` | Optional phase intentionally skipped |

## Global Gates

Every phase must satisfy these checks:

| Check | Required Evidence |
|---|---|
| Run state exists | `runs/<run-id>/state.json` or equivalent durable state. |
| Run state version current | `schema_version` matches the current schema contract. Legacy states require explicit migration. |
| Project and owning tracks selected | Runs record `project_id` and one or more Project Profile `tracks`. |
| Release scope tracks selected | Release-acceptance baseline and scope phases record one or more Project Profile `release_scope_tracks`. |
| Workflow selected | `entry`, `workflow`, and `phase` are recorded. |
| Skills declared | `required_skills` includes the router skill and all phase-specific skills. |
| Skills loaded | `skill_receipts` contains every required skill for the current phase; its repo-relative path exists and its sha256 matches the current file. |
| Knowledge used | Relevant `knowledge/` files or required skill references used by conclusions are listed in `knowledge_used`, their repo-relative paths exist, or the phase records a `knowledge_not_applicable:` note in `notes[]`. |
| Repository evidence | Required repositories include path, revision, and files or commits actually inspected, or the phase records a `repository_not_applicable:` note when no repo was read. |
| Environment checked | Required `.env` groups are checked before remote reads or execution. |
| Artifacts tracked | Generated artifacts are listed with path and producing phase. |
| Traceability valid | Internal `REQ/RISK/TP/TC/AUTO/BR/Q` endpoints resolve in current Run artifacts; duplicate, dangling, and undefined `RA` references fail. |
| Confirmations tracked | Required user confirmations are recorded before side-effect actions. |

## Global Blocking Actions

These actions must never run before explicit user confirmation:

- External test-management create, update, delete, upload, or status change.
- test-management acceptance order create/update or case association changes.
- Bug create, close, reopen, or assignment change.
- Test data mutation in shared environments.
- Automation execution against shared or production-like environments.
- SSH access to test servers.
- Deployment, image, chart, or environment replacement.
- Shared knowledge update.
- Shared repository configuration update.

## Artifact Rules

- If a template exists for an artifact type, the artifact must be created from
  that template via `tools/copy_template.py`. Hand-written Markdown without
  Required body sections fail `stage_gate.py`.
- `tools/stage_gate.py` validates every registered artifact file:
  - `test_cases` → `validate_test_cases.py` (template sections,
    `TC-00N` headings, test-case design / coverage review / case-writing
    receipts)
  - all other templated types → `validate_artifact.py` (template sections,
    `artifact_type`, template section markers)
- Every generated artifact must record minimal metadata: `id`, `type`,
  `producer_phase`, `source_artifacts`, `evidence`, and `validation`.
- A phase can complete without an artifact only when the workflow explicitly
  marks the artifact as not required and explains why.

## Traceability Rules

- Every artifact must reference its upstream artifact IDs.
- The expected chain is:
  `Requirement -> Risk -> Test Point -> Test Case -> Automation -> Execution -> Bug -> Report`.
- Optional steps may be absent, but the report must still show the chain that
  exists.

## Knowledge Rules

- Requirement, risk, test point, test case, acceptance, and report phases must
  read relevant knowledge first.
- Knowledge is reusable context, not source evidence.
- Gates check `knowledge_used`, not only `knowledge_read`.
- Proposed knowledge updates must be stored as proposals until the user confirms
  the change.
- A phase that reads no knowledge must record a `knowledge_not_applicable:`
  note in `notes[]`.
- **AI-first routing**: navigate from the Project Profile knowledge index and
  each page's `related[].path`; do not rely on wikilinks or guessed filenames.
- `knowledge_used[].path` must match an actually opened file under
  `knowledge/`.

## Repository Rules

- Source analysis phases prefer Project Profile product repositories over
  remote inspection.
- Automation phases use Project Profile automation repositories.
- Data setup phases use Project Profile tool repositories.
- Each repository record must include path and one of branch, tag, commit, or
  explicit local working tree state.
- Repository evidence must list files, commits, or other concrete references
  inspected for the phase.

## Fail-Closed Rules

Fail the gate when any of these are true:

- Required skill was not loaded.
- A required skill receipt belongs to another phase, points to a missing file, or its sha256 is stale.
- `workflow` does not match the selected `entry`.
- The immediately preceding phase has no passed gate result.
- Repository evidence names no matching repository record, or that record has no revision/working-tree state.
- Required repository revision is missing.
- Required knowledge use is missing and no `knowledge_not_applicable:` note is recorded in `notes[]`.
- Required `.env` group is missing.
- Artifact path is missing for a required artifact.
- Source evidence is required but absent.
- Side-effect action lacks explicit confirmation.
- A phase attempts to skip its declared predecessor without recorded rationale.
- The workflow entrypoint changes mid-run without updating run state.
