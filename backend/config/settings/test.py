"""Test settings.

Uses PostgreSQL when DATABASE_URL is set (as in CI/docker), otherwise falls
back to in-memory SQLite so tests can run anywhere. Production behaviour
must still be checked against PostgreSQL.
"""
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-real-use")
# Embeddings use pgvector, so tests use the local Postgres URL when the root
# .env provides one. SQLite remains the fallback for a machine without it.
_env_file = Path(__file__).resolve().parents[3] / ".env"
if "DATABASE_URL" not in os.environ and _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        if _line.startswith("DATABASE_URL="):
            os.environ["DATABASE_URL"] = _line.split("=", 1)[1].strip().strip('"').strip("'")
            break
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")

from .base import *  # noqa: E402,F401,F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests only
