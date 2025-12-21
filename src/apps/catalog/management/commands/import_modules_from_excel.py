# src/apps/catalog/management/commands/import_modules_from_excel.py
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

try:
    import openpyxl
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Falta 'openpyxl'. Instalalo con: pip install openpyxl") from exc

from apps.catalog.models.modules import ErpModule, ErpModuleLevel, ErpModuleSubLevel


def _norm(s: object) -> str:
    return str(s or "").strip()


def _norm_header(s: object) -> str:
    return _norm(s).lower().replace(" ", "")


class Command(BaseCommand):
    help = "Importa Módulo/Nivel/Subnivel desde un Excel (permisos.xlsx) a la DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="permisos.xlsx",
            help="Ruta al Excel. Por defecto: permisos.xlsx (en la raíz del proyecto).",
        )
        parser.add_argument(
            "--sheet",
            default=None,
            help="Nombre de la hoja. Si no se indica, usa la hoja activa.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la importación sin escribir en la base.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_opt = options["file"]
        sheet_name = options["sheet"]
        dry_run = options["dry_run"]

        # Raíz del proyecto: .../it (asumiendo src/manage.py)
        # .../src/apps/catalog/management/commands
        project_root = Path(__file__).resolve().parents[5]
        xlsx_path = Path(file_opt)
        if not xlsx_path.is_absolute():
            xlsx_path = project_root / xlsx_path

        if not xlsx_path.exists():
            raise CommandError(f"No existe el archivo: {xlsx_path}")

        wb = openpyxl.load_workbook(xlsx_path)
        ws = wb[sheet_name] if sheet_name else wb.active

        rows = ws.iter_rows(values_only=True)
        try:
            header = next(rows)
        except StopIteration:
            raise CommandError("La hoja está vacía.")

        # Detectar columnas
        header_map = {_norm_header(h): idx for idx, h in enumerate(header)}
        required = ["modulo", "nivel", "subnivel"]
        missing = [k for k in required if k not in header_map]
        if missing:
            raise CommandError(
                "Encabezados inválidos. Deben existir columnas: Modulo, Nivel, Subnivel. "
                f"Faltan: {', '.join(missing)}"
            )

        i_mod = header_map["modulo"]
        i_lvl = header_map["nivel"]
        i_sub = header_map["subnivel"]

        created_modules = 0
        created_levels = 0
        created_sublevels = 0
        processed = 0
        skipped = 0

        for row in rows:
            processed += 1
            mod_name = _norm(row[i_mod] if i_mod < len(row) else "")
            lvl_name = _norm(row[i_lvl] if i_lvl < len(row) else "")
            sub_name = _norm(row[i_sub] if i_sub < len(row) else "")

            if not mod_name:
                skipped += 1
                continue

            module, mod_created = ErpModule.objects.get_or_create(
                name=mod_name)
            if mod_created:
                created_modules += 1

            level = None
            if lvl_name:
                level, lvl_created = ErpModuleLevel.objects.get_or_create(
                    module=module,
                    name=lvl_name,
                )
                if lvl_created:
                    created_levels += 1

            if level and sub_name:
                sub, sub_created = ErpModuleSubLevel.objects.get_or_create(
                    level=level,
                    name=sub_name,
                )
                if sub_created:
                    created_sublevels += 1

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(
                "DRY-RUN: no se guardó nada en la DB."))

        self.stdout.write(
            self.style.SUCCESS(
                f"OK. Procesadas: {processed} | Saltadas: {skipped} | "
                f"Creado módulos: {created_modules} | Niveles: {created_levels} | Subniveles: {created_sublevels}"
            )
        )
