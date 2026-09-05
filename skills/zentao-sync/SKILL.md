---
name: zentao-sync
description: Read or synchronize ZenTao requirements, tasks, bugs, test cases, comments, statuses, attachments, and external IDs through zentao-cli, with preview and explicit confirmation before writes.
---

# zentao-sync

Use this skill for ZenTao interaction. Read actions may support intake; write
actions require explicit user confirmation.

## Required Reading

- Use the route and blockers already returned by `agent-next explain`; do not
  reopen the workflow index, selected README, or full Stage Gate audit guide.
- If no routed Run exists, return to `agent-next` to create one.
- `references/zentao-sync-rules.md` before uploading, updating, backfilling, or
  verifying ZenTao test cases or bugs.

## Inputs

- ZenTao IDs or search criteria.
- Confirmed local artifacts to sync.
- Credentials and product/module mappings selected by the Project Profile or
  repository-root `.env` / process environment; never record secret values in
  artifacts or Run State. Use `agent-next env --group ZENTAO` to inspect
  presence without printing values.
- User confirmation for write actions.

## Outputs

- ZenTao read summary.
- Sync plan.
- Upload/update result.
- Backfilled IDs or verification result.
- Traceability between local artifact IDs and ZenTao IDs.

## Do Not

- Do not create, update, delete, upload, or change status without confirmation.
- Do not implement a second ZenTao client; use `zentao-cli`.
- Do not invent unset field values on update; with zentao-cli ≥ 0.1.7 pass only
  fields you intend to change (testcase update still requires `--title`). Follow
  `references/zentao-sync-rules.md`.
- Do not treat a failed search as proof that an item does not exist.
- Do not generate test cases; use `test-case-design`.
