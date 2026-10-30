"""Load the canonical root .env without letting a blank process value hide it."""

import os
from pathlib import Path


def fill_blank_env_from_file(path: Path) -> None:
    """Copy non-empty file values into the process when the current value is missing or blank.

    A non-empty process value still wins. This matters for the Django reloader:
    a parent process that started with OPENROUTER_API_KEY="" passes that empty
    string to the child, and django-environ will not replace it.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if not value:
            continue
        current = os.environ.get(key)
        if current is not None and current.strip():
            continue
        os.environ[key] = value
