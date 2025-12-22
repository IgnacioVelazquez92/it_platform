from __future__ import annotations

import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = "Bootstrap completo del catálogo + opcional creación de superusuario."

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-superuser",
            action="store_true",
            help="Crea superusuario usando variables de entorno (o genera .env si faltan).",
        )
        parser.add_argument(
            "--write-env",
            action="store_true",
            help="Si faltan credenciales, genera valores y los escribe en un archivo .env local.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "Iniciando bootstrap del catálogo\n"))

        # 1) Correr tus comandos en orden
        steps = [
            ("Importar módulos", "import_modules_from_excel"),
            ("Importar entidades scoped", "import_scoped_from_excel"),
            ("Importar permisos de acciones",
             "import_action_permissions_from_excel"),
            ("Crear reglas de visibilidad", "bootstrap_visibility_rules"),
        ]

        for label, command_name in steps:
            self.stdout.write(self.style.MIGRATE_LABEL(f"→ {label}"))
            try:
                call_command(command_name)
            except Exception as exc:
                raise CommandError(
                    f"Error ejecutando '{command_name}': {exc}") from exc
            self.stdout.write(self.style.SUCCESS(f"✓ {label} completado\n"))

        # 2) Superusuario (opcional)
        env_flag = os.getenv("DJANGO_SUPERUSER_CREATE", "").strip(
        ).lower() in ("1", "true", "yes", "si", "sí")
        if options["create_superuser"] or env_flag:
            self._ensure_superuser(write_env=options["write_env"])

        self.stdout.write(self.style.SUCCESS(
            "Bootstrap finalizado correctamente"))

    def _ensure_superuser(self, *, write_env: bool) -> None:
        User = get_user_model()

        username = (os.getenv("DJANGO_SUPERUSER_USERNAME") or "").strip()
        email = (os.getenv("DJANGO_SUPERUSER_EMAIL") or "").strip()
        password = (os.getenv("DJANGO_SUPERUSER_PASSWORD") or "").strip()

        missing = [k for k, v in {
            "DJANGO_SUPERUSER_USERNAME": username,
            "DJANGO_SUPERUSER_EMAIL": email,
            "DJANGO_SUPERUSER_PASSWORD": password,
        }.items() if not v]

        # Si faltan y pediste write_env: generar y escribir .env local
        if missing and write_env:
            username = username or "admin"
            email = email or "admin@example.com"
            password = password or secrets.token_urlsafe(24)

            self._append_env_file({
                "DJANGO_SUPERUSER_CREATE": "1",
                "DJANGO_SUPERUSER_USERNAME": username,
                "DJANGO_SUPERUSER_EMAIL": email,
                "DJANGO_SUPERUSER_PASSWORD": password,
            })

            self.stdout.write(self.style.WARNING(
                "Se generaron credenciales y se escribieron en .env (solo recomendado para entorno local)."
            ))
            self.stdout.write(self.style.WARNING(
                f"USER={username}  EMAIL={email}  PASS={password}"
            ))
        elif missing:
            # En deploy: no inventar secretos silenciosamente
            raise CommandError(
                "Faltan variables para crear superusuario: "
                + ", ".join(missing)
                + ". Definilas en el entorno (Railway Variables) o ejecutá con --write-env en local."
            )

        # Crear o actualizar usuario
        user = User.objects.filter(username=username).first()
        if user:
            if not user.is_superuser or not user.is_staff:
                user.is_staff = True
                user.is_superuser = True
                user.email = email or user.email
                user.set_password(password)
                user.save(update_fields=["is_staff",
                          "is_superuser", "email", "password"])
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Superusuario actualizado: {username}"))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Superusuario ya existe: {username}"))
            return

        User.objects.create_superuser(
            username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(
            f"✓ Superusuario creado: {username}"))

    def _append_env_file(self, values: dict[str, str]) -> None:
        """
        Escribe en un .env en BASE_DIR (o raíz del repo) sin pisar entradas existentes.
        """
        # Intento razonable: BASE_DIR suele apuntar a src/, subimos uno
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        env_path = base_dir / ".env"
        if not env_path.exists():
            # si BASE_DIR es src/, el .env suele estar en el root (un nivel arriba)
            alt = base_dir.parent / ".env"
            env_path = alt

        existing = ""
        if env_path.exists():
            existing = env_path.read_text(encoding="utf-8")

        lines = []
        for k, v in values.items():
            if f"{k}=" in existing:
                continue
            safe = str(v).replace("\n", "").strip()
            lines.append(f"{k}={safe}")

        if not lines:
            return

        with env_path.open("a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n".join(lines) + "\n")
