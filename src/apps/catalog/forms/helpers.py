from __future__ import annotations
from django.db import transaction

from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetModule,
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
)


from apps.catalog.models.modules import ErpModule, ErpModuleSubLevel
from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetModule,
    SelectionSetSubLevel,
)


def clone_selection_set(base: PermissionSelectionSet, *, company, branch=None) -> PermissionSelectionSet:
    """
    Clona un PermissionSelectionSet (módulos + scoped + global) hacia otra empresa/sucursal.
    Importante: company/branch pueden cambiar. Se copian:
    - módulos y globales siempre
    - scoped solo si corresponde a la nueva company/branch (si no, se omite)
    """
    new_set = PermissionSelectionSet.objects.create(
        company=company,
        branch=branch,
        notes=base.notes,
    )

    # Modules
    SelectionSetModule.objects.bulk_create(
        [
            SelectionSetModule(selection_set=new_set, module=m.module)
            for m in base.selected_modules.select_related("module").all()
        ]
    )

    # Global actions
    SelectionSetActionValue.objects.bulk_create(
        [
            SelectionSetActionValue(
                selection_set=new_set,
                action_permission=a.action_permission,
                value_bool=a.value_bool,
                value_int=a.value_int,
                value_decimal=a.value_decimal,
                value_text=a.value_text,
                is_active=a.is_active,
            )
            for a in base.action_values.select_related("action_permission").all()
        ]
    )

    # Matrix
    SelectionSetMatrixPermission.objects.bulk_create(
        [
            SelectionSetMatrixPermission(
                selection_set=new_set,
                permission=mp.permission,
                can_create=mp.can_create,
                can_update=mp.can_update,
                can_authorize=mp.can_authorize,
                can_close=mp.can_close,
                can_cancel=mp.can_cancel,
                can_update_validity=mp.can_update_validity,
            )
            for mp in base.matrix_permissions.select_related("permission").all()
        ]
    )

    # Payment methods
    SelectionSetPaymentMethod.objects.bulk_create(
        [
            SelectionSetPaymentMethod(
                selection_set=new_set,
                payment_method=pm.payment_method,
                enabled=pm.enabled,
                is_active=pm.is_active,
            )
            for pm in base.payment_methods.select_related("payment_method").all()
        ]
    )

    # Scoped: copiar solo si coincide el scope nuevo
    if branch is not None:
        SelectionSetWarehouse.objects.bulk_create(
            [
                SelectionSetWarehouse(
                    selection_set=new_set, warehouse=w.warehouse)
                for w in base.warehouses.select_related("warehouse").all()
                if w.warehouse.branch_id == branch.id
            ]
        )
        SelectionSetCashRegister.objects.bulk_create(
            [
                SelectionSetCashRegister(
                    selection_set=new_set, cash_register=c.cash_register)
                for c in base.cash_registers.select_related("cash_register").all()
                if c.cash_register.branch_id == branch.id
            ]
        )

    SelectionSetControlPanel.objects.bulk_create(
        [
            SelectionSetControlPanel(
                selection_set=new_set, control_panel=p.control_panel)
            for p in base.control_panels.select_related("control_panel").all()
            if p.control_panel.company_id == company.id
        ]
    )
    SelectionSetSeller.objects.bulk_create(
        [
            SelectionSetSeller(selection_set=new_set, seller=s.seller)
            for s in base.sellers.select_related("seller").all()
            if s.seller.company_id == company.id
        ]
    )

    return new_set


@transaction.atomic
def set_selection_set_modules(selection_set: PermissionSelectionSet, modules: list[ErpModule]) -> None:
    """
    Reemplaza módulos seleccionados (nivel rápido).
    No toca subniveles (eso lo decide la estrategia).
    """
    SelectionSetModule.objects.filter(selection_set=selection_set).delete()
    SelectionSetModule.objects.bulk_create(
        [SelectionSetModule(selection_set=selection_set, module=m)
         for m in modules]
    )


@transaction.atomic
def set_selection_set_sublevels(selection_set: PermissionSelectionSet, sublevels: list[ErpModuleSubLevel]) -> None:
    """
    Reemplaza subniveles seleccionados (refinamiento).
    """
    SelectionSetSubLevel.objects.filter(selection_set=selection_set).delete()
    SelectionSetSubLevel.objects.bulk_create(
        [SelectionSetSubLevel(selection_set=selection_set, sublevel=s)
         for s in sublevels]
    )


def active_sublevels_for_modules(modules: list[ErpModule]) -> list[ErpModuleSubLevel]:
    """
    Devuelve todos los subniveles activos pertenecientes a módulos activos seleccionados.
    (default: módulo marcado => todo adentro marcado)
    """
    if not modules:
        return []
    return list(
        ErpModuleSubLevel.objects.filter(
            is_active=True,
            level__is_active=True,
            level__module__in=modules,
            level__module__is_active=True,
        )
        .select_related("level", "level__module")
        .order_by("level__module__name", "level__name", "name")
    )
