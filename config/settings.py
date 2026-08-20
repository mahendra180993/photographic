"""
Django settings for the MS Photo Studio photography studio platform.

Reads configuration from environment variables (and an optional .env file)
so the same code base runs locally on SQLite and in production on Postgres.
"""

from pathlib import Path
from urllib.parse import urlparse
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Small env helpers
# ---------------------------------------------------------------------------
def env(key, default=None):
    value = os.environ.get(key)
    return default if value is None or value == "" else value


def env_bool(key, default=False):
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key, default=0):
    try:
        return int(env(key, default))
    except (TypeError, ValueError):
        return default


def env_list(key, default=None):
    raw = os.environ.get(key)
    if not raw:
        return list(default or [])
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-ms-photo-studio-development-key-do-not-use-in-production",
)
DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"] if DEBUG else [],
)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])


def _register_site_origin(site_url):
    """Add a host / origin from a full URL or bare hostname."""
    if not site_url:
        return
    raw = site_url if "://" in site_url else f"https://{site_url}"
    parsed = urlparse(raw)
    host = parsed.netloc or parsed.path.split("/")[0]
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)
    origin = raw.rstrip("/")
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)


# Netlify serves static files and proxies HTML/API traffic to a Django backend.
NETLIFY = env_bool("NETLIFY", False)
if NETLIFY or env("NETLIFY_URL"):
    if ".netlify.app" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(".netlify.app")
    for key in ("URL", "DEPLOY_PRIME_URL", "SITE_DOMAIN"):
        _register_site_origin(env(key))

_backend_url = env("DJANGO_BACKEND_URL")
if _backend_url:
    _register_site_origin(_backend_url)

SITE_DOMAIN = env("SITE_DOMAIN", "http://localhost:8000")
SITE_NAME = env("SITE_NAME", "MS Photo Studio")


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
]

THIRD_PARTY_APPS = [
    "widget_tweaks",
]

LOCAL_APPS = [
    "apps.common",
    "apps.core",
    "apps.accounts",
    "apps.customers",
    "apps.portfolio",
    "apps.services",
    "apps.cms",
    "apps.galleries",
    "apps.albums",
    "apps.notifications",
    "apps.analytics",
    "apps.website",
    "apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.MaintenanceModeMiddleware",
    "apps.core.middleware.LastActivityMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_context",
                "apps.core.context_processors.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# Database - SQLite by default, Postgres when configured
# ---------------------------------------------------------------------------
def build_database_config():
    url = env("DATABASE_URL")
    if url:
        parsed = urlparse(url)
        engines = {
            "postgres": "django.db.backends.postgresql",
            "postgresql": "django.db.backends.postgresql",
            "psql": "django.db.backends.postgresql",
            "mysql": "django.db.backends.mysql",
            "sqlite": "django.db.backends.sqlite3",
        }
        engine = engines.get(parsed.scheme, "django.db.backends.postgresql")
        if engine.endswith("sqlite3"):
            return {"ENGINE": engine, "NAME": parsed.path.lstrip("/") or str(BASE_DIR / "db.sqlite3")}
        return {
            "ENGINE": engine,
            "NAME": (parsed.path or "").lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
            "CONN_MAX_AGE": 600,
        }

    if env("POSTGRES_HOST") and env_bool("USE_POSTGRES", False):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "lumina"),
            "USER": env("POSTGRES_USER", "lumina"),
            "PASSWORD": env("POSTGRES_PASSWORD", "lumina"),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
        }

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }


DATABASES = {"default": build_database_config()}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/client/"
LOGOUT_REDIRECT_URL = "/"

SESSION_COOKIE_NAME = "lumina_sessionid"
SESSION_COOKIE_AGE = env_int("SESSION_COOKIE_AGE", 60 * 60 * 12)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("LANGUAGE_CODE", "en-us")
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

USE_S3 = env_bool("USE_S3", False)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

if USE_S3:
    # django-storages + boto3 must be installed for this branch.
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "eu-west-1")
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"}

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 400
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "MS Photo Studio <studio@msphotostudio.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
STUDIO_NOTIFICATION_EMAIL = env("STUDIO_NOTIFICATION_EMAIL", "studio@msphotostudio.com")


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {
    message_constants.DEBUG: "debug",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "error",
}


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ---------------------------------------------------------------------------
# Studio / gallery domain settings
# ---------------------------------------------------------------------------
STUDIO_BRAND_NAME = "MS Photo Studio"
STUDIO_BRAND_GOLD = "#D4AF37"
GALLERY_DEFAULT_EXPIRY_DAYS = env_int("GALLERY_DEFAULT_EXPIRY_DAYS", 90)
GALLERY_ACCESS_SESSION_KEY = "unlocked_galleries"
GALLERY_MEDIA_PREFIX = "galleries"
GALLERY_MAX_BULK_UPLOAD = env_int("GALLERY_MAX_BULK_UPLOAD", 200)
GALLERY_ZIP_MAX_IMAGES = env_int("GALLERY_ZIP_MAX_IMAGES", 300)
NOTIFY_EMAILS_ENABLED = env_bool("NOTIFY_EMAILS_ENABLED", True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "lumina": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
    },
}