from __future__ import annotations

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.permissions.global_ops import (
    ActionPermission,
    ActionValueType,
)


# -----------------------------
# ACTIONS (ActionPermission -> SelectionSetActionValue)
# -----------------------------
class ActionValueRowForm(BootstrapFormMixin, forms.Form):
    action_permission_id = forms.IntegerField(widget=forms.HiddenInput)

    # valores posibles (solo uno aplica según value_type)
    value_bool = forms.BooleanField(required=False)
    value_int = forms.IntegerField(required=False)
    value_decimal = forms.DecimalField(
        required=False, max_digits=18, decimal_places=6)
    value_text = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, action_permissions_map: dict[int, ActionPermission] | None = None, **kwargs):
        # lo inyecta el formset para evitar queries
        self.action_permissions_map = action_permissions_map or {}
        super().__init__(*args, **kwargs)

        # UX: compactación (opcional, pero útil)
        self.fields["value_int"].widget.attrs.setdefault(
            "class", "form-control form-control-sm")
        self.fields["value_decimal"].widget.attrs.setdefault(
            "class", "form-control form-control-sm")
        self.fields["value_text"].widget.attrs.setdefault(
            "class", "form-control form-control-sm")

    def clean(self):
        cleaned = super().clean()

        ap_id = cleaned.get("action_permission_id")
        ap = self.action_permissions_map.get(int(ap_id)) if ap_id else None

        if not ap:
            # Si el catálogo no coincide con el formset, es un estado inválido
            raise ValidationError("Acción inválida.")

        vt = ap.value_type

        # Normalización por tipo
        if vt == ActionValueType.BOOL:
            # UX: checkbox. Si no viene en POST, Django lo deja False.
            # Está OK: la persistencia decide si guardar o no.
            return cleaned

        if vt == ActionValueType.INT:
            # vacío = no persistir
            return cleaned

        if vt in (ActionValueType.DECIMAL, ActionValueType.PERCENT):
            v = cleaned.get("value_decimal")
            if v is None:
                return cleaned
            if vt == ActionValueType.PERCENT:
                if not (Decimal("0") <= v <= Decimal("100")):
                    self.add_error("value_decimal",
                                   "Porcentaje fuera de rango (0–100).")
            return cleaned

        if vt == ActionValueType.TEXT:
            # aceptamos vacío = no persistir
            cleaned["value_text"] = (cleaned.get("value_text") or "").strip()
            return cleaned

        return cleaned


class BaseActionRowFormSet(forms.BaseFormSet):
    """
    Inyecta un mapa {id: ActionPermission} en cada form (sin queries).
    """

    def __init__(self, *args, action_permissions: list[ActionPermission] | None = None, **kwargs):
        self._aps = action_permissions or []
        self._ap_map = {ap.id: ap for ap in self._aps}
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kw = super().get_form_kwargs(index)
        kw["action_permissions_map"] = self._ap_map
        return kw


ActionValueFormSet = forms.formset_factory(
    ActionValueRowForm,
    formset=BaseActionRowFormSet,
    extra=0,
    can_delete=False,
)


# -----------------------------
# MATRIX (MatrixPermission -> SelectionSetMatrixPermission)
# -----------------------------
class MatrixRowForm(BootstrapFormMixin, forms.Form):
    permission_id = forms.IntegerField(widget=forms.HiddenInput)

    can_create = forms.BooleanField(required=False)
    can_update = forms.BooleanField(required=False)
    can_authorize = forms.BooleanField(required=False)
    can_close = forms.BooleanField(required=False)
    can_cancel = forms.BooleanField(required=False)
    can_update_validity = forms.BooleanField(required=False)


MatrixFormSet = forms.formset_factory(
    MatrixRowForm,
    extra=0,
    can_delete=False,
)


# -----------------------------
# PAYMENT METHODS (PaymentMethodPermission -> SelectionSetPaymentMethod)
# -----------------------------
class PaymentRowForm(BootstrapFormMixin, forms.Form):
    payment_method_id = forms.IntegerField(widget=forms.HiddenInput)
    enabled = forms.BooleanField(required=False)


PaymentFormSet = forms.formset_factory(
    PaymentRowForm,
    extra=0,
    can_delete=False,
)
