# 时间戳与时区

## cycle-studio on UTC+8 hosts

cycle-studio may emit `ts` values in local wall time (UTC+8). dataflow often
stores `plcdatetime` without converting timezones. Effects:

- PG timestamps may appear 8 hours ahead of intended UTC display
- UI filters by shift may miss injected data

## Mitigations

**Before send:** adjust JSON `ts` values to UTC if the environment expects UTC
storage.

**When querying:**

```sql
SELECT plcdatetime AT TIME ZONE 'UTC+8' AS ts_cst
FROM envision.tagsrc
WHERE assetuid = 'ASSET:<asset_id>';
```

**After wrong insert into events:** corrective updates may use interval shifts;
only with user confirmation on shared data.

## cycle-factory `timestamp` mode

| Mode | Use when |
|---|---|
| `keep` | Replaying captured timestamps exactly |
| `renew` | Fresh run anchored to now (relative spacing preserved once per load) |
| `random` | Stress / spread tests |

`renew` does not advance time between packets inside one factory invocation.
For multiple distinct cycle times, rerun factory or regenerate JSON between runs.

## Acceptance criteria

When a test asserts UI time alignment, record in the execution note:

- Host timezone used by cycle-studio
- `timestamp` mode in config.toml
- Query timezone used during verification
