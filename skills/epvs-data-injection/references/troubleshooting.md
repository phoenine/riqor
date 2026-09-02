# 管道排查

## Symptom → cause → action

| Symptom | Likely cause | Action |
|---|---|---|
| tagsrc 0 rows, RabbitMQ has ready messages | dataflow slow or down | Wait; check dataflow logs / restart pod |
| RabbitMQ unack backlog | dataflow processing failure | Restart dataflow; inspect negativeMetaCache |
| tagsrc rows present, events empty | bg_events_v2 not running | Check MageAI scheduler; see verification-queries |
| GROUPSTART/GROUPNSTOP missing | negativeMetaCache in dataflow | Restart dataflow pod (5 min TTL cache) |
| CYCLETIME has cyclelength, UI empty | events not in ClickHouse | Run db_sync_events pipeline; do not assume PG INSERT is enough |
| etlprocess stuck at 1 | Incomplete cycle ops sequence | Fix cycle-studio ops; resend |
| UI wrong time by ~8h | Timezone / renew semantics | See timezone-notes.md |

## negativeMetaCache

dataflow caches dwmap misses in Caffeine (≈5 min TTL, ~20K entries). After
metadata changes, restart dataflow to avoid false negatives.

## RabbitMQ flow control

High `messages_unacknowledged` means consumers fetched but did not ACK. Repeated
NACK with requeue can loop. Deleting a queue disconnects consumers — restart
dataflow after queue recovery.

## Manual events INSERT

Manual `INSERT INTO envision.events` from tagsrc can help DB-level verification
but **does not** satisfy UI checks. UI path:

```text
tagsrc → bg_events_v2 → events(PG) → db_sync_events → events(ClickHouse) → UI
```

Use manual SQL only when explicitly validating PG-side ETL, not as UI sign-off.

## Index / Bug #1650 class issues

When validating unique index or GROUPSTATE behavior, capture:

- tagsrc rows before and after ETL
- statproc transitions per taguid
- Whether grpstate maps GROUPSTATE taguid to CYCLETIME START taguid

Cross-check with `knowledge/` pages on paypoint and cycle-time if the regression
ties to product semantics.
