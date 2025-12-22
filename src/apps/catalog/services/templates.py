from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetModule,
    SelectionSetLevel,
    SelectionSetSubLevel,
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
)


@dataclass(frozen=True)
class CloneResult:
    source_id: int
    cloned: PermissionSelectionSet


@transaction.atomic
def clone_selection_set(source: PermissionSelectionSet, *, notes: str = "") -> CloneResult:
    """
    Clona un PermissionSelectionSet con TODAS sus selecciones (modules, levels/sublevels,
    scoped y globales). El resultado queda independiente del original.
    """
    target = PermissionSelectionSet.objects.create(
        company_id=source.company_id,
        branch_id=source.branch_id,
        notes=notes or source.notes,
    )

    # Modules
    SelectionSetModule.objects.bulk_create(
        [SelectionSetModule(selection_set=target, module=row.module)
         for row in source.selected_modules.select_related("module").all()],
        ignore_conflicts=True,
    )

    # Levels
    SelectionSetLevel.objects.bulk_create(
        [SelectionSetLevel(selection_set=target, level=row.level)
         for row in source.selected_levels.select_related("level").all()],
        ignore_conflicts=True,
    )

    # Sublevels
    SelectionSetSubLevel.objects.bulk_create(
        [SelectionSetSubLevel(selection_set=target, sublevel=row.sublevel)
         for row in source.sublevels.select_related("sublevel").all()],
        ignore_conflicts=True,
    )

    # Scoped
    SelectionSetWarehouse.objects.bulk_create(
        [SelectionSetWarehouse(selection_set=target, warehouse=row.warehouse)
         for row in source.warehouses.select_related("warehouse").all()],
        ignore_conflicts=True,
    )
    SelectionSetCashRegister.objects.bulk_create(
        [SelectionSetCashRegister(selection_set=target, cash_register=row.cash_register)
         for row in source.cash_registers.select_related("cash_register").all()],
        ignore_conflicts=True,
    )
    SelectionSetControlPanel.objects.bulk_create(
        [SelectionSetControlPanel(selection_set=target, control_panel=row.control_panel)
         for row in source.control_panels.select_related("control_panel").all()],
        ignore_conflicts=True,
    )
    SelectionSetSeller.objects.bulk_create(
        [SelectionSetSeller(selection_set=target, seller=row.seller)
         for row in source.sellers.select_related("seller").all()],
        ignore_conflicts=True,
    )

    # Globales: Action values
    SelectionSetActionValue.objects.bulk_create(
        [SelectionSetActionValue(
            selection_set=target,
            action_permission=row.action_permission,
            value_bool=row.value_bool,
            value_int=row.value_int,
            value_decimal=row.value_decimal,
            value_text=row.value_text,
            is_active=row.is_active,
        ) for row in source.action_values.select_related("action_permission").all()],
        ignore_conflicts=True,
    )

    # Matrix permissions
    SelectionSetMatrixPermission.objects.bulk_create(
        [SelectionSetMatrixPermission(
            selection_set=target,
            permission=row.permission,
            can_create=row.can_create,
            can_update=row.can_update,
            can_authorize=row.can_authorize,
            can_close=row.can_close,
            can_cancel=row.can_cancel,
            can_update_validity=row.can_update_validity,
        ) for row in source.matrix_permissions.select_related("permission").all()],
        ignore_conflicts=True,
    )

    # Payment methods
    SelectionSetPaymentMethod.objects.bulk_create(
        [SelectionSetPaymentMethod(
            selection_set=target,
            payment_method=row.payment_method,
            enabled=row.enabled,
            is_active=row.is_active,
        ) for row in source.payment_methods.select_related("payment_method").all()],
        ignore_conflicts=True,
    )

    return CloneResult(source_id=source.pk, cloned=target)
