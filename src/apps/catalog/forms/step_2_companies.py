from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from collections import defaultdict

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.permissions.scoped import Company, Branch


class Step2CompaniesForm(BootstrapFormMixin, forms.Form):
    companies = forms.ModelMultipleChoiceField(
        label="Empresas",
        queryset=Company.objects.filter(is_active=True).order_by("name"),
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )

    branches = forms.ModelMultipleChoiceField(
        label="Sucursales",
        queryset=Branch.objects.filter(is_active=True).select_related(
            "company").order_by("company__name", "name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Seleccioná las sucursales correspondientes a las empresas elegidas.",
    )

    same_modules_for_all = forms.ChoiceField(
        label="¿Replicar módulos y permisos generales para todas las empresas?",
        choices=[("1", "Sí, una sola configuración para todas"),
                 ("0", "No, configurar por empresa")],
        widget=forms.RadioSelect,
        required=False,  # solo aplica si hay múltiples empresas
        initial="1",
    )

    def clean(self):
        cleaned = super().clean()
        companies = cleaned.get("companies")
        branches = cleaned.get("branches") or []
        same = cleaned.get("same_modules_for_all")

        if not companies or companies.count() == 0:
            raise ValidationError(
                {"companies": "Seleccioná al menos una empresa."})

        # Validar que branches pertenezcan a companies seleccionadas
        company_ids = {c.id for c in companies}
        invalid = [b for b in branches if b.company_id not in company_ids]
        if invalid:
            raise ValidationError(
                {"branches": "Seleccionaste sucursales que no pertenecen a las empresas elegidas."})

        # NUEVO: Validar que cada empresa tenga al menos una sucursal
        # Agrupamos por company_id
        branches_by_company = defaultdict(list)
        for b in branches:
            branches_by_company[b.company_id].append(b)

        missing_branches_companies = []
        for c in companies:
            if not branches_by_company.get(c.id):
                missing_branches_companies.append(c.name)
        
        if missing_branches_companies:
            names = ", ".join(missing_branches_companies)
            raise ValidationError(
                f"Debe seleccionar al menos una sucursal para: {names}."
            )

        # Si hay más de 1 empresa, same_modules_for_all es requerido
        if companies.count() > 1 and same not in ("0", "1"):
            raise ValidationError(
                {"same_modules_for_all": "Elegí si querés replicar módulos y permisos generales."})

        # Si hay 1 empresa, default a True (no molestar al usuario)
        if companies.count() == 1:
            cleaned["same_modules_for_all"] = "1"

        return cleaned
