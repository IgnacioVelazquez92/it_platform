# src/apps/catalog/forms/scoped_selections.py
from __future__ import annotations

from typing import Any

from django import forms
from django.db import transaction

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.forms.helpers import (
    sync_through_rows,
    validate_cash_register_belongs_to_branch,
    validate_control_panel_belongs_to_company,
    validate_seller_belongs_to_company,
    validate_warehouse_belongs_to_branch,
)
from apps.catalog.models.permissions.scoped import (
    Branch,
    CashRegister,
    Company,
    ControlPanel,
    Seller,
    Warehouse,
)
from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
    SelectionSetWarehouse,
)


class SelectionSetScopedSelectionsForm(BootstrapFormMixin, forms.ModelForm):
    """
    Paso 3 del wizard: selecciones scoped condicionales.

    Importante:
    - El PermissionSelectionSet ya debe existir (con company/branch definidos).
    - Guardamos selecciones en tablas hijas (SelectionSetWarehouse, etc.)
    - Validación fuerte mínima:
        - warehouse/cash_register ∈ branch
        - control_panel/seller ∈ company

    Nota sobre reglas:
    - Por ahora el form expone TODOS los campos.
    - Más adelante, la vista/template puede ocultar secciones según PermissionBlocks
      sin cambiar esta lógica.
    """

    warehouses = forms.ModelMultipleChoiceField(
        queryset=Warehouse.objects.none(),
        required=False,
        help_text="Depósitos disponibles para la sucursal seleccionada.",
    )

    cash_registers = forms.ModelMultipleChoiceField(
        queryset=CashRegister.objects.none(),
        required=False,
        help_text="Cajas disponibles para la sucursal seleccionada.",
    )

    control_panels = forms.ModelMultipleChoiceField(
        queryset=ControlPanel.objects.none(),
        required=False,
        help_text="Paneles disponibles para la empresa seleccionada.",
    )

    sellers = forms.ModelMultipleChoiceField(
        queryset=Seller.objects.none(),
        required=False,
        help_text="Vendedores disponibles para la empresa seleccionada.",
    )

    class Meta:
        model = PermissionSelectionSet
        fields = []  # no editamos columnas directas del selection_set en este paso

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if not self.instance or not self.instance.pk:
            raise ValueError(
                "SelectionSetScopedSelectionsForm requiere instance=PermissionSelectionSet ya guardada."
            )

        company_id = self.instance.company_id
        branch_id = self.instance.branch_id

        # Querysets filtrados por scope + activos
        self.fields["warehouses"].queryset = Warehouse.objects.filter(
            branch_id=branch_id, is_active=True
        ).order_by("name")

        self.fields["cash_registers"].queryset = CashRegister.objects.filter(
            branch_id=branch_id, is_active=True
        ).order_by("name")

        self.fields["control_panels"].queryset = ControlPanel.objects.filter(
            company_id=company_id, is_active=True
        ).order_by("name")

        self.fields["sellers"].queryset = Seller.objects.filter(
            company_id=company_id, is_active=True
        ).order_by("name")

        # Inicial desde tablas hijas
        if not self.is_bound:
            self.fields["warehouses"].initial = list(
                self.instance.warehouses.values_list("warehouse_id", flat=True)
            )
            self.fields["cash_registers"].initial = list(
                self.instance.cash_registers.values_list(
                    "cash_register_id", flat=True)
            )
            self.fields["control_panels"].initial = list(
                self.instance.control_panels.values_list(
                    "control_panel_id", flat=True)
            )
            self.fields["sellers"].initial = list(
                self.instance.sellers.values_list("seller_id", flat=True)
            )

    def clean(self) -> dict:
        cleaned = super().clean()

        # Scope real (defensivo): validamos contra DB
        branch = Branch.objects.only("id").get(id=self.instance.branch_id)
        company = Company.objects.only("id").get(id=self.instance.company_id)

        for w in cleaned.get("warehouses", []):
            validate_warehouse_belongs_to_branch(branch=branch, warehouse=w)

        for c in cleaned.get("cash_registers", []):
            validate_cash_register_belongs_to_branch(
                branch=branch, cash_register=c)

        for p in cleaned.get("control_panels", []):
            validate_control_panel_belongs_to_company(
                company=company, control_panel=p)

        for s in cleaned.get("sellers", []):
            validate_seller_belongs_to_company(company=company, seller=s)

        return cleaned

    @transaction.atomic
    def save(self, commit: bool = True) -> PermissionSelectionSet:
        """
        Sincroniza tablas hijas según lo seleccionado.
        """
        selection_set = self.instance

        sync_through_rows(
            selection_set=selection_set,
            through_model=SelectionSetWarehouse,
            fk_name="warehouse",
            desired_ids=[
                w.id for w in self.cleaned_data.get("warehouses", [])],
        )

        sync_through_rows(
            selection_set=selection_set,
            through_model=SelectionSetCashRegister,
            fk_name="cash_register",
            desired_ids=[c.id for c in self.cleaned_data.get(
                "cash_registers", [])],
        )

        sync_through_rows(
            selection_set=selection_set,
            through_model=SelectionSetControlPanel,
            fk_name="control_panel",
            desired_ids=[p.id for p in self.cleaned_data.get(
                "control_panels", [])],
        )

        sync_through_rows(
            selection_set=selection_set,
            through_model=SelectionSetSeller,
            fk_name="seller",
            desired_ids=[s.id for s in self.cleaned_data.get("sellers", [])],
        )

        return selection_set
