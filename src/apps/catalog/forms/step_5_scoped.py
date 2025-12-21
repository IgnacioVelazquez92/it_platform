# src/apps/catalog/forms/step_5_scoped.py
from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.permissions.scoped import (
    Company,
    Branch,
    Warehouse,
    CashRegister,
    ControlPanel,
    Seller,
)


class NoValidationMultipleChoiceField(forms.MultipleChoiceField):
    """Campo que acepta cualquier valor sin validar contra choices."""

    def valid_value(self, value):
        return True


class CompanyScopedForm(BootstrapFormMixin, forms.Form):
    """
    Scoped por EMPRESA:
    - control_panels: depende de Company
    - sellers: depende de Company
    """

    control_panels = NoValidationMultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Paneles",
    )
    sellers = NoValidationMultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Vendedores",
    )

    def __init__(self, *args, company: Company, **kwargs):
        self.company = company
        super().__init__(*args, **kwargs)

        # Querysets filtrados por empresa + activos
        cp_qs = ControlPanel.objects.filter(
            company=company, is_active=True).order_by("name")
        s_qs = Seller.objects.filter(
            company=company, is_active=True).order_by("name")

        # Construir choices dinámicamente
        self.fields["control_panels"].choices = [(p.id, str(p)) for p in cp_qs]
        self.fields["sellers"].choices = [(s.id, str(s)) for s in s_qs]

        import logging
        logger = logging.getLogger("apps.catalog")
        logger.debug(
            "[FORM][INIT] CompanyScopedForm | prefix=%s company=%s cp_choices=%s s_choices=%s",
            self.prefix, company.id,
            [c[0] for c in self.fields["control_panels"].choices],
            [c[0] for c in self.fields["sellers"].choices]
        )

    def clean_control_panels(self):
        """Valida y retorna QuerySet de paneles seleccionados."""
        import logging
        logger = logging.getLogger("apps.catalog")

        raw_ids = self.cleaned_data.get("control_panels", [])
        # Convertir strings a ints
        try:
            ids = [int(x) for x in raw_ids if x]
        except (ValueError, TypeError):
            raise forms.ValidationError("IDs inválidos.")

        logger.debug(
            "[FORM][CLEAN] control_panels | prefix=%s company=%s ids_from_cleaned=%s",
            self.prefix, self.company.id, ids
        )

        if not ids:
            return ControlPanel.objects.none()

        # Log de choices disponibles
        available_ids = [c[0] for c in self.fields["control_panels"].choices]
        logger.debug(
            "[FORM][CLEAN] control_panels | available_choice_ids=%s",
            available_ids
        )

        qs = ControlPanel.objects.filter(
            id__in=ids, company=self.company, is_active=True
        )
        logger.debug(
            "[FORM][CLEAN] control_panels | qs_count=%s expected_count=%s qs_ids=%s",
            qs.count(), len(ids), list(qs.values_list("id", flat=True))
        )

        if qs.count() != len(ids):
            raise forms.ValidationError(
                "Uno o más paneles seleccionados no son válidos.")
        return qs

    def clean_sellers(self):
        """Valida y retorna QuerySet de vendedores seleccionados."""
        import logging
        logger = logging.getLogger("apps.catalog")

        raw_ids = self.cleaned_data.get("sellers", [])
        try:
            ids = [int(x) for x in raw_ids if x]
        except (ValueError, TypeError):
            raise forms.ValidationError("IDs inválidos.")

        logger.debug(
            "[FORM][CLEAN] sellers | prefix=%s company=%s ids_from_cleaned=%s",
            self.prefix, self.company.id, ids
        )

        if not ids:
            return Seller.objects.none()

        available_ids = [c[0] for c in self.fields["sellers"].choices]
        logger.debug(
            "[FORM][CLEAN] sellers | available_choice_ids=%s",
            available_ids
        )

        qs = Seller.objects.filter(
            id__in=ids, company=self.company, is_active=True
        )
        logger.debug(
            "[FORM][CLEAN] sellers | qs_count=%s expected_count=%s qs_ids=%s",
            qs.count(), len(ids), list(qs.values_list("id", flat=True))
        )

        if qs.count() != len(ids):
            raise forms.ValidationError(
                "Uno o más vendedores seleccionados no son válidos.")
        return qs


