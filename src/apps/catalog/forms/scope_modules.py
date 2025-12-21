# src/apps/catalog/forms/scope_modules.py
from __future__ import annotations

from typing import Any, Optional

from django import forms
from django.db import transaction

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.forms.helpers import validate_branch_belongs_to_company, sync_through_rows
from apps.catalog.models.modules import ErpModule
from apps.catalog.models.permissions.scoped import Branch, Company
from apps.catalog.models.selections import PermissionSelectionSet, SelectionSetModule


class SelectionSetScopeModulesForm(BootstrapFormMixin, forms.ModelForm):
    """
    Paso 2 del wizard:
    - Company (obligatoria)
    - Branch (obligatoria, filtrada por company)
    - Modules (multi selección, opcional)
    - Notes (opcional)

    Principios:
    - Validación fuerte mínima: branch pertenece a company
    - Querysets filtrados por is_active=True
    - Sync explícito de módulos vía through model (SelectionSetModule)
    """

    modules = forms.ModelMultipleChoiceField(
        queryset=ErpModule.objects.filter(is_active=True).order_by("name"),
        required=False,
    )

    class Meta:
        model = PermissionSelectionSet
        fields = ["company", "branch", "modules", "notes"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Company siempre activo
        self.fields["company"].queryset = Company.objects.filter(
            is_active=True).order_by("name")

        # Determinar company_id para filtrar branches
        company_id: Optional[int] = None
        if self.is_bound:
            company_id = self.data.get(self.add_prefix("company")) or None
        elif self.instance and self.instance.company_id:
            company_id = self.instance.company_id

        if company_id:
            self.fields["branch"].queryset = Branch.objects.filter(
                company_id=company_id,
                is_active=True,
            ).order_by("name")
        else:
            # Evita mostrar “todas las sucursales” sin company.
            self.fields["branch"].queryset = Branch.objects.none()

        # Inicial de módulos desde through table (solo activos).
        if self.instance and self.instance.pk and not self.is_bound:
            self.fields["modules"].initial = list(
                self.instance.selected_modules
                .select_related("module")
                .filter(module__is_active=True)
                .values_list("module_id", flat=True)
            )

    def clean(self) -> dict:
        cleaned = super().clean()

        company: Optional[Company] = cleaned.get("company")
        branch: Optional[Branch] = cleaned.get("branch")

        if company and branch:
            validate_branch_belongs_to_company(company=company, branch=branch)

        return cleaned

    @transaction.atomic
    def save(self, commit: bool = True) -> PermissionSelectionSet:
        """
        Guarda el selection_set y sincroniza SelectionSetModule.
        """
        selection_set: PermissionSelectionSet = super().save(commit=commit)

        module_ids = [m.id for m in self.cleaned_data.get("modules", [])]
        sync_through_rows(
            selection_set=selection_set,
            through_model=SelectionSetModule,
            fk_name="module",
            desired_ids=module_ids,
        )
        return selection_set
