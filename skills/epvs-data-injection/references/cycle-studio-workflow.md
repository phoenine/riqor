# cycle-studio 工作流

Working directory: `repositories/tools/epvs-perf-eval/cycle-studio/`

Prerequisites:

- Python virtualenv at `cycle-studio/.venv` (create per repo README if missing)
- PostgreSQL reachability using `.env` `PG_*` variables
- `cycle_studio.py` executable from repo root

## Discover hierarchy

```bash
python3 ./cycle_studio.py list-plants
python3 ./cycle_studio.py list-areas --plant-id <plant_id>
python3 ./cycle_studio.py list-lines --area-id <area_id>
python3 ./cycle_studio.py list-stations --line-id <line_id>
python3 ./cycle_studio.py list-assets --station-id <station_id>
python3 ./cycle_studio.py list-ops --asset-id <asset_id>
python3 ./cycle_studio.py list-metadata --asset-id <asset_id>
python3 ./cycle_studio.py list-state --asset-id <asset_id>
```

Record the chosen `asset_id` and hierarchy IDs in the run note `data_injection:`.

## Initialize a cycle

```bash
python3 ./cycle_studio.py cycle-init --name <cycle_name> --asset-id <asset_id>
```

## Add operations

Supported `--ops-type` values:

| ops-type | Meaning |
|---|---|
| `start` | GROUPSTART |
| `action` | GROUPOP |
| `stop` | GROUPNSTOP |
| `state-faulted` | GROUPSTATE FAULTED |
| `state-blocked` | GROUPSTATE BLOCKED |

Example:

```bash
python3 ./cycle_studio.py cycle-ops-add --name <cycle_name> --index 0 \
  --ops-id <ops_id> --ops-type start
python3 ./cycle_studio.py cycle-ops-add --name <cycle_name> --index 1 \
  --ops-id <ops_id> --ops-type action
python3 ./cycle_studio.py cycle-ops-add --name <cycle_name> --index 2 \
  --ops-id <ops_id> --ops-type stop
```

Indexes must reflect the intended PLC sequence. Incomplete cycles often leave
`etlprocess=1` stuck — see `troubleshooting.md`.

## Generate JSON

```bash
python3 ./cycle_studio.py cycle-generate --name <cycle_name>
```

Output: `cycles/<cycle_name>.json` (and optional CSV). This path is the input to
`cycle-factory`.

## Naming convention

Use descriptive names that include asset or scenario context, for example
`BSOL015-RB01-TEST`. Avoid reusing production cycle names on shared environments
without documenting scope in run state.
