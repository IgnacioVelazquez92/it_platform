# src/apps/catalog/models/selections.py
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from .modules import ErpModule
from .permissions.scoped import (
    Company,
    Branch,
    Warehouse,
    CashRegister,
    ControlPanel,
    Seller,
)
from .permissions.global_ops import (
    ActionPermission,
    ActionValueType,
    MatrixPermission,
    PaymentMethodPermission,
)

from .modules import ErpModule, ErpModuleSubLevel


class PermissionSelectionSet(models.Model):
    """
    Contenedor reutilizable de lo que el usuario eligió.
    """

    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="selection_sets"
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="selection_sets",
        null=True,
        blank=True,
    )

    modules = models.ManyToManyField(
        ErpModule,
        blank=True,
        related_name="selection_sets",
        through="SelectionSetModule",
    )

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Selección de permisos"
        verbose_name_plural = "Selecciones de permisos"
        ordering = ("-created_at",)

    def clean(self):
        super().clean()
        if self.branch_id and self.company_id:
            if self.branch.company_id != self.company_id:
                raise ValidationError(
                    {"branch": "La sucursal no pertenece a la empresa seleccionada."}
                )

    def __str__(self) -> str:
        return f"{self.company} / {self.branch} (SelectionSet #{self.pk})"


class SelectionSetModule(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="selected_modules"
    )
    module = models.ForeignKey(ErpModule, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Módulo seleccionado"
        verbose_name_plural = "Módulos seleccionados"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "module"], name="uniq_selection_module"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.selection_set_id} -> {self.module}"


class SelectionSetLevel(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="selected_levels"
    )
    level = models.ForeignKey("catalog.ErpModuleLevel",
                              on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "level"], name="uniq_selection_level"),
        ]


class SelectionSetSubLevel(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="sublevels"
    )
    sublevel = models.ForeignKey(ErpModuleSubLevel, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subnivel seleccionado"
        verbose_name_plural = "Subniveles seleccionados"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "sublevel"], name="uniq_selection_sublevel"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.selection_set_id} -> {self.sublevel}"


# -------------------------------------------------
# Scoped selections
# -------------------------------------------------

class SelectionSetWarehouse(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="warehouses"
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Depósito seleccionado"
        verbose_name_plural = "Depósitos seleccionados"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "warehouse"], name="uniq_selection_warehouse"
            ),
        ]

    def clean(self):
        if self.warehouse.branch_id != self.selection_set.branch_id:
            raise ValidationError(
                "El depósito no pertenece a la sucursal seleccionada."
            )


class SelectionSetCashRegister(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="cash_registers"
    )
    cash_register = models.ForeignKey(CashRegister, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Caja seleccionada"
        verbose_name_plural = "Cajas seleccionadas"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "cash_register"], name="uniq_selection_cash_register"
            ),
        ]

    def clean(self):
        if self.cash_register.branch_id != self.selection_set.branch_id:
            raise ValidationError(
                "La caja no pertenece a la sucursal seleccionada.")


class SelectionSetControlPanel(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="control_panels"
    )
    control_panel = models.ForeignKey(ControlPanel, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Panel seleccionado"
        verbose_name_plural = "Paneles seleccionados"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "control_panel"], name="uniq_selection_control_panel"
            ),
        ]

    def clean(self):
        if self.control_panel.company_id != self.selection_set.company_id:
            raise ValidationError(
                "El panel no pertenece a la empresa seleccionada.")


class SelectionSetSeller(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="sellers"
    )
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Vendedor seleccionado"
        verbose_name_plural = "Vendedores seleccionados"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "seller"], name="uniq_selection_seller"
            ),
        ]

    def clean(self):
        if self.seller.company_id != self.selection_set.company_id:
            raise ValidationError(
                "El vendedor no pertenece a la empresa seleccionada.")


# -------------------------------------------------
# Global selections
# -------------------------------------------------

class SelectionSetActionValue(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.CASCADE, related_name="action_values"
    )
    action_permission = models.ForeignKey(
        ActionPermission, on_delete=models.PROTECT
    )

    value_bool = models.BooleanField(null=True, blank=True)
    value_int = models.IntegerField(null=True, blank=True)
    value_decimal = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    value_text = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Acción (valor)"
        verbose_name_plural = "Acciones (valores)"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "action_permission"],
                name="uniq_selection_action_value",
            ),
        ]
        ordering = ("action_permission__group", "action_permission__action")

    def clean(self):
        vt = self.action_permission.value_type

        if vt == ActionValueType.BOOL and self.value_bool is None:
            return

        if vt == ActionValueType.PERCENT and self.value_decimal is not None:
            if not (Decimal("0") <= self.value_decimal <= Decimal("100")):
                raise ValidationError("Porcentaje fuera de rango (0–100).")

    def __str__(self) -> str:
        return f"{self.action_permission.group} / {self.action_permission.action}"


class SelectionSetMatrixPermission(models.Model):
    """
    Permiso de matriz seleccionado con columnas booleanas.
    """

    selection_set = models.ForeignKey(
        PermissionSelectionSet,
        on_delete=models.CASCADE,
        related_name="matrix_permissions",
    )
    permission = models.ForeignKey(
        MatrixPermission, on_delete=models.PROTECT
    )

    can_create = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_authorize = models.BooleanField(default=False)
    can_close = models.BooleanField(default=False)
    can_cancel = models.BooleanField(default=False)
    can_update_validity = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Permiso de matriz (selección)"
        verbose_name_plural = "Permisos de matriz (selección)"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "permission"],
                name="uniq_selection_matrix_permission",
            ),
        ]
        ordering = ("permission__name",)

    def __str__(self) -> str:
        return f"{self.permission}"


class SelectionSetPaymentMethod(models.Model):
    selection_set = models.ForeignKey(
        PermissionSelectionSet,
        on_delete=models.CASCADE,
        related_name="payment_methods",
    )
    payment_method = models.ForeignKey(
        PaymentMethodPermission, on_delete=models.PROTECT
    )

    enabled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Medio de pago (selección)"
        verbose_name_plural = "Medios de pago (selección)"
        constraints = [
            models.UniqueConstraint(
                fields=["selection_set", "payment_method"],
                name="uniq_selection_payment_method",
            ),
        ]
        ordering = ("payment_method__name",)

    def __str__(self) -> str:
        return f"{self.payment_method} = {self.enabled}"
