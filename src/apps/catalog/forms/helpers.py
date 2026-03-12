from __future__ import annotations
from django.db import transaction

from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetModule,
    SelectionSetLevel,
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
    SelectionSetLevel,
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


def _merge_bool(current, incoming) -> bool | None:
    if current is None and incoming is None:
        return None
    return bool(current) or bool(incoming)


def _merge_number(current, incoming):
    if current is None:
        return incoming
    if incoming is None:
        return current
    return incoming if incoming > current else current


def _merge_text(current, incoming) -> str | None:
    current = (current or "").strip()
    incoming = (incoming or "").strip()
    if current:
        return current
    if incoming:
        return incoming
    return None


@transaction.atomic
def merge_selection_sets(
    bases: list[PermissionSelectionSet], *, company, branch=None
) -> PermissionSelectionSet:
    """
    Fusiona selection sets por union positiva y crea un nuevo selection_set en el
    scope destino. Reglas:
    - modulos, niveles, subniveles, scoped, matriz y medios de pago: union
    - acciones BOOL: OR
    - acciones INT/DECIMAL/PERCENT: maximo
    - acciones TEXT: primer valor no vacio
    """
    if not bases:
        return PermissionSelectionSet.objects.create(company=company, branch=branch)

    notes_parts: list[str] = []
    module_ids: set[int] = set()
    level_ids: set[int] = set()
    sublevel_ids: set[int] = set()
    warehouse_ids: set[int] = set()
    cash_register_ids: set[int] = set()
    control_panel_ids: set[int] = set()
    seller_ids: set[int] = set()
    matrix_by_permission: dict[int, dict] = {}
    payments_by_method: dict[int, dict] = {}
    actions_by_permission: dict[int, dict] = {}

    for base in bases:
        note = (base.notes or "").strip()
        if note and note not in notes_parts:
            notes_parts.append(note)

        module_ids.update(
            base.selected_modules.values_list("module_id", flat=True)
        )
        level_ids.update(
            base.selected_levels.values_list("level_id", flat=True)
        )
        sublevel_ids.update(
            base.sublevels.values_list("sublevel_id", flat=True)
        )

        if branch is not None:
            warehouse_ids.update(
                base.warehouses.filter(warehouse__branch_id=branch.id)
                .values_list("warehouse_id", flat=True)
            )
            cash_register_ids.update(
                base.cash_registers.filter(cash_register__branch_id=branch.id)
                .values_list("cash_register_id", flat=True)
            )

        control_panel_ids.update(
            base.control_panels.filter(control_panel__company_id=company.id)
            .values_list("control_panel_id", flat=True)
        )
        seller_ids.update(
            base.sellers.filter(seller__company_id=company.id)
            .values_list("seller_id", flat=True)
        )

        for row in base.action_values.select_related("action_permission").all():
            action_permission = row.action_permission
            current = actions_by_permission.get(action_permission.id)
            if current is None:
                actions_by_permission[action_permission.id] = {
                    "action_permission": action_permission,
                    "value_bool": row.value_bool,
                    "value_int": row.value_int,
                    "value_decimal": row.value_decimal,
                    "value_text": row.value_text,
                    "is_active": row.is_active,
                }
                continue

            current["is_active"] = bool(current["is_active"]) or bool(row.is_active)
            if action_permission.value_type == "BOOL":
                current["value_bool"] = _merge_bool(current["value_bool"], row.value_bool)
            elif action_permission.value_type in ("INT", "DECIMAL", "PERCENT"):
                key = "value_int" if action_permission.value_type == "INT" else "value_decimal"
                current[key] = _merge_number(current[key], getattr(row, key))
            else:
                current["value_text"] = _merge_text(current["value_text"], row.value_text)

        for row in base.matrix_permissions.select_related("permission").all():
            current = matrix_by_permission.get(row.permission_id)
            if current is None:
                matrix_by_permission[row.permission_id] = {
                    "permission": row.permission,
                    "can_create": row.can_create,
                    "can_update": row.can_update,
                    "can_authorize": row.can_authorize,
                    "can_close": row.can_close,
                    "can_cancel": row.can_cancel,
                    "can_update_validity": row.can_update_validity,
                }
                continue
            current["can_create"] = current["can_create"] or row.can_create
            current["can_update"] = current["can_update"] or row.can_update
            current["can_authorize"] = current["can_authorize"] or row.can_authorize
            current["can_close"] = current["can_close"] or row.can_close
            current["can_cancel"] = current["can_cancel"] or row.can_cancel
            current["can_update_validity"] = current["can_update_validity"] or row.can_update_validity

        for row in base.payment_methods.select_related("payment_method").all():
            current = payments_by_method.get(row.payment_method_id)
            if current is None:
                payments_by_method[row.payment_method_id] = {
                    "payment_method": row.payment_method,
                    "enabled": row.enabled,
                    "is_active": row.is_active,
                }
                continue
            current["enabled"] = current["enabled"] or row.enabled
            current["is_active"] = current["is_active"] or row.is_active

    new_set = PermissionSelectionSet.objects.create(
        company=company,
        branch=branch,
        notes="\n\n".join(notes_parts),
    )

    SelectionSetModule.objects.bulk_create(
        [SelectionSetModule(selection_set=new_set, module_id=module_id) for module_id in sorted(module_ids)],
        ignore_conflicts=True,
    )
    SelectionSetLevel.objects.bulk_create(
        [SelectionSetLevel(selection_set=new_set, level_id=level_id) for level_id in sorted(level_ids)],
        ignore_conflicts=True,
    )
    SelectionSetSubLevel.objects.bulk_create(
        [SelectionSetSubLevel(selection_set=new_set, sublevel_id=sublevel_id) for sublevel_id in sorted(sublevel_ids)],
        ignore_conflicts=True,
    )
    if branch is not None:
        SelectionSetWarehouse.objects.bulk_create(
            [SelectionSetWarehouse(selection_set=new_set, warehouse_id=warehouse_id) for warehouse_id in sorted(warehouse_ids)],
            ignore_conflicts=True,
        )
        SelectionSetCashRegister.objects.bulk_create(
            [SelectionSetCashRegister(selection_set=new_set, cash_register_id=cash_register_id) for cash_register_id in sorted(cash_register_ids)],
            ignore_conflicts=True,
        )
    SelectionSetControlPanel.objects.bulk_create(
        [SelectionSetControlPanel(selection_set=new_set, control_panel_id=control_panel_id) for control_panel_id in sorted(control_panel_ids)],
        ignore_conflicts=True,
    )
    SelectionSetSeller.objects.bulk_create(
        [SelectionSetSeller(selection_set=new_set, seller_id=seller_id) for seller_id in sorted(seller_ids)],
        ignore_conflicts=True,
    )
    SelectionSetActionValue.objects.bulk_create(
        [
            SelectionSetActionValue(
                selection_set=new_set,
                action_permission=row["action_permission"],
                value_bool=row["value_bool"],
                value_int=row["value_int"],
                value_decimal=row["value_decimal"],
                value_text=row["value_text"],
                is_active=row["is_active"],
            )
            for row in actions_by_permission.values()
        ],
        ignore_conflicts=True,
    )
    SelectionSetMatrixPermission.objects.bulk_create(
        [
            SelectionSetMatrixPermission(
                selection_set=new_set,
                permission=row["permission"],
                can_create=row["can_create"],
                can_update=row["can_update"],
                can_authorize=row["can_authorize"],
                can_close=row["can_close"],
                can_cancel=row["can_cancel"],
                can_update_validity=row["can_update_validity"],
            )
            for row in matrix_by_permission.values()
        ],
        ignore_conflicts=True,
    )
    SelectionSetPaymentMethod.objects.bulk_create(
        [
            SelectionSetPaymentMethod(
                selection_set=new_set,
                payment_method=row["payment_method"],
                enabled=row["enabled"],
                is_active=row["is_active"],
            )
            for row in payments_by_method.values()
        ],
        ignore_conflicts=True,
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
