---
name: epvs-zentao-sync
description: ZenTao synchronization skill for agent-next. Use when querying or writing ZenTao requirements, tasks, bugs, test cases, IDs, status updates, comments, uploads, backfills, or verifying ZenTao records after explicit confirmation.
---

# epvs-zentao-sync

Use this skill for ZenTao interaction. Read actions may support intake; write
actions require explicit user confirmation.

## Required Reading

- Current workflow file selected by `agent-next`
- `workflows/stage-gates.md`
- `docs/environment.md`
- `references/zentao-sync-rules.md` before uploading, updating, backfilling, or
  verifying ZenTao test cases or bugs.

## Inputs

- ZenTao IDs or search criteria.
- Confirmed local artifacts to sync.
- Required `ZENTAO_*` environment values.
- User confirmation for write actions.

## Outputs

- ZenTao read summary.
- Sync plan.
- Upload/update result.
- Backfilled IDs or verification result.
- Traceability between local artifact IDs and ZenTao IDs.

## Do Not

- Do not create, update, delete, upload, or change status without confirmation.
- Do not invent unset field values on update; with zentao-cli ≥ 0.1.7 pass only
  fields you intend to change (testcase update still requires `--title`). Follow
  `references/zentao-sync-rules.md`.
- Do not treat a failed search as proof that an item does not exist.
- Do not generate test cases; use `epvs-test-cases`.
