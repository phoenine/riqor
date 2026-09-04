# Environment configuration

Agent-next reads credentials and environment-specific endpoints from a local
repository-root `.env` file.

```bash
cp .env.example .env
```

`.env` is ignored by Git. `.env.example` contains names and non-sensitive
defaults only. Values already present in the process environment take
precedence over the file, which allows CI or a secret manager to inject values
without being overwritten.

The unified `agent-next` CLI loads `.env` before handling a command. Integration
code can use `tools.environment.load_project_environment`; values must never be
copied into Run State, artifacts, logs, or Project Profiles.

Inspect configuration presence without printing values:

```bash
agent-next env --group ZENTAO
```

Supported groups are `ZENTAO`, `GITLAB`, `LARK`, `TEST_SERVER`, `PG`, `CK`,
`RABBITMQ`, `MAGE`, and `REDIS`. `SET` only means that a value is
present; it does not prove credentials or connectivity are valid.

Do not add a group to Run State `environment.checked_groups` merely because its
variables are present. Record it only after the selected integration has
validated the fields and, where applicable, connectivity for the current
target.

The dotenv reader accepts blank lines, comments, `export KEY=VALUE`, quoted
values, and unquoted values. It does not expand shell expressions or variables.
Malformed assignments fail closed with a line-numbered error.

External writes and shared-environment or shared-data operations still require
explicit user confirmation even when all environment variables are configured.
