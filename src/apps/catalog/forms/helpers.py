# src/apps/catalog/forms/helpers.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Optional, Sequence, TypeVar

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models.permissions.scoped import (
    Branch,
    CashRegister,
    Company,
    ControlPanel,
    Seller,
    Warehouse,
)
from apps.catalog.models.permissions.global_ops import (
    ActionPermission,
    ActionValueType,
    MatrixPermission,
    PaymentMethodPermission,
)
from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetActionValue,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetMatrixPermission,
    SelectionSetModule,
    SelectionSetPaymentMethod,
    SelectionSetSeller,
    SelectionSetWarehouse,
)
from apps.catalog.models.templates import AccessTemplate

T = TypeVar("T")


# ============================================================
# Scope & validaciones mínimas fuertes
# ============================================================

@dataclass(frozen=True)
class Scope:
    """
    Scope operativo del selection_set.

    Nota:
    - Company/Branch son “ancla” del flujo.
    - Los demás catálogos deben pertenecer a este scope.
    """
    company_id: int
    branch_id: int


def scope_from_selection_set(selection_set: PermissionSelectionSet) -> Scope:
    return Scope(company_id=selection_set.company_id, branch_id=selection_set.branch_id)


def validate_branch_belongs_to_company(*, company: Company, branch: Branch) -> None:
    if branch.company_id != company.id:
        raise ValidationError(
            {"branch": "La sucursal no pertenece a la empresa seleccionada."})


def validate_warehouse_belongs_to_branch(*, branch: Branch, warehouse: Warehouse) -> None:
    if warehouse.branch_id != branch.id:
        raise ValidationError(
            "El depósito no pertenece a la sucursal seleccionada.")


def validate_cash_register_belongs_to_branch(*, branch: Branch, cash_register: CashRegister) -> None:
    if cash_register.branch_id != branch.id:
        raise ValidationError(
            "La caja no pertenece a la sucursal seleccionada.")


def validate_control_panel_belongs_to_company(*, company: Company, control_panel: ControlPanel) -> None:
    if control_panel.company_id != company.id:
        raise ValidationError(
            "El panel no pertenece a la empresa seleccionada.")


def validate_seller_belongs_to_company(*, company: Company, seller: Seller) -> None:
    if seller.company_id != company.id:
        raise ValidationError(
            "El vendedor no pertenece a la empresa seleccionada.")


# ============================================================
# Sync genérico de tablas intermedias (rows-based selections)
# ============================================================

def _unique_ints(values: Iterable[int]) -> list[int]:
    """
    Dedup conservando orden (para trazabilidad).
    """
    out: list[int] = []
    seen: set[int] = set()
    for v in values:
        iv = int(v)
        if iv in seen:
            continue
        seen.add(iv)
        out.append(iv)
    return out


def sync_through_rows(
    *,
    selection_set: PermissionSelectionSet,
    through_model,
    fk_name: str,
    desired_ids: Sequence[int],
) -> None:
    """
    Sincroniza una tabla "SelectionSetXxx" contra un listado de IDs.

    Comportamiento:
    - Borra filas existentes que ya no estén en desired_ids
    - Crea filas nuevas para IDs faltantes
    - No toca las filas que ya existen y siguen seleccionadas

    Parámetros:
    - through_model: modelo tipo SelectionSetWarehouse / SelectionSetModule / etc.
    - fk_name: nombre del campo FK hacia el catálogo *sin* sufijo "_id"
      ej: "warehouse", "module", "cash_register", etc.
    """
    desired_ids = _unique_ints([int(x) for x in desired_ids])
    desired_set = set(desired_ids)

    fk_id_field = f"{fk_name}_id"

    existing_qs = through_model.objects.filter(selection_set=selection_set)
    existing_ids = set(existing_qs.values_list(fk_id_field, flat=True))

    # 1) Delete removed
    existing_qs.exclude(**{f"{fk_id_field}__in": desired_set}).delete()

    # 2) Create missing
    missing = [i for i in desired_ids if i not in existing_ids]
    if not missing:
        return

    bulk = [
        through_model(selection_set=selection_set, **{fk_id_field: i})
        for i in missing
    ]
    through_model.objects.bulk_create(bulk, ignore_conflicts=True)


# ============================================================
# Clonado de selection_set desde template (reutilización segura)
# ============================================================

