"""Run-state schema version constants shared by writers and validators."""

from __future__ import annotations

from typing import Any


LEGACY_SCHEMA_VERSION = 1
PREVIOUS_SCHEMA_VERSION = 2
CURRENT_SCHEMA_VERSION = 3


def detect_schema_version(state: dict[str, Any]) -> int | None:
    """Treat unversioned historical state as v1; reject malformed versions."""
    value = state.get("schema_version", LEGACY_SCHEMA_VERSION)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
