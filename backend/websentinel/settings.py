"""
Django settings for WebSentinel.

12-factor: all environment-specific configuration is read from environment
variables (via django-environ), with safe local-dev defaults so the project
runs out of the box. Production must override SECRET_KEY, DEBUG, ALLOWED_HOSTS,
and DATABASE_URL.
"""

from pathlib import Path

import environ

# backend/ directory (this file is backend/websentinel/settings.py).
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "0.0.0.0"]),
)

# When running outside Docker, load a repo-root .env if present. Inside Docker,
# variables are injected via compose `env_file`, so this is a no-op there.
environ.Env.read_env(BASE_DIR.parent / ".env")

# --- Core ---------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    # Local
    "core",
    "monitoring",
    "llm",
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

ROOT_URLCONF = "websentinel.urls"

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

WSGI_APPLICATION = "websentinel.wsgi.application"
ASGI_APPLICATION = "websentinel.asgi.application"

# --- Database -----------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://websentinel:websentinel@postgres:5432/websentinel",
    ),
}

# --- Auth ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N / TZ ----------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static / media -----------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ----------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# --- Celery -------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # hard limit (s); fetch/LLM tasks tune this later
CELERY_BEAT_SCHEDULE = {
    "heartbeat": {
        "task": "core.heartbeat",
        "schedule": 30.0,  # seconds; proves the beat -> worker loop
    },
}
# Fetch/render tasks run on a dedicated queue served by the Playwright worker.
CELERY_TASK_ROUTES = {
    "monitoring.render_url": {"queue": "fetch"},
    "monitoring.check_target": {"queue": "fetch"},
}

# --- LLM provider (NVIDIA NIM) ------------------------------------------------
# NVIDIA's API is OpenAI-compatible. Leave NVIDIA_API_KEY unset to disable LLM
# features (the pipeline falls back to rule-based behavior).
NVIDIA_API_KEY = env("NVIDIA_API_KEY", default="")
NVIDIA_BASE_URL = env("NVIDIA_BASE_URL", default="https://integrate.api.nvidia.com/v1")
# Model routing: cheap/fast for routine extraction, stronger for assessment.
LLM_MODEL_EXTRACT = env("LLM_MODEL_EXTRACT", default="meta/llama-3.1-8b-instruct")
LLM_MODEL_ASSESS = env("LLM_MODEL_ASSESS", default="meta/llama-3.3-70b-instruct")
LLM_EMBED_MODEL = env("LLM_EMBED_MODEL", default="nvidia/nv-embedqa-e5-v5")
LLM_MAX_TOKENS = env.int("LLM_MAX_TOKENS", default=1024)
LLM_TEMPERATURE = env.float("LLM_TEMPERATURE", default=0.2)
LLM_TIMEOUT = env.float("LLM_TIMEOUT", default=30.0)
LLM_MAX_RETRIES = env.int("LLM_MAX_RETRIES", default=3)

# --- Semantic diff thresholds -------------------------------------------------
# Prose change is meaningful only when normalized-text similarity is below this
# and (when available) embedding similarity is below the embedding threshold.
DIFF_TEXT_SIM_THRESHOLD = env.float("DIFF_TEXT_SIM_THRESHOLD", default=0.92)
DIFF_EMBED_SIM_THRESHOLD = env.float("DIFF_EMBED_SIM_THRESHOLD", default=0.97)
EMBED_CONTENT_LIMIT = env.int("EMBED_CONTENT_LIMIT", default=4000)

# --- OpenAPI (drf-spectacular) ------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "WebSentinel API",
    "DESCRIPTION": "Web change-intelligence platform — watch targets, snapshots, "
    "detected changes, and alerts.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