class BranchScopedForm(BootstrapFormMixin, forms.Form):
    """
    Scoped por SUCURSAL:
    - warehouses: depende de Branch
    - cash_registers: depende de Branch
    """

    warehouses = NoValidationMultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Depósitos",
    )
    cash_registers = NoValidationMultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Cajas",
    )

    def __init__(self, *args, branch: Branch, **kwargs):
        self.branch = branch
        super().__init__(*args, **kwargs)

        wh_qs = Warehouse.objects.filter(
            branch=branch, is_active=True).order_by("name")
        cr_qs = CashRegister.objects.filter(
            branch=branch, is_active=True).order_by("name")

        # Construir choices dinámicamente
        self.fields["warehouses"].choices = [(w.id, str(w)) for w in wh_qs]
        self.fields["cash_registers"].choices = [(c.id, str(c)) for c in cr_qs]

        import logging
        logger = logging.getLogger("apps.catalog")
        logger.debug(
            "[FORM][INIT] BranchScopedForm | prefix=%s branch=%s wh_choices=%s cr_choices=%s",
            self.prefix, branch.id,
            [c[0] for c in self.fields["warehouses"].choices],
            [c[0] for c in self.fields["cash_registers"].choices]
        )

    def clean_warehouses(self):
        """Valida y retorna QuerySet de depósitos seleccionados."""
        import logging
        logger = logging.getLogger("apps.catalog")

        raw_ids = self.cleaned_data.get("warehouses", [])
        try:
            ids = [int(x) for x in raw_ids if x]
        except (ValueError, TypeError):
            raise forms.ValidationError("IDs inválidos.")

        logger.debug(
            "[FORM][CLEAN] warehouses | prefix=%s branch=%s ids_from_cleaned=%s",
            self.prefix, self.branch.id, ids
        )

        if not ids:
            return Warehouse.objects.none()

        available_ids = [c[0] for c in self.fields["warehouses"].choices]
        logger.debug(
            "[FORM][CLEAN] warehouses | available_choice_ids=%s",
            available_ids
        )

        qs = Warehouse.objects.filter(
            id__in=ids, branch=self.branch, is_active=True
        )
        logger.debug(
            "[FORM][CLEAN] warehouses | qs_count=%s expected_count=%s qs_ids=%s",
            qs.count(), len(ids), list(qs.values_list("id", flat=True))
        )

        if qs.count() != len(ids):
            raise forms.ValidationError(
                "Uno o más depósitos seleccionados no son válidos.")
        return qs

    def clean_cash_registers(self):
        """Valida y retorna QuerySet de cajas seleccionadas."""
        import logging
        logger = logging.getLogger("apps.catalog")

        raw_ids = self.cleaned_data.get("cash_registers", [])
        try:
            ids = [int(x) for x in raw_ids if x]
        except (ValueError, TypeError):
            raise forms.ValidationError("IDs inválidos.")

        logger.debug(
            "[FORM][CLEAN] cash_registers | prefix=%s branch=%s ids_from_cleaned=%s",
            self.prefix, self.branch.id, ids
        )

        if not ids:
            return CashRegister.objects.none()

        available_ids = [c[0] for c in self.fields["cash_registers"].choices]
        logger.debug(
            "[FORM][CLEAN] cash_registers | available_choice_ids=%s",
            available_ids
        )

        qs = CashRegister.objects.filter(
            id__in=ids, branch=self.branch, is_active=True
        )
        logger.debug(
            "[FORM][CLEAN] cash_registers | qs_count=%s expected_count=%s qs_ids=%s",
            qs.count(), len(ids), list(qs.values_list("id", flat=True))
        )

        if qs.count() != len(ids):
            raise forms.ValidationError(
                "Uno o más cajas seleccionadas no son válidas.")
        return qs
