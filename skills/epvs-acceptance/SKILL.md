---
name: epvs-acceptance
description: Release acceptance and version validation skill for agent-next. Use when locking release baselines, collecting release scope, defining acceptance plans, thresholds, blockers, execution evidence, release decisions, or post-release observation.
---

# epvs-acceptance

Use this skill for release acceptance workflows and release-readiness decisions.

## Required Reading

- `workflows/release-acceptance/README.md`
- `workflows/stage-gates.md`
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
- Release scope tracks (`v1`, `v2`, `shared`) for the release bundle.
- Current-version features, bug fixes, release notes, MRs, or commit range.
- Automation and manual test inventory.
- Environment, account, and data scope.

## Outputs

- Release baseline record.
- Scope source completeness and out-of-scope rationale.
- Scope Gap between declared scope, tag diff, deployment/configuration changes,
  and ZenTao items.
- Acceptance plan, thresholds, and blockers.
- Acceptance execution evidence.
- Release decision.
- Post-release observation record when in scope.

## Artifact Workflow

Create release-level acceptance deliverables with `tools/copy_template.py`
under `outputs/releases/<release>/`. Keep feature, bug, test point, test case,
and automation assets under `outputs/v1/`, `outputs/v2/`, or
`outputs/shared/` according to their owning track; release artifacts reference
those assets instead of copying them.

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template acceptance-plan \
  --producer-phase "Acceptance Plan" \
  --artifact-id ACC-PLAN-001 \
  --destination outputs/releases/<release>/acceptance-plan.md
```

```bash
python3 tools/validate_artifact.py \
  --artifact-file outputs/releases/<release>/acceptance-plan.md \
  --artifact-type acceptance_plan \
  --artifact-id ACC-PLAN-001
```

Supplement test cases with `--template test-cases` and
`validate_test_cases.py` (see `epvs-test-cases`). Supplement cases belong under
the owning track, not under `outputs/releases/<release>/`.

## ZenTao Closure

Creating or updating ZenTao acceptance test orders is optional and requires
`epvs-zentao-sync`, `ZENTAO_*` environment checks, and explicit confirmation.
When used, link the ZenTao acceptance order to existing test cases where
possible, then record the ZenTao order/case IDs in traceability and execution
evidence.

## Tool Commands

Check pages/cases consistency before reporting acceptance readiness:

```bash
python3 tools/check_acceptance_assets.py \
  --acceptance-dir outputs/v2/acceptance-tests/<release> \
  --source-root repositories/dev/<repo> \
  --output-dir runs/<run-id>/acceptance-audit
```

The checker is read-only for acceptance assets. It writes Markdown and JSON
reports under the selected output directory and exits non-zero when error-level
issues are found.

## Do Not

- Do not run automation; use `epvs-automation`.
- Do not decide release acceptance before execution evidence and issue
  classification exist.
- Do not accept production-environment release readiness without rollback or
  recovery readiness when required.
- Do not update ZenTao without `epvs-zentao-sync` and confirmation.
- Do not duplicate v1/v2/shared test cases into `outputs/releases/<release>/`;
  reference the owning track assets instead.
