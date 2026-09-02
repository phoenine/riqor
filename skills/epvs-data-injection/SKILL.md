---
name: epvs-data-injection
description: Prepare and inject synthetic PLC cycle data into the ePVS pipeline via epvs-perf-eval (cycle-studio and cycle-factory). Use when shared test data must be built before UI, pipeline, ETL, or index validation; when verifying tagsrc/events flow; or when regression needs RabbitMQ → dataflow → tagsrc → ETL → events coverage.
---

# epvs-data-injection

Use this skill to design, generate, send, and verify synthetic PLC cycle data.
It coordinates the tool repository under `repositories/tools/epvs-perf-eval/`; it
does not run API/Web automation (see `epvs-automation`).

## Required Reading

- Current workflow file selected by `agent-next`
- `workflows/stage-gates.md`
- `docs/repositories.md` (Tools Repositories)
- `docs/environment.md` (`.env` variable groups)
- `references/pipeline-architecture.md` before planning injection scope
- `references/cycle-studio-workflow.md` when building cycle JSON
- `references/cycle-factory-config.md` before sending to RabbitMQ
- `references/verification-queries.md` after send
- `references/troubleshooting.md` when pipeline health is unclear
- `references/timezone-notes.md` when timestamps or UI visibility look wrong

## Tool Repository

Local mirror (from the ePVS Project Profile tools repository configuration):

```text
repositories/tools/epvs-perf-eval/
├── cycle-studio/     # Design cycles, list assets, export JSON/CSV
└── cycle-factory/    # Send cycle JSON to RabbitMQ (Rust binary)
```

Record the tools repository in run state before mutating shared data:

```bash
python3 tools/run_state.py \
  --run-id <run-id> \
  --repository kind=tools,name=epvs-perf-eval,path=repositories/tools/epvs-perf-eval
```

## Environment

Read credentials only from `.env`. Typical groups:

| Group | Variables | Purpose |
|---|---|---|
| PostgreSQL | `PG_HOST`, `PG_PORT`, `PG_DATABASE`, `PG_USERNAME`, `PG_PASSWORD`, `PG_SSLMODE` | tagsrc / events verification |
| RabbitMQ | `RABBITMQ_HOST`, `RABBITMQ_AMQP_PORT`, `RABBITMQ_MGMT_PORT`, `RABBITMQ_USERNAME`, `RABBITMQ_PASSWORD`, `RABBITMQ_QUEUE` | cycle-factory destination |
| MageAI | `MAGE_BASE_URL`, `MAGE_USERNAME`, `MAGE_PASSWORD` | scheduler / pipeline status |

Set `environment.required_groups` and `environment.checked_groups` for every
group you will use. Set `environment.target` to the test environment name.

## Confirmation Gates

`epvs-perf-eval` is configured with `confirmation_required_for:
shared-data-mutation`. Before sending cycles or running tools that write shared
pipeline data:

1. Present the target environment, asset, cycle name, rate, and duration.
2. Record a confirmation in run state (`status=confirmed` only after user approval).
3. Record repository evidence and commands in `notes[]` with prefix `data_injection:`.

Example note:

```text
data_injection: asset=ASSET:12345 cycle=BSOL015-RB01-TEST queue=edca.cip-data rate=10 duration=10s
```

## Workflow Summary

### 1. Activate cycle-studio environment

```bash
cd repositories/tools/epvs-perf-eval/cycle-studio
source .venv/bin/activate
export PGHOST="$PG_HOST" PGPORT="$PG_PORT" PGUSER="$PG_USERNAME" \
       PGPASSWORD="$PG_PASSWORD" PGDATABASE="$PG_DATABASE" PGSSLMODE="$PG_SSLMODE"
```

### 2. Resolve target asset and metadata

```bash
python3 ./cycle_studio.py list-plants
python3 ./cycle_studio.py list-areas --plant-id <id>
python3 ./cycle_studio.py list-lines --area-id <id>
python3 ./cycle_studio.py list-stations --line-id <id>
python3 ./cycle_studio.py list-assets --station-id <id>
python3 ./cycle_studio.py list-ops --asset-id <id>
```

See `references/cycle-studio-workflow.md` for `cycle-init`, `cycle-ops-add`,
and `cycle-generate`.

### 3. Send with cycle-factory

```bash
cd repositories/tools/epvs-perf-eval/cycle-factory
./target/release/cycle-factory \
  -i ../cycle-studio/cycles/<name>.json \
  -c config.toml
```

Align `config.toml` with `.env` RabbitMQ settings. See
`references/cycle-factory-config.md`.

### 4. Verify

- RabbitMQ queue health (consumers, unack, ready) — see `references/verification-queries.md`
- `envision.tagsrc` rows for target asset
- `envision.dpe_assetprocess` ETL state
- events / UI path only after MageAI pipelines run — see `references/troubleshooting.md`

Record verification queries and outcomes in run state notes or execution record.

## Outputs

- Data injection plan (asset, cycle structure, send parameters).
- Commands actually run (cycle-studio + cycle-factory).
- Verification summary (tagsrc, queue, ETL, events/UI if in scope).
- `data_injection:` note and confirmation receipt when shared data was mutated.

## Do Not

- Do not embed credentials in artifacts, skills, or run state.
- Do not invent ad-hoc send scripts when `cycle-factory` can send the cycle.
- Do not mutate shared environments without user confirmation.
- Do not treat manual `INSERT INTO envision.events` as sufficient for UI proof
  without ClickHouse sync — see `references/troubleshooting.md`.
- Do not run automation; delegate execution to `epvs-automation` after data is ready.

## Handoff

After data is injected and verified, return to the workflow phase owner:

- `epvs-automation` for automated case execution against the prepared environment.
- `epvs-reporting` for execution records and evidence summaries.
- `epvs-acceptance` when validating release-scope scenarios.
