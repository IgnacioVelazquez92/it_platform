# src/config/settings/production.py
from .base import *  # noqa
import os
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS", "").split(",") if h.strip()]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", ""),
        conn_max_age=600,
        ssl_require=True,
    )
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# WhiteNoise (static)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


CATALOG_IT_NOTIFY_EMAILS = ["it@empresa.com", "tu_mail@empresa.com"]

GMAIL_OAUTH_SENDER = "tu_cuenta_google_workspace@empresa.com"
GMAIL_OAUTH_CLIENT_ID = os.environ.get("GMAIL_OAUTH_CLIENT_ID", "")
GMAIL_OAUTH_CLIENT_SECRET = os.environ.get("GMAIL_OAUTH_CLIENT_SECRET", "")
GMAIL_OAUTH_REFRESH_TOKEN = os.environ.get("GMAIL_OAUTH_REFRESH_TOKEN", "")

# Recomendado: esto lo usás para forzar que en PROD se use Gmail API
USE_GMAIL_OAUTH = True
