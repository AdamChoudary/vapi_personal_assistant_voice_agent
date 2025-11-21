"""
Helpers for loading Google service account credentials in flexible formats.

Supports:
- Absolute/relative file paths
- Paths prefixed with '@' (Fly secrets syntax)
- Raw JSON content (plain or base64 encoded) stored directly in env vars
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path
from typing import Final

_CACHE: dict[str, str] = {}
_TMP_PREFIX: Final[str] = "google-service-account"


def _write_temp(content: str) -> str:
    tmp = tempfile.NamedTemporaryFile("w", delete=False, prefix=_TMP_PREFIX, suffix=".json")
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return tmp.name


def resolve_service_account_path(raw_value: str) -> str:
    if not raw_value:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not set.")

    cached = _CACHE.get(raw_value)
    if cached:
        return cached

    candidate = raw_value.strip()
    candidate = candidate.strip("'\"")
    if candidate.startswith("@"):
        candidate = candidate[1:].strip()

    # Try raw JSON (plain or base64) first
    for possible in (candidate, _maybe_base64(candidate)):
        if possible is None:
            continue
        try:
            parsed = json.loads(possible)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        resolved = _write_temp(json.dumps(parsed))
        _CACHE[raw_value] = resolved
        return resolved

    # Treat as file path if JSON parse failed
    path_candidate = Path(candidate)
    if path_candidate.exists():
        resolved = str(path_candidate)
        _CACHE[raw_value] = resolved
        return resolved

    raise FileNotFoundError(
        "Service account credentials not found. Provide a file path or inline JSON content."
    )


def _maybe_base64(value: str) -> str | None:
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except Exception:
        return None
    return decoded.strip()

