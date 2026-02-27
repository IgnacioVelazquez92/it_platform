# src/apps/catalog/views/template_wizard/step_3_globals.py
from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.helpers_globals import save_globals_for_selection_set
from apps.catalog.forms.step_4_globals import ActionValueFormSet, MatrixFormSet, PaymentFormSet
from apps.catalog.models.permissions.global_ops import (
    ActionPermission, MatrixPermission, PaymentMethodPermission,
)
from apps.catalog.models.selections import (
    SelectionSetActionValue, SelectionSetMatrixPermission, SelectionSetPaymentMethod,
)
from apps.catalog.models.templates import AccessTemplate

from .base import TemplateWizardBaseView


def _active_catalogs():
    actions = list(ActionPermission.objects.filter(is_active=True).order_by("group", "action"))
    matrix = list(MatrixPermission.objects.filter(is_active=True).order_by("name"))
    payments = list(PaymentMethodPermission.objects.filter(is_active=True).order_by("name"))
    return actions, matrix, payments


def _build_initial(selection_set):
    existing_actions = {
        r.action_permission_id: r for r in
        SelectionSetActionValue.objects.filter(selection_set=selection_set)
    }
    existing_matrix = {
        r.permission_id: r for r in
        SelectionSetMatrixPermission.objects.filter(selection_set=selection_set)
    }
    existing_pay = {
        r.payment_method_id: r for r in
        SelectionSetPaymentMethod.objects.filter(selection_set=selection_set)
    }
    return existing_actions, existing_matrix, existing_pay


def _build_formsets(ss, actions, matrix, payments, prefix_suffix="", data=None):
    existing_a, existing_m, existing_p = _build_initial(ss)

    action_initial = []
    for ap in actions:
        row = {"action_permission_id": ap.id}
        r = existing_a.get(ap.id)
        if r:
            row.update({"value_bool": r.value_bool, "value_int": r.value_int,
                        "value_decimal": r.value_decimal, "value_text": r.value_text})
        action_initial.append(row)

    matrix_initial = []
    for mp in matrix:
        row = {"permission_id": mp.id}
        r = existing_m.get(mp.id)
        if r:
            row.update({"can_create": r.can_create, "can_update": r.can_update,
                        "can_authorize": r.can_authorize, "can_close": r.can_close,
                        "can_cancel": r.can_cancel, "can_update_validity": r.can_update_validity})
        matrix_initial.append(row)

    pay_initial = []
    for pm in payments:
        row = {"payment_method_id": pm.id}
        r = existing_p.get(pm.id)
        if r:
            row["enabled"] = bool(r.enabled)
        pay_initial.append(row)

    kwargs_a = dict(prefix=f"actions{prefix_suffix}", action_permissions=actions, initial=action_initial)
    kwargs_m = dict(prefix=f"matrix{prefix_suffix}", initial=matrix_initial)
    kwargs_p = dict(prefix=f"payments{prefix_suffix}", initial=pay_initial)
    if data is not None:
        kwargs_a["data"] = data
        kwargs_m["data"] = data
        kwargs_p["data"] = data

    a_fs = ActionValueFormSet(**kwargs_a)
    m_fs = MatrixFormSet(**kwargs_m)
    p_fs = PaymentFormSet(**kwargs_p)
    return a_fs, m_fs, p_fs


class TemplateWizardStep3GlobalsView(TemplateWizardBaseView):
    step = 2
    progress_percent = 66
    template_name = "catalog/template_wizard/step_3_globals.html"

    def _get_template(self, request) -> AccessTemplate:
        tmpl = self.get_template_obj(request)
        if not tmpl:
            raise AccessTemplate.DoesNotExist
        return tmpl

    def get(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        item, ensure_error = self.ensure_single_base_item(tmpl)
        if ensure_error or item is None:
            messages.warning(request, ensure_error or "No se pudo inicializar el template.")
            return self.redirect_to("catalog:template_wizard_start")

        actions, matrix, payments = _active_catalogs()
        action_groups = sorted({a.group for a in actions})
        ss = item.selection_set
        a_fs, m_fs, p_fs = _build_formsets(ss, actions, matrix, payments)
        return render(request, self.template_name, self.wizard_context(
            template_obj=tmpl, mode="GLOBAL", items=[item],
            actions=actions, matrix_perms=matrix, payment_methods=payments,
            action_formset=a_fs, matrix_formset=m_fs, payment_formset=p_fs,
            action_groups=action_groups,
            action_rows=list(zip(actions, a_fs.forms)),
            matrix_rows=list(zip(matrix, m_fs.forms)),
            payment_rows=list(zip(payments, p_fs.forms)),
        ))

    @transaction.atomic
    def post(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        item, ensure_error = self.ensure_single_base_item(tmpl)
        if ensure_error or item is None:
            messages.warning(request, ensure_error or "No se pudo inicializar el template.")
            return self.redirect_to("catalog:template_wizard_start")

        actions, matrix, payments = _active_catalogs()
        action_groups = sorted({a.group for a in actions})
        actions_by_id = {a.id: a for a in actions}
        matrix_by_id = {m.id: m for m in matrix}
        pay_by_id = {p.id: p for p in payments}

        def parse_formsets(a_fs, m_fs, p_fs):
            action_items = []
            for f in a_fs:
                ap = actions_by_id.get(f.cleaned_data["action_permission_id"])
                if ap:
                    action_items.append({"action_permission": ap, **{k: f.cleaned_data.get(k) for k in ("value_bool", "value_int", "value_decimal", "value_text")}})
            matrix_items = []
            for f in m_fs:
                mp = matrix_by_id.get(f.cleaned_data["permission_id"])
                if mp:
                    matrix_items.append({"permission": mp, **{k: f.cleaned_data.get(k) for k in ("can_create", "can_update", "can_authorize", "can_close", "can_cancel", "can_update_validity")}})
            payment_items = []
            for f in p_fs:
                pm = pay_by_id.get(f.cleaned_data["payment_method_id"])
                if pm:
                    payment_items.append({"payment_method": pm, "enabled": bool(f.cleaned_data.get("enabled"))})
            return action_items, matrix_items, payment_items

        a_fs, m_fs, p_fs = _build_formsets(
            item.selection_set, actions, matrix, payments, data=request.POST)
        if not (a_fs.is_valid() and m_fs.is_valid() and p_fs.is_valid()):
            return render(request, self.template_name, self.wizard_context(
                template_obj=tmpl, mode="GLOBAL", items=[item],
                actions=actions, matrix_perms=matrix, payment_methods=payments,
                action_formset=a_fs, matrix_formset=m_fs, payment_formset=p_fs,
                action_groups=action_groups,
                action_rows=list(zip(actions, a_fs.forms)),
                matrix_rows=list(zip(matrix, m_fs.forms)),
                payment_rows=list(zip(payments, p_fs.forms)),
            ))

        ai, mi, pi = parse_formsets(a_fs, m_fs, p_fs)
        save_globals_for_selection_set(item.selection_set, action_items=ai, matrix_items=mi, payment_items=pi)
        messages.success(request, "Permisos globales guardados.")
        return self.redirect_to("catalog:template_wizard_review")
