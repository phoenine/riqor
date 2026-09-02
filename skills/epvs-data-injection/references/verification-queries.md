# 注入后验证

Use `.env` PostgreSQL credentials. Replace `<asset_id>` with the numeric asset
id from cycle-studio (tagsrc uses `ASSET:<id>`).

## RabbitMQ queue health

```bash
curl -s -u "${RABBITMQ_USERNAME}:${RABBITMQ_PASSWORD}" \
  "http://${RABBITMQ_HOST}:${RABBITMQ_MGMT_PORT}/api/queues"
```

| Signal | Meaning | Action |
|---|---|---|
| `consumers=0` | dataflow not connected | Restart dataflow consumer / pod |
| `messages_unacknowledged > 0` | Processing stuck | Inspect dataflow logs |
| `messages_ready > 0` | Backlog | Wait or scale consumer |

## tagsrc sample

```sql
SELECT id, dwkey, dwbit, taguid, tagtype, tagmode, statproc,
       cyclelength, cyclenumber, ucounter, plcdatetime
FROM envision.tagsrc
WHERE assetuid = 'ASSET:<asset_id>'
ORDER BY plcdatetime;
```

### statproc flags (common)

| Value | Meaning |
|---|---|
| 0 | New record |
| 256 | GROUPOP/STOP processed |
| 512 | CYCLETIME STOP processed |
| 4096 | Participated in cycle scan |
| 4352 | 4096 + 256 (GROUPOP settled) |
| 4608 | 4096 + 512 (CYCLETIME settled) |
| 1024 | Duplicate |
| 8192 | Pending delete |
| 16384 | Expired |

## ETL process state

```sql
SELECT assetuid, etlprocess, stateprocess, lastupdate
FROM envision.dpe_assetprocess
WHERE assetuid = 'ASSET:<asset_id>';
```

`etlprocess=1` → ETL busy. `etlprocess=0` → idle. Stuck at `1` often indicates
incomplete cycle structure.

## Hierarchy lookup (for manual events debugging)

```sql
SELECT a.id AS assetid, a.name AS assetname,
       a2.id AS stationid, a2.name AS stationname,
       a3.id AS lineid, a3.name AS linename,
       a4.id AS areaid, a4.name AS areaname,
       a5.id AS plantid
FROM envision.article a
LEFT JOIN envision.article a2 ON a.parent_id = a2.id
LEFT JOIN envision.article a3 ON a2.parent_id = a3.id
LEFT JOIN envision.article a4 ON a3.parent_id = a4.id
LEFT JOIN envision.article a5 ON a4.parent_id = a5.id
WHERE a.id = <asset_id>;
```

## MageAI scheduler

```bash
curl -s "${MAGE_BASE_URL}/api/status" | python3 -c "
import sys, json
d = json.load(sys.stdin)['statuses'][0]
print('scheduler:', d['scheduler_status'])
"
```

`stopped` → scheduled pipelines will not run until scheduler restarts or jobs are
triggered manually.

## UI visibility

UI reads events through statistics / ClickHouse. PG `envision.events` alone does
not prove UI data unless `db_sync_events` (or equivalent) has synced to
ClickHouse. See `troubleshooting.md` before closing a UI-visible test.
