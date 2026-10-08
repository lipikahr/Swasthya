"""Test settings.

Uses PostgreSQL when DATABASE_URL is set (as in CI/docker), otherwise falls
back to in-memory SQLite so tests can run anywhere. Production behaviour
must still be checked against PostgreSQL.
"""
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-real-use")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")

from .base import *  # noqa: E402,F401,F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests only
