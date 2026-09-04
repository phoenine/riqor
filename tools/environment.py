from __future__ import annotations

import os
import re
from collections.abc import MutableMapping
from pathlib import Path


ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ENV_GROUPS: dict[str, tuple[str, ...]] = {
    "ZENTAO": (
        "ZENTAO_BASE_URL",
        "ZENTAO_PRODUCT_ID",
        "ZENTAO_USERNAME",
        "ZENTAO_PASSWORD",
        "ZENTAO_API_TOKEN",
    ),
    "GITLAB": (
        "GITLAB_BASE_URL",
        "GITLAB_USERNAME",
        "GITLAB_PASSWORD",
        "GITLAB_PRIVATE_TOKEN",
        "GITLAB_PROJECT_NAMESPACE",
    ),
    "LARK": ("LARK_APP_ID", "LARK_APP_SECRET", "LARK_TENANT_ACCESS_TOKEN"),
    "TEST_SERVER": (
        "TEST_SERVER_NAME",
        "TEST_SERVER_BASE_URL",
        "TEST_SERVER_SSH_HOST",
        "TEST_SERVER_SSH_PORT",
        "TEST_SERVER_SSH_USER",
        "TEST_SERVER_SSH_PASSWORD",
        "TEST_SERVER_SSH_KEY_PATH",
    ),
    "PG": (
        "PG_HOST",
        "PG_PORT",
        "PG_DATABASE",
        "PG_USERNAME",
        "PG_PASSWORD",
        "PG_SSLMODE",
    ),
    "CK": (
        "CK_HOST",
        "CK_PORT",
        "CK_DATABASE",
        "CK_USERNAME",
        "CK_PASSWORD",
        "CK_SECURE",
    ),
    "RABBITMQ": (
        "RABBITMQ_HOST",
        "RABBITMQ_MGMT_PORT",
        "RABBITMQ_AMQP_PORT",
        "RABBITMQ_USERNAME",
        "RABBITMQ_PASSWORD",
        "RABBITMQ_QUEUE",
    ),
    "MAGE": ("MAGE_BASE_URL", "MAGE_USERNAME", "MAGE_PASSWORD"),
    "REDIS": ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"),
}


class EnvironmentFileError(ValueError):
    """Raised when a local dotenv file cannot be parsed safely."""


def _parse_value(raw: str, *, line_number: int) -> str:
    value = raw.strip()
    if not value:
        return ""
    if value[0] in {'"', "'"}:
        quote = value[0]
        if len(value) < 2 or value[-1] != quote:
            raise EnvironmentFileError(
                f".env line {line_number}: unterminated quoted value"
            )
        return value[1:-1]
    comment = re.search(r"\s+#", value)
    return value[: comment.start()].rstrip() if comment else value


def load_project_environment(
    root: Path,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> list[str]:
    """Load root/.env without replacing values already supplied by the process."""

    target = environ if environ is not None else os.environ
    path = root / ".env"
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EnvironmentFileError(f"cannot read {path}: {exc}") from exc

    loaded: list[str] = []
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise EnvironmentFileError(f".env line {line_number}: expected KEY=VALUE")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY.fullmatch(key):
            raise EnvironmentFileError(
                f".env line {line_number}: invalid variable name {key!r}"
            )
        value = _parse_value(raw_value, line_number=line_number)
        if key not in target:
            target[key] = value
            loaded.append(key)
    return loaded


def environment_group_status(
    group: str,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> list[tuple[str, bool]]:
    target = environ if environ is not None else os.environ
    variables = ENV_GROUPS.get(group.upper())
    if variables is None:
        raise ValueError(f"unknown environment group: {group}")
    return [(name, bool(target.get(name, "").strip())) for name in variables]
