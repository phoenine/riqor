# ePVS compatibility profile

This directory is the public, secret-free boundary for ePVS compatibility. It
does not contain credentials, live endpoints, private repository revisions,
real ZenTao identifiers, historical Run State, or product knowledge.

## Private profile interface

Copy `project.example.yaml` to the private path
`config/projects/epvs.yaml`, then replace the example repository and knowledge
paths with repository-relative local paths. Keep secrets in the local
environment; Project Profile integration config may name a source or mapping,
but must not contain a credential value.

The private profile must continue to satisfy
`schemas/project-profile.schema.json`. Use these public extension points:

- `project.tracks`: retain `v1`, `v2`, and `shared` where legacy routing is required.
- `knowledge`: point to the approved private ePVS knowledge root.
- `repositories.product|automation|tools`: map the old `dev|test|tools` groups.
- `integrations`: select `zentao-sync`, ePVS automation, and data-preparation Skills.
- `environments`: classify local, shared, and production-like targets.
- `policies.require_confirmation`: keep all three protected action classes.
- `extensions.epvs`: keep private module mappings, branch rules, and release policy.

`profile.yaml` records legacy aliases and old output routing for migration
comparison only. New runs use `project_id + tracks` and route artifacts through
the private Project Profile's `artifacts.root`.

Integration `config.environment_group` or `config.environment_groups` names the
variables loaded from the root `.env`; it must never embed their values.

## Verification boundary

The repository tests use controlled, non-sensitive Feature, Bug, and Release
fixtures derived from the historical Run IDs recorded in
`migration-scenarios.yaml`. They prove Profile validation, Skill receipts,
evidence preservation, confirmation blocking, and legacy routing compatibility. They do not prove
access to ZenTao, a shared environment, shared data, private repositories, or
historical ePVS outputs. Those checks require an authorized private run.
