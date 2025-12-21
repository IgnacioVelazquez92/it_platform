from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.db import transaction

from apps.catalog.models.permissions.global_ops import (
    ActionPermission,
    ActionValueType,
    MatrixPermission,
    PaymentMethodPermission,
)
from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
)


def _has_any_matrix_flag(d: dict) -> bool:
    return any(
        d.get(k)
        for k in (
            "can_create",
            "can_update",
            "can_authorize",
            "can_close",
            "can_cancel",
            "can_update_validity",
        )
    )


def _action_has_value(value_type: str, cleaned: dict) -> bool:
    """
    Define si un ActionValue debe persistirse.
    Criterio UX/DB:
      - BOOL: solo si True (tildado)
      - INT: solo si hay número
      - DECIMAL/PERCENT: solo si hay número
      - TEXT: solo si hay texto no vacío
    """
    if value_type == ActionValueType.BOOL:
        return bool(cleaned.get("value_bool"))

    if value_type == ActionValueType.INT:
        return cleaned.get("value_int") is not None

    if value_type in (ActionValueType.DECIMAL, ActionValueType.PERCENT):
        return cleaned.get("value_decimal") is not None

    if value_type == ActionValueType.TEXT:
        v = cleaned.get("value_text")
        return bool(str(v or "").strip())

    return False


@transaction.atomic
def save_globals_for_selection_set(
    selection_set: PermissionSelectionSet,
    *,
    action_items: list[dict],
    matrix_items: list[dict],
    payment_items: list[dict],
) -> None:
    """
    Reemplaza globales del selection_set con los payloads ya validados.
    Payload esperado:
      - action_items: [{action_permission, value_bool/value_int/value_decimal/value_text}]
      - matrix_items: [{permission, can_create, ...}]
      - payment_items: [{payment_method, enabled}]
    """
    # --------- ACTIONS ----------
    SelectionSetActionValue.objects.filter(
        selection_set=selection_set).delete()

    action_rows: list[SelectionSetActionValue] = []
    for it in action_items:
        ap: ActionPermission = it["action_permission"]
        vt = ap.value_type

        if not _action_has_value(vt, it):
            continue

        row = SelectionSetActionValue(
            selection_set=selection_set,
            action_permission=ap,
            is_active=True,
            value_bool=it.get("value_bool"),
            value_int=it.get("value_int"),
            value_decimal=it.get("value_decimal"),
            value_text=it.get("value_text"),
        )
        action_rows.append(row)

    if action_rows:
        SelectionSetActionValue.objects.bulk_create(
            action_rows, batch_size=500)

    # --------- MATRIX ----------
    SelectionSetMatrixPermission.objects.filter(
        selection_set=selection_set).delete()

    matrix_rows: list[SelectionSetMatrixPermission] = []
    for it in matrix_items:
        if not _has_any_matrix_flag(it):
            continue
        mp: MatrixPermission = it["permission"]
        matrix_rows.append(
            SelectionSetMatrixPermission(
                selection_set=selection_set,
                permission=mp,
                can_create=bool(it.get("can_create")),
                can_update=bool(it.get("can_update")),
                can_authorize=bool(it.get("can_authorize")),
                can_close=bool(it.get("can_close")),
                can_cancel=bool(it.get("can_cancel")),
                can_update_validity=bool(it.get("can_update_validity")),
            )
        )

    if matrix_rows:
        SelectionSetMatrixPermission.objects.bulk_create(
            matrix_rows, batch_size=500)

    # --------- PAYMENT METHODS ----------
    SelectionSetPaymentMethod.objects.filter(
        selection_set=selection_set).delete()

    pay_rows: list[SelectionSetPaymentMethod] = []
    for it in payment_items:
        if not it.get("enabled"):
            continue
        pm: PaymentMethodPermission = it["payment_method"]
        pay_rows.append(
            SelectionSetPaymentMethod(
                selection_set=selection_set,
                payment_method=pm,
                enabled=True,
                is_active=True,
            )
        )

    if pay_rows:
        SelectionSetPaymentMethod.objects.bulk_create(pay_rows, batch_size=500)
