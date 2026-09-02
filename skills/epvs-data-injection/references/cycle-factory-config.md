# cycle-factory 配置与发送

Working directory: `repositories/tools/epvs-perf-eval/cycle-factory/`

Build the binary once per machine (or use pre-built binary from project README /
MinIO mirror documented in repo):

```bash
cargo build --release
```

## CLI

```bash
./target/release/cycle-factory -h
./target/release/cycle-factory \
  -i ../cycle-studio/cycles/<cycle_name>.json \
  -c config.toml
```

`-i` accepts a single JSON file or a directory. Use `-v` for verbose logging.

## config.toml

Start from `config.toml.example`. Map RabbitMQ settings from `.env`:

```toml
[rabbitmq]
host = "<RABBITMQ_HOST>"
port = <RABBITMQ_AMQP_PORT>
username = "<RABBITMQ_USERNAME>"
password = "<RABBITMQ_PASSWORD>"
queue = "<RABBITMQ_QUEUE>"          # default pipeline queue: edca.cip-data

[cycle]
strategy = "order"                    # order | random
timestamp = "renew"                   # keep | renew | random
rate = 10                             # packets per second
duration = 10                         # seconds → total packets ≈ rate × duration
```

| timestamp | Behavior |
|---|---|
| `keep` | Use timestamps from JSON as-is |
| `renew` | Anchor to current time, preserve relative offsets (applied once per JSON load) |
| `random` | Current time plus random offsets |

## Multiple sends

`timestamp = "renew"` applies when the JSON is loaded, not on every packet in a
loop. To produce multiple distinct cycle times, run `cycle-factory` multiple
times with pauses, or regenerate JSON between runs. See `timezone-notes.md`.

## Multi-send shell pattern

```bash
for i in 1 2 3 4 5; do
  ./target/release/cycle-factory \
    -i ../cycle-studio/cycles/<cycle_name>.json \
    -c config.toml
  sleep 5
done
```

Record each run in `data_injection:` notes when confirming shared mutation.
