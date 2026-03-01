from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Company
from apps.catalog.services.template_excel_import import (
    TemplateExcelImportError,
    import_templates_from_excel,
)


User = get_user_model()


class Command(BaseCommand):
    help = "Importa AccessTemplate desde un Excel donde cada solapa representa un perfil."

    def add_arguments(self, parser):
        parser.add_argument("excel_path", type=str)
        parser.add_argument("--owner", required=True, help="Username del owner de los templates importados.")
        parser.add_argument(
            "--company-id",
            type=int,
            default=None,
            help="Empresa base tecnica opcional. Si no se informa, usa la misma resolucion interna del wizard.",
        )
        parser.add_argument(
            "--replace-existing",
            action="store_true",
            help="Reemplaza templates existentes con el mismo nombre de solapa.",
        )

    def handle(self, *args, **options):
        excel_path = Path(options["excel_path"]).expanduser().resolve()
        if not excel_path.exists():
            raise CommandError(f"No existe el archivo: {excel_path}")

        owner = User.objects.filter(username=options["owner"]).first()
        if owner is None:
            raise CommandError(f"No existe el usuario owner '{options['owner']}'.")

        company = None
        company_id = options.get("company_id")
        if company_id is not None:
            company = Company.objects.filter(pk=company_id, is_active=True).first()
            if company is None:
                raise CommandError(f"No existe una empresa activa con id={company_id}.")

        try:
            with excel_path.open("rb") as fh:
                result = import_templates_from_excel(
                    file_obj=fh,
                    owner=owner,
                    company=company,
                    replace_existing=bool(options["replace_existing"]),
                )
        except TemplateExcelImportError as exc:
            raise CommandError(str(exc)) from exc

        for warning in result.warnings:
            self.stdout.write(self.style.WARNING(warning))

        for item in result.results:
            verb = "creado" if item.created else "actualizado"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{item.sheet_name}: {verb} (template_id={item.template_id}, "
                    f"modulos={item.modules_selected}, subniveles={item.sublevels_selected}, "
                    f"acciones={item.action_values_selected})"
                )
            )
