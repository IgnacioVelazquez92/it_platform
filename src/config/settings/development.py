# src/config/settings/development.py
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": PROJECT_DIR / "db.sqlite3",
    }
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "apps.catalog": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "CatalogoPermisos <no-reply@local>"

