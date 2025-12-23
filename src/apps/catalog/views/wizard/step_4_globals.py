from __future__ import annotations

from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.helpers_globals import save_globals_for_selection_set
from apps.catalog.forms.step_4_globals import ActionValueFormSet, MatrixFormSet, PaymentFormSet
from apps.catalog.models.permissions.global_ops import ActionPermission, MatrixPermission, PaymentMethodPermission
from apps.catalog.models.requests import AccessRequest
from apps.catalog.models.selections import (
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
)

from .base import WizardBaseView


class WizardStep4GlobalsView(WizardBaseView):
    step = 4
    progress_percent = 80
    template_name = "catalog/wizard/step_4_globals.html"

    def _get_request(self, request) -> AccessRequest:
        wizard = self.get_wizard(request)
        req_id = wizard.get("request_id")
        if not req_id:
            raise AccessRequest.DoesNotExist
        return (
            AccessRequest.objects
            .select_related("person_data")
            .prefetch_related(
                "items__selection_set__company",
                "items__selection_set__branch",
            )
            .get(pk=req_id)
        )

    def _active_catalogs(self):
        actions = list(ActionPermission.objects.filter(
            is_active=True).order_by("group", "action"))
        matrix = list(MatrixPermission.objects.filter(
            is_active=True).order_by("name"))
        payments = list(PaymentMethodPermission.objects.filter(
            is_active=True).order_by("name"))
        return actions, matrix, payments

    def _build_initial_for_selection_set(self, selection_set):
        # ACTIONS initial (map action_permission_id -> row values)
        existing_actions = {
            r.action_permission_id: r
            for r in SelectionSetActionValue.objects.filter(selection_set=selection_set)
        }

        # MATRIX initial
        existing_matrix = {
            r.permission_id: r
            for r in SelectionSetMatrixPermission.objects.filter(selection_set=selection_set)
        }

        # PAYMENTS initial
        existing_pay = {
            r.payment_method_id: r
            for r in SelectionSetPaymentMethod.objects.filter(selection_set=selection_set)
        }

        return existing_actions, existing_matrix, existing_pay

    def get(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        items = list(req.items.all().order_by("order", "id"))
        if not items:
            messages.warning(request, "Primero definí empresas y sucursales.")
            return self.redirect_to("catalog:wizard_step_2_companies")

        actions, matrix, payments = self._active_catalogs()

        # Groups para tabs (Generales, Comercial, etc.)
        action_groups = sorted({a.group for a in actions})

        if req.same_modules_for_all:
            ss = items[0].selection_set
            existing_actions, existing_matrix, existing_pay = self._build_initial_for_selection_set(
                ss)

            # --------- ACTIONS initial ---------
            action_initial = []
            for ap in actions:
                row = {"action_permission_id": ap.id}
                r = existing_actions.get(ap.id)
                if r:
                    row.update(
                        {
                            "value_bool": r.value_bool,
                            "value_int": r.value_int,
                            "value_decimal": r.value_decimal,
                            "value_text": r.value_text,
                        }
                    )
                action_initial.append(row)

            # --------- MATRIX initial ---------
            matrix_initial = []
            for mp in matrix:
                row = {"permission_id": mp.id}
                r = existing_matrix.get(mp.id)
                if r:
                    row.update(
                        {
                            "can_create": r.can_create,
                            "can_update": r.can_update,
                            "can_authorize": r.can_authorize,
                            "can_close": r.can_close,
                            "can_cancel": r.can_cancel,
                            "can_update_validity": r.can_update_validity,
                        }
                    )
                matrix_initial.append(row)

            # --------- PAYMENTS initial ---------
            pay_initial = []
            for pm in payments:
                row = {"payment_method_id": pm.id}
                r = existing_pay.get(pm.id)
                if r:
                    row["enabled"] = bool(r.enabled)
                pay_initial.append(row)

            # Formsets
            action_fs = ActionValueFormSet(
                prefix="actions",
                initial=action_initial,
                action_permissions=actions,
            )
            matrix_fs = MatrixFormSet(prefix="matrix", initial=matrix_initial)
            pay_fs = PaymentFormSet(prefix="payments", initial=pay_initial)

            # IMPORTANTÍSIMO: zip (modelo, form) para template limpio
            action_rows = list(zip(actions, action_fs.forms))
            matrix_rows = list(zip(matrix, matrix_fs.forms))
            payment_rows = list(zip(payments, pay_fs.forms))

            return render(
                request,
                self.template_name,
                self.wizard_context(
                    request_obj=req,
                    mode="GLOBAL",
                    items=items,

                    # catálogos
                    actions=actions,
                    matrix_perms=matrix,
                    payment_methods=payments,

                    # formsets
                    action_formset=action_fs,
                    matrix_formset=matrix_fs,
                    payment_formset=pay_fs,

                    # extras que usa el template
                    action_groups=action_groups,
                    action_rows=action_rows,
                    matrix_rows=matrix_rows,
                    payment_rows=payment_rows,
                ),
            )

        # -------------------------
        # PER_ITEM (backend listo)
        # -------------------------
        blocks = []
        for it in items:
            ss = it.selection_set
            existing_actions, existing_matrix, existing_pay = self._build_initial_for_selection_set(
                ss)

            action_initial = []
            for ap in actions:
                row = {"action_permission_id": ap.id}
                r = existing_actions.get(ap.id)
                if r:
                    row.update(
                        {
                            "value_bool": r.value_bool,
                            "value_int": r.value_int,
                            "value_decimal": r.value_decimal,
                            "value_text": r.value_text,
                        }
                    )
                action_initial.append(row)

            matrix_initial = []
            for mp in matrix:
                row = {"permission_id": mp.id}
                r = existing_matrix.get(mp.id)
                if r:
                    row.update(
                        {
                            "can_create": r.can_create,
                            "can_update": r.can_update,
                            "can_authorize": r.can_authorize,
                            "can_close": r.can_close,
                            "can_cancel": r.can_cancel,
                            "can_update_validity": r.can_update_validity,
                        }
                    )
                matrix_initial.append(row)

            pay_initial = []
            for pm in payments:
                row = {"payment_method_id": pm.id}
                r = existing_pay.get(pm.id)
                if r:
                    row["enabled"] = bool(r.enabled)
                pay_initial.append(row)

            a_fs = ActionValueFormSet(
                prefix=f"it_{it.id}_a",
                initial=action_initial,
                action_permissions=actions,
            )
            m_fs = MatrixFormSet(
                prefix=f"it_{it.id}_m", initial=matrix_initial)
            p_fs = PaymentFormSet(prefix=f"it_{it.id}_p", initial=pay_initial)

            blocks.append(
                {
                    "item": it,
                    "action_formset": a_fs,
                    "matrix_formset": m_fs,
                    "payment_formset": p_fs,
                    "action_rows": list(zip(actions, a_fs.forms)),
                    "matrix_rows": list(zip(matrix, m_fs.forms)),
                    "payment_rows": list(zip(payments, p_fs.forms)),
                }
            )

        return render(
            request,
            self.template_name,
            self.wizard_context(
                request_obj=req,
                mode="PER_ITEM",
                items=items,
                actions=actions,
                matrix_perms=matrix,
                payment_methods=payments,
                blocks=blocks,
                action_groups=action_groups,  # útil para futuro template per-item
            ),
        )

    @transaction.atomic
    def post(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        items = list(req.items.all().order_by("order", "id"))
        if not items:
            return self.redirect_to("catalog:wizard_step_2_companies")

        actions, matrix, payments = self._active_catalogs()

        if req.same_modules_for_all:
            action_fs = ActionValueFormSet(
                data=request.POST, prefix="actions", action_permissions=actions)
            matrix_fs = MatrixFormSet(data=request.POST, prefix="matrix")
            pay_fs = PaymentFormSet(data=request.POST, prefix="payments")

            if not (action_fs.is_valid() and matrix_fs.is_valid() and pay_fs.is_valid()):
                return render(
                    request,
                    self.template_name,
                    self.wizard_context(
                        request_obj=req,
                        mode="GLOBAL",
                        items=items,
                        actions=actions,
                        matrix_perms=matrix,
                        payment_methods=payments,
                        action_groups=sorted({a.group for a in actions}),
                        action_formset=action_fs,
                        matrix_formset=matrix_fs,
                        payment_formset=pay_fs,
                        action_rows=list(zip(actions, action_fs.forms)),
                        matrix_rows=list(zip(matrix, matrix_fs.forms)),
                        payment_rows=list(zip(payments, pay_fs.forms)),
                    ),
                )

            # Build payloads
            actions_by_id = {a.id: a for a in actions}
            matrix_by_id = {m.id: m for m in matrix}
            pay_by_id = {p.id: p for p in payments}

            action_items = []
            for f in action_fs:
                ap_id = f.cleaned_data["action_permission_id"]
                ap = actions_by_id.get(ap_id)
                if not ap:
                    continue
                action_items.append(
                    {
                        "action_permission": ap,
                        "value_bool": f.cleaned_data.get("value_bool"),
                        "value_int": f.cleaned_data.get("value_int"),
                        "value_decimal": f.cleaned_data.get("value_decimal"),
                        "value_text": f.cleaned_data.get("value_text"),
                    }
                )

            matrix_items = []
            for f in matrix_fs:
                pid = f.cleaned_data["permission_id"]
                mp = matrix_by_id.get(pid)
                if not mp:
                    continue
                matrix_items.append(
                    {
                        "permission": mp,
                        "can_create": f.cleaned_data.get("can_create"),
                        "can_update": f.cleaned_data.get("can_update"),
                        "can_authorize": f.cleaned_data.get("can_authorize"),
                        "can_close": f.cleaned_data.get("can_close"),
                        "can_cancel": f.cleaned_data.get("can_cancel"),
                        "can_update_validity": f.cleaned_data.get("can_update_validity"),
                    }
                )

            payment_items = []
            for f in pay_fs:
                pm_id = f.cleaned_data["payment_method_id"]
                pm = pay_by_id.get(pm_id)
                if not pm:
                    continue
                payment_items.append(
                    {"payment_method": pm, "enabled": bool(f.cleaned_data.get("enabled"))})

            # Apply to all selection_sets
            for it in items:
                save_globals_for_selection_set(
                    it.selection_set,
                    action_items=action_items,
                    matrix_items=matrix_items,
                    payment_items=payment_items,
                )

            messages.success(request, "Permisos globales guardados.")
            return self.redirect_to("catalog:wizard_step_5_scoped")

        # PER_ITEM (plantilla futura, pero backend listo)
        all_valid = True
        blocks = []

        for it in items:
            a_fs = ActionValueFormSet(
                data=request.POST, prefix=f"it_{it.id}_a", action_permissions=actions)
            m_fs = MatrixFormSet(data=request.POST, prefix=f"it_{it.id}_m")
            p_fs = PaymentFormSet(data=request.POST, prefix=f"it_{it.id}_p")

            if not (a_fs.is_valid() and m_fs.is_valid() and p_fs.is_valid()):
                all_valid = False

            blocks.append({"item": it, "action_formset": a_fs,
                          "matrix_formset": m_fs, "payment_formset": p_fs,
                           "action_rows": list(zip(actions, a_fs.forms)),
                           "matrix_rows": list(zip(matrix, m_fs.forms)),
                           "payment_rows": list(zip(payments, p_fs.forms))})

        if not all_valid:
            return render(
                request,
                self.template_name,
                self.wizard_context(
                    request_obj=req,
                    mode="PER_ITEM",
                    items=items,
                    actions=actions,
                    matrix_perms=matrix,
                    payment_methods=payments,
                    blocks=blocks,
                    action_groups=sorted({a.group for a in actions}),
                ),
            )

        actions_by_id = {a.id: a for a in actions}
        matrix_by_id = {m.id: m for m in matrix}
        pay_by_id = {p.id: p for p in payments}

        for b in blocks:
            it = b["item"]
            a_fs = b["action_formset"]
            m_fs = b["matrix_formset"]
            p_fs = b["payment_formset"]

            action_items = []
            for f in a_fs:
                ap = actions_by_id.get(f.cleaned_data["action_permission_id"])
                if not ap:
                    continue
                action_items.append(
                    {
                        "action_permission": ap,
                        "value_bool": f.cleaned_data.get("value_bool"),
                        "value_int": f.cleaned_data.get("value_int"),
                        "value_decimal": f.cleaned_data.get("value_decimal"),
                        "value_text": f.cleaned_data.get("value_text"),
                    }
                )

            matrix_items = []
            for f in m_fs:
                mp = matrix_by_id.get(f.cleaned_data["permission_id"])
                if not mp:
                    continue
                matrix_items.append(
                    {
                        "permission": mp,
                        "can_create": f.cleaned_data.get("can_create"),
                        "can_update": f.cleaned_data.get("can_update"),
                        "can_authorize": f.cleaned_data.get("can_authorize"),
                        "can_close": f.cleaned_data.get("can_close"),
                        "can_cancel": f.cleaned_data.get("can_cancel"),
                        "can_update_validity": f.cleaned_data.get("can_update_validity"),
                    }
                )

            payment_items = []
            for f in p_fs:
                pm = pay_by_id.get(f.cleaned_data["payment_method_id"])
                if not pm:
                    continue
                payment_items.append(
                    {"payment_method": pm, "enabled": bool(f.cleaned_data.get("enabled"))})

            save_globals_for_selection_set(
                it.selection_set,
                action_items=action_items,
                matrix_items=matrix_items,
                payment_items=payment_items,
            )

        messages.success(
            request, "Permisos globales guardados por empresa/sucursal.")
        return self.redirect_to("catalog:wizard_step_5_scoped")
