#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""

    # src/manage.py -> src/
    base_dir = Path(__file__).resolve().parent

    # Carga .env desde la raíz del proyecto (un nivel arriba de src)
    try:
        from dotenv import load_dotenv
        load_dotenv(base_dir.parent / ".env")  # .../it/.env
    except Exception:
        # Si python-dotenv no está o el archivo no existe, no rompe
        pass

    # Este módulo debe apuntar a config/settings/__init__.py
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
