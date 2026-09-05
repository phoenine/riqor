---
name: release-acceptance
description: Release acceptance and version validation skill for agent-next. Use when locking release baselines, collecting release scope, defining acceptance plans, thresholds, blockers, execution evidence, release decisions, or post-release observation.
---

# release-acceptance

Use this skill for release acceptance workflows and release-readiness decisions.

## Required Reading

- Use the route and blockers already returned by `agent-next explain`; do not
  reopen the workflow index, selected README, or full Stage Gate audit guide.
- If no routed Run exists, return to `agent-next` to create one.
- `references/acceptance-pages-cases.md` when designing acceptance pages,
  acceptance cases, SPA validation units, or pages/cases synchronization.
- `references/version-source-sync.md` when release acceptance depends on local
  repository checkout, release tags, source refresh, or regenerated assets.
- `references/acceptance-asset-checks.md` before checking or reporting
  pages/cases consistency, source evidence, or acceptance asset quality.
- Relevant release knowledge under `knowledge/`

## Inputs

- Release version, tag, branch, or environment.
- Release type and candidate/freeze status.
- Project-defined release scope tracks for the release bundle.
- Current-version features, bug fixes, release notes, MRs, or commit range.
- Automation and manual test inventory.
- Environment, account, and data scope.

## Outputs

- Release baseline record.
- Scope source completeness and out-of-scope rationale.
- Scope Gap between declared scope, tag diff, deployment/configuration changes,
  and project-selected issue or test-management items.
- Acceptance plan, thresholds, and blockers.
- Acceptance execution evidence.
- Release decision.
- Post-release observation record when in scope.

## Artifact Workflow

Create release-level acceptance deliverables with `tools/copy_template.py`
under the Project Profile artifact root. Keep feature, bug, test point, test
case, and automation assets under their owning scope and track; release
artifacts reference those assets instead of copying them.

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template acceptance-plan \
  --producer-phase "Acceptance Plan" \
  --artifact-id ACC-PLAN-001 \
  --destination <artifact-root>/releases/<release>/acceptance-plan.md
```

```bash
python3 tools/validate_artifact.py \
  --artifact-file <artifact-root>/releases/<release>/acceptance-plan.md \
  --artifact-type acceptance_plan \
  --artifact-id ACC-PLAN-001
```

Supplement test cases with `--template test-cases` and
`validate_test_cases.py` (see `test-case-design`). Supplement cases belong under
the owning scope, not inside the release bundle directory.

## Test-management closure

Creating or updating an external acceptance order is optional and requires the
Project Profile-selected integration Skill, environment checks, and explicit
confirmation. Link the external order to existing test cases where possible,
then record returned order/case IDs in traceability and execution evidence.

## Project-specific checks

Load a Project Profile Skill when a project requires generated acceptance
pages, repository refresh, or a dedicated asset checker. Do not assume that a
project-specific checker exists in the generic repository.

## Do Not

- Do not run automation; use `automation`.
- Do not decide release acceptance before execution evidence and issue
  classification exist.
- Do not accept production-environment release readiness without rollback or
  recovery readiness when required.
- Do not update an external test-management platform without its selected
  integration Skill and confirmation.
- Do not duplicate track-owned test cases into the release bundle; reference
  the owning scope and track assets instead.
