# src/apps/catalog/forms/global_permissions.py
from __future__ import annotations

from typing import Any, Optional

from django import forms
from django.forms import BaseModelFormSet, modelformset_factory

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.forms.helpers import ensure_global_rows_exist
from apps.catalog.models.permissions.global_ops import ActionValueType
from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
)


# ============================================================
# Forms (una fila por modelo)
# ============================================================

class SelectionSetActionValueForm(BootstrapFormMixin, forms.ModelForm):
    """
    Una fila por ActionPermission (SelectionSetActionValue).
    Mantiene el modelo de “multi-campo” (bool/int/decimal/text).

    Regla:
    - Solo el campo correspondiente al value_type debería usarse.
    - Permitimos "None" / vacío como “no definido aún”.
    """

    class Meta:
        model = SelectionSetActionValue
        fields = [
            "action_permission",
            "value_bool",
            "value_int",
            "value_decimal",
            "value_text",
            "is_active",
        ]
        widgets = {"action_permission": forms.HiddenInput()}

    def clean(self) -> dict:
        cleaned = super().clean()

        ap = self.instance.action_permission
        if not ap:
            return cleaned

        vt = ap.value_type

        vb = cleaned.get("value_bool")
        vi = cleaned.get("value_int")
        vd = cleaned.get("value_decimal")
        vt_text = cleaned.get("value_text")

        def _is_set(v: Any) -> bool:
            if v is None:
                return False
            if isinstance(v, str):
                return v.strip() != ""
            return True

        def _any_set(*vals: Any) -> bool:
            return any(_is_set(x) for x in vals)

        # Bloqueamos valores cruzados: mantiene coherencia del payload.
        if vt == ActionValueType.BOOL:
            if _any_set(vi, vd, vt_text):
                raise forms.ValidationError(
                    "Valor inválido: esta acción es tipo BOOL.")
        elif vt == ActionValueType.INT:
            if _any_set(vb, vd, vt_text):
                raise forms.ValidationError(
                    "Valor inválido: esta acción es tipo INT.")
        elif vt in (ActionValueType.DECIMAL, ActionValueType.PERCENT):
            if _any_set(vb, vi, vt_text):
                raise forms.ValidationError(
                    "Valor inválido: esta acción es tipo DECIMAL/PERCENT.")
        elif vt == ActionValueType.TEXT:
            if _any_set(vb, vi, vd):
                raise forms.ValidationError(
                    "Valor inválido: esta acción es tipo TEXT.")

        # Nota: la validación del porcentaje (0–100) ya vive en el model.clean().
        return cleaned


class SelectionSetMatrixPermissionForm(BootstrapFormMixin, forms.ModelForm):
    """
    Una fila por MatrixPermission dentro del selection_set.
    Flags booleanos.
    """

    class Meta:
        model = SelectionSetMatrixPermission
        fields = [
            "permission",
            "can_create",
            "can_update",
            "can_authorize",
            "can_close",
            "can_cancel",
            "can_update_validity",
        ]
        widgets = {"permission": forms.HiddenInput()}


class SelectionSetPaymentMethodForm(BootstrapFormMixin, forms.ModelForm):
    """
    Una fila por PaymentMethodPermission.
    enabled = valor principal.
    is_active = toggle interno (útil para desactivar sin borrar).
    """

    class Meta:
        model = SelectionSetPaymentMethod
        fields = ["payment_method", "enabled", "is_active"]
        widgets = {"payment_method": forms.HiddenInput()}


# ============================================================
# Base FormSet bound a un PermissionSelectionSet
# ============================================================

class _BaseSelectionSetBoundFormSet(BaseModelFormSet):
    """
    FormSet que conoce el selection_set (para bootstrap y para futuras reglas).
    """

    selection_set: PermissionSelectionSet

    def __init__(self, *args: Any, selection_set: PermissionSelectionSet, **kwargs: Any) -> None:
        self.selection_set = selection_set

        # Asegura “tabla completa” (solo crea faltantes para catálogos activos).
        ensure_global_rows_exist(selection_set)

        super().__init__(*args, **kwargs)


# ============================================================
# Builders de formsets (para vistas wizard)
# ============================================================

def make_action_value_formset(
    *,
    selection_set: PermissionSelectionSet,
    data: Optional[dict] = None,
    prefix: str = "actions",
    extra: int = 0,
) -> BaseModelFormSet:
    """
    Crea un formset para SelectionSetActionValue del selection_set.
    """
    qs = (
        SelectionSetActionValue.objects.filter(
            selection_set=selection_set,
            action_permission__isnull=False,
        )
        .select_related("action_permission")
        .order_by("action_permission__group", "action_permission__action")
    )

    FormSet = modelformset_factory(
        SelectionSetActionValue,
        form=SelectionSetActionValueForm,
        formset=_BaseSelectionSetBoundFormSet,
        extra=extra,
        can_delete=False,
    )
    return FormSet(data=data, queryset=qs, prefix=prefix, selection_set=selection_set)


def make_matrix_permission_formset(
    *,
    selection_set: PermissionSelectionSet,
    data: Optional[dict] = None,
    prefix: str = "matrix",
    extra: int = 0,
) -> BaseModelFormSet:
    """
    Crea un formset para SelectionSetMatrixPermission del selection_set.
    """
    qs = (
        SelectionSetMatrixPermission.objects.filter(
            selection_set=selection_set)
        .select_related("permission")
        .order_by("permission__name")
    )

    FormSet = modelformset_factory(
        SelectionSetMatrixPermission,
        form=SelectionSetMatrixPermissionForm,
        formset=_BaseSelectionSetBoundFormSet,
        extra=extra,
        can_delete=False,
    )
    return FormSet(data=data, queryset=qs, prefix=prefix, selection_set=selection_set)


def make_payment_method_formset(
    *,
    selection_set: PermissionSelectionSet,
    data: Optional[dict] = None,
    prefix: str = "payments",
    extra: int = 0,
) -> BaseModelFormSet:
    """
    Crea un formset para SelectionSetPaymentMethod del selection_set.
    """
    qs = (
        SelectionSetPaymentMethod.objects.filter(selection_set=selection_set)
        .select_related("payment_method")
        .order_by("payment_method__name")
    )

    FormSet = modelformset_factory(
        SelectionSetPaymentMethod,
        form=SelectionSetPaymentMethodForm,
        formset=_BaseSelectionSetBoundFormSet,
        extra=extra,
        can_delete=False,
    )
    return FormSet(data=data, queryset=qs, prefix=prefix, selection_set=selection_set)
