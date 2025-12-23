#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def main():
    # src/manage.py -> src/
    base_dir = Path(__file__).resolve().parent

    # Cargar .env local (Railway ignora esto)
    try:
        from dotenv import load_dotenv
        load_dotenv(base_dir.parent / ".env")
    except Exception:
        pass

    # Default LOCAL (Railway lo pisa con env)
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings.development"
    )

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
