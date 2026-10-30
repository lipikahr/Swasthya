"""Base settings shared by every environment.

Secrets and environment-specific values come from environment variables
(see the root .env.example). Nothing secret is hard-coded here.
"""
import os
from datetime import timedelta
from pathlib import Path

import environ

from config.envfile import fill_blank_env_from_file

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_ROOT = BASE_DIR.parent  # repository root, where the one canonical .env lives

env = environ.Env()
# Load the root .env if it exists (it is git-ignored; the template is the root
# .env.example). A non-empty process value wins. A blank process value does not
# hide a value saved in the file.
fill_blank_env_from_file(REPO_ROOT / ".env")
environ.Env.read_env(REPO_ROOT / ".env", overwrite=False)
os.environ.setdefault("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # lets logout invalidate refresh tokens
    "drf_spectacular",
    # Project apps
    "apps.core",
    "apps.accounts",
    "apps.nutrition",
    "apps.profiles",
    "apps.targets",
    "apps.meals",
    "apps.progress",
    "apps.conversations",
    "apps.agent",
    "apps.kitchen",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: PostgreSQL is the project database. DATABASE_URL looks like
# postgres://user:password@host:5432/dbname
DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email is the login identity, so we use our own User model (apps.accounts).
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=60 * 60 * 24)
FRONTEND_URL = env("FRONTEND_URL", default="http://127.0.0.1:5173")
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Swasthya <noreply@localhost>")

LANGUAGE_CODE = "en-us"
# Timestamps are stored in UTC.
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Secure by default: every endpoint needs a logged-in user unless it
    # explicitly opts out (register, login, health).
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Optional text-agent providers. OpenRouter is used when OPENROUTER_API_KEY is set;
# otherwise Gemini when GEMINI_API_KEY is set; otherwise the rules provider.
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY", default="")
OPENROUTER_BASE_URL = env("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
OPENROUTER_MODEL = env("OPENROUTER_MODEL", default="openai/gpt-4o-mini")
OPENROUTER_HTTP_REFERER = env("OPENROUTER_HTTP_REFERER", default="http://127.0.0.1:5173")
OPENROUTER_APP_TITLE = env("OPENROUTER_APP_TITLE", default="Swasthya")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="models/gemini-3.8-flash")
# Daily calorie goal is met when intake is within this fraction of the active calorie target.
GOAL_CALORIE_TOLERANCE = env("GOAL_CALORIE_TOLERANCE", default="0.05")
SARVAM_API_KEY = env("SARVAM_API_KEY", default="")
SARVAM_STT_URL = env("SARVAM_STT_URL", default="https://api.sarvam.ai/speech-to-text")
SARVAM_STT_MODEL = env("SARVAM_STT_MODEL", default="saaras:v4")
SARVAM_STT_MODE = env("SARVAM_STT_MODE", default="transcribe")
SARVAM_TTS_URL = env("SARVAM_TTS_URL", default="https://api.sarvam.ai/text-to-speech")
SARVAM_TTS_MODEL = env("SARVAM_TTS_MODEL", default="bulbul:v3")

SPECTACULAR_SETTINGS = {
    "TITLE": "Swasthya API",
    "DESCRIPTION": "Backend API. All endpoints except register, login, refresh and health "
    "need an `Authorization: Bearer <access token>` header.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # API docs are the contract for the frontend/agent teams, so they are public.
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_AUTHENTICATION": [],
}
