from .base import *  # noqa
import os
import dj_database_url

# =========================
# CORE
# =========================

DEBUG = False


# =========================
# HOSTS / CSRF (Railway-safe)
# =========================

# ALLOWED_HOSTS
raw_hosts = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",") if h.strip()]

# Fallback seguro para Railway (evita DisallowedHost)
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [
        "pharma-it.up.railway.app",
        ".up.railway.app",
    ]


# CSRF_TRUSTED_ORIGINS
raw_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in raw_csrf.split(",") if o.strip()]

# Fallback CSRF seguro (solo tu dominio real)
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        "https://pharma-it.up.railway.app",
    ]


# =========================
# DATABASE
# =========================

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}


# =========================
# SECURITY / PROXY
# =========================

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# =========================
# STATIC FILES
# =========================

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)


# =========================
# APP CONFIG
# =========================

CATALOG_IT_NOTIFY_EMAILS = os.getenv(
    "CATALOG_IT_NOTIFY_EMAILS",
    "i.velazquez@pharmacenter.com.ar",
).split(",")

USE_GMAIL_OAUTH = True

GMAIL_OAUTH_SENDER = os.getenv("GMAIL_OAUTH_SENDER", "")
GMAIL_OAUTH_CLIENT_ID = os.getenv("GMAIL_OAUTH_CLIENT_ID", "")
GMAIL_OAUTH_CLIENT_SECRET = os.getenv("GMAIL_OAUTH_CLIENT_SECRET", "")
GMAIL_OAUTH_REFRESH_TOKEN = os.getenv("GMAIL_OAUTH_REFRESH_TOKEN", "")