@transaction.atomic
def clone_selection_set_from_template(*, template: AccessTemplate) -> PermissionSelectionSet:
    """
    Clona el PermissionSelectionSet de un AccessTemplate hacia uno nuevo.

    Regla:
    - Nunca se reusa el selection_set del template.
    - El destino queda completamente independiente.
    """
    src = template.selection_set

    dst = PermissionSelectionSet.objects.create(
        company=src.company,
        branch=src.branch,
        notes=src.notes,
    )

    # Modules (through)
    sync_through_rows(
        selection_set=dst,
        through_model=SelectionSetModule,
        fk_name="module",
        desired_ids=list(
            src.selected_modules.filter(
                module__is_active=True).values_list("module_id", flat=True)
        ),
    )

    # Scoped selections
    sync_through_rows(
        selection_set=dst,
        through_model=SelectionSetWarehouse,
        fk_name="warehouse",
        desired_ids=list(
            src.warehouses.filter(warehouse__is_active=True).values_list(
                "warehouse_id", flat=True)
        ),
    )
    sync_through_rows(
        selection_set=dst,
        through_model=SelectionSetCashRegister,
        fk_name="cash_register",
        desired_ids=list(
            src.cash_registers.filter(cash_register__is_active=True).values_list(
                "cash_register_id", flat=True)
        ),
    )
    sync_through_rows(
        selection_set=dst,
        through_model=SelectionSetControlPanel,
        fk_name="control_panel",
        desired_ids=list(
            src.control_panels.filter(control_panel__is_active=True).values_list(
                "control_panel_id", flat=True)
        ),
    )
    sync_through_rows(
        selection_set=dst,
        through_model=SelectionSetSeller,
        fk_name="seller",
        desired_ids=list(
            src.sellers.filter(seller__is_active=True).values_list(
                "seller_id", flat=True)
        ),
    )

    # Global: Action values (copiamos valores tal cual)
    av_rows = list(
        src.action_values.filter(action_permission__is_active=True).values(
            "action_permission_id",
            "value_bool",
            "value_int",
            "value_decimal",
            "value_text",
            "is_active",
        )
    )
    if av_rows:
        SelectionSetActionValue.objects.bulk_create(
            [SelectionSetActionValue(selection_set=dst, **row)
             for row in av_rows],
            ignore_conflicts=True,
        )

    # Global: Matrix permissions (copiamos flags)
    mp_rows = list(
        src.matrix_permissions.filter(permission__is_active=True).values(
            "permission_id",
            "can_create",
            "can_update",
            "can_authorize",
            "can_close",
            "can_cancel",
            "can_update_validity",
        )
    )
    if mp_rows:
        SelectionSetMatrixPermission.objects.bulk_create(
            [SelectionSetMatrixPermission(
                selection_set=dst, **row) for row in mp_rows],
            ignore_conflicts=True,
        )

    # Global: Payment methods
    pm_rows = list(
        src.payment_methods.filter(payment_method__is_active=True).values(
            "payment_method_id",
            "enabled",
            "is_active",
        )
    )
    if pm_rows:
        SelectionSetPaymentMethod.objects.bulk_create(
            [SelectionSetPaymentMethod(selection_set=dst, **row)
             for row in pm_rows],
            ignore_conflicts=True,
        )

    return dst


# ============================================================
# Bootstrap del Paso 4 (filas globales completas)
# ============================================================

@transaction.atomic
def ensure_global_rows_exist(selection_set: PermissionSelectionSet) -> None:
    """
    Asegura que existan filas “por catálogo” para el Paso 4:

    - 1 SelectionSetActionValue por ActionPermission activo
    - 1 SelectionSetMatrixPermission por MatrixPermission activo
    - 1 SelectionSetPaymentMethod por PaymentMethodPermission activo

    Importante:
    - Solo crea faltantes (no pisa valores existentes).
    - No crea filas para catálogos inactivos (is_active=False).
    """
    # --- Actions
    existing_av = set(
        SelectionSetActionValue.objects.filter(selection_set=selection_set)
        .values_list("action_permission_id", flat=True)
    )
    to_create_av = [
        SelectionSetActionValue(
            selection_set=selection_set, action_permission_id=ap_id)
        for ap_id in ActionPermission.objects.filter(is_active=True).values_list("id", flat=True)
        if ap_id not in existing_av
    ]
    if to_create_av:
        SelectionSetActionValue.objects.bulk_create(
            to_create_av, ignore_conflicts=True)

    # --- Matrix
    existing_mp = set(
        SelectionSetMatrixPermission.objects.filter(
            selection_set=selection_set)
        .values_list("permission_id", flat=True)
    )
    to_create_mp = [
        SelectionSetMatrixPermission(
            selection_set=selection_set, permission_id=mp_id)
        for mp_id in MatrixPermission.objects.filter(is_active=True).values_list("id", flat=True)
        if mp_id not in existing_mp
    ]
    if to_create_mp:
        SelectionSetMatrixPermission.objects.bulk_create(
            to_create_mp, ignore_conflicts=True)

    # --- Payment methods
    existing_pm = set(
        SelectionSetPaymentMethod.objects.filter(selection_set=selection_set)
        .values_list("payment_method_id", flat=True)
    )
    to_create_pm = [
        SelectionSetPaymentMethod(
            selection_set=selection_set, payment_method_id=pm_id)
        for pm_id in PaymentMethodPermission.objects.filter(is_active=True).values_list("id", flat=True)
        if pm_id not in existing_pm
    ]
    if to_create_pm:
        SelectionSetPaymentMethod.objects.bulk_create(
            to_create_pm, ignore_conflicts=True)
