# src/config/settings/base.py
from pathlib import Path
import os

# /app/src/config/settings/base.py -> parents[2] = /app/src
PROJECT_DIR = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_DIR

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "apps.core.apps.CoreConfig",
    "apps.catalog.apps.CatalogConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

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
        "DIRS": [PROJECT_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Tucuman"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_DIR / "staticfiles"
STATICFILES_DIRS = [PROJECT_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# Correo (Gmail OAuth) - NO lo toco
USE_GMAIL_OAUTH = True
GMAIL_OAUTH_CLIENT_ID = os.getenv("GMAIL_OAUTH_CLIENT_ID", "")
GMAIL_OAUTH_CLIENT_SECRET = os.getenv("GMAIL_OAUTH_CLIENT_SECRET", "")
GMAIL_OAUTH_REFRESH_TOKEN = os.getenv("GMAIL_OAUTH_REFRESH_TOKEN", "")
GMAIL_OAUTH_SENDER = os.getenv("GMAIL_OAUTH_SENDER", "")

# Destinatarios - mejor por env, con fallback
CATALOG_IT_NOTIFY_EMAILS = [
    e.strip()
    for e in os.getenv("CATALOG_IT_NOTIFY_EMAILS", "").split(",")
    if e.strip()
] or [
    "i.velazquez@pharmacenter.com.ar",
    "ignaciov92@gmail.com",
]
