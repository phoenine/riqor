# ePVS 数据注入管道架构

Synthetic PLC data enters the ePVS stack through RabbitMQ and flows through
ETL and event pipelines before UI/statistics services can show cycle results.

## End-to-end flow

```text
cycle-studio (design JSON)
  → cycle-factory (AMQP publish)
    → RabbitMQ (edca.cip-data or configured queue)
      → dataflow (GoogleSQL consumer)
        → INSERT INTO envision.tagsrc (ON CONFLICT DO NOTHING)
          → ETL (processop.py: buildCycle)
            → UPDATE statproc / cyclelength / cyclenumber
              → bg_events_v2 (MageAI)
                → envision.events (PostgreSQL)
                  → db_sync_events → ClickHouse events
                    → statistics service → UI
```

## Component roles

| Stage | Responsibility |
|---|---|
| cycle-studio | Discover hierarchy (plant → asset), define ops sequence, export cycle JSON |
| cycle-factory | Rate-limited publish of PLC packets from JSON to RabbitMQ |
| dataflow | Consume queue, map dwkey, insert tagsrc |
| ETL | Settle groups, compute cyclelength, update statproc flags |
| MageAI pipelines | Scan settled tagsrc windows, write events, sync to ClickHouse |
| UI | Reads through statistics / ClickHouse, not raw tagsrc |

## dataflow INSERT behavior

`GoogleSQL.java` uses `INSERT INTO tagsrc (...) ON CONFLICT DO NOTHING`. Unique
index conflicts are silent at insert time; some conflicts surface later during
ETL `batchUpdateTagsr` updates.

## ETL ordering

`buildCycle` orders by `plcdatetime ASC, tagtype DESC, tagmode DESC`. GROUPSTATE
handling can rewrite `taguid` to match CYCLETIME START groupuid — relevant for
index and Bug #1650 class regressions.

## cyclenumber composition

`processop.py` forms cyclenumber from dwdatetime and plcdatetime millisecond
components. Verification should record both timestamps when debugging mismatches.

## When to use injection vs other tools

| Need | Tool |
|---|---|
| Full pipeline / tagsrc / ETL / events | cycle-studio + cycle-factory (this skill) |
| Replay Siemens e-connect hex logs | `scripts/plc_simulator.py` in same repo |
| Analyze e-connect enhanced logs | `scripts/analyze_logs.py` |

Prefer cycle-factory for structured cycle regression; use plc_simulator only when
replaying captured PLC hex streams is the explicit goal.
