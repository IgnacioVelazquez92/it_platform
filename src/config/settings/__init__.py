import os

env = os.getenv("DJANGO_ENV", "development").lower().strip()

if env == "production":
    from .production import *  # noqa
else:
    from .development import *  # noqa
