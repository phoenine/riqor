# Release Acceptance Workflow

Use for release version, tag, deployment environment, validation window, or full regression.

**Triggers:** release version, tag, branch, environment, full automation request.

## Outcomes

Primary: release bundle baseline, resolved scope, acceptance plan, execution, decision, acceptance report.

Optional: supplement cases, issue list, test-management updates, post-release observation.

## Deliverable Routing

Release acceptance is managed as a release bundle. Use
`<artifact-root>/releases/<release-version>/` for release-level orchestration and
decision artifacts. Never write release-level deliverables under `runs/`.

Feature, bug, test point, test case, automation, and execution evidence assets
remain under their Project Profile scope and owning track. Release artifacts reference those assets; they do not copy
or fork test cases into the release directory.

| Phase | Template | Artifact type | Example path |
|---|---|---|---|
| Acceptance Plan | `acceptance-plan` | `acceptance_plan` | `<artifact-root>/releases/<release>/acceptance-plan.md` |
| Acceptance Execution | `execution-record` | `execution_record` | `<artifact-root>/releases/<release>/execution-record.md` |
| Release Decision | `acceptance-report` | `acceptance_report` | `<artifact-root>/releases/<release>/acceptance-report.md` |
| (supplement) | `test-cases` | `test_cases` | `<artifact-root>/<scope>/<track>/test-cases.md` |

Validate: `validate_artifact.py`, `validate_test_cases.py`, `stage_gate.py`.

Recommended release bundle layout:

```text
<artifact-root>/releases/<release>/
  baseline.md
  scope.md
  priority-risk-ranking.md
  acceptance-plan.md
  execution-record.md
  acceptance-report.md
  observation.md
  tracks/
    <track>.md
```

`tracks` records ownership for a single artifact. For release acceptance,
record bundle coverage with project-defined `release_scope_tracks`, for example:

```yaml
release_scope_tracks:
  - web
  - backend
```

## Lazy-load phase docs

```bash
python3 tools/phase_doc.py --entry release-acceptance --phase "<phase>"
```

Set `state.workflow` to `workflows/release-acceptance/README.md`.

| # | Phase | Doc |
|---|---|---|
| 1 | Release Baseline | `phases/01-release-baseline.md` |
| 2 | Scope Collection | `phases/02-scope-collection.md` |
| 3 | Acceptance Plan | `phases/03-acceptance-plan.md` |
| 4 | Acceptance Execution | `phases/04-acceptance-execution.md` |
| 5 | Release Decision | `phases/05-release-decision.md` |
| 6 | Optional Post-release Observation | `phases/06-optional-post-release-observation.md` |

## Scope Authority

Use tag diff as the scope initializer, not the final authority.

Resolved release scope must reconcile:

- Declared release notes, external requirement, task, and bug records, and release owner input.
- Tag diff from previous release tag to current release tag.
- Deployment, configuration, migration, feature flag, and dependency changes.
- Known bugs, accepted carry-over items, and explicitly excluded work.

Record mismatches as `Scope Gap` items. Examples:

- A release note item has no matching tag diff evidence.
- Tag diff shows module changes with no declared requirement, bug, task, or
  accepted technical change.
- Deployment/configuration/migration scope exists outside source commits.

## Priority And Risk

Keep release acceptance priority separate from risk:

- `Risk` = impact severity and likelihood if the item fails.
- `Acceptance Priority` = execution order and depth for this release.

Release plans should include both fields for each scope item or track summary.

## Test-management closure

test-management acceptance orders may be created or updated only after explicit
confirmation and the `zentao-sync` skill is loaded. The external order should
link to existing local or external test cases where possible, then backfill the
external order/case IDs into release traceability. This closes the chain:

`Release Scope -> Test Case -> Test-management Acceptance Order -> Execution Evidence -> Acceptance Report`.
