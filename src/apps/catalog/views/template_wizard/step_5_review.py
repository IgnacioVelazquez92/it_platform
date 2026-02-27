# src/apps/catalog/views/template_wizard/step_5_review.py
from __future__ import annotations

from collections import OrderedDict, defaultdict

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse

from apps.catalog.models.selections import (
    SelectionSetActionValue, SelectionSetMatrixPermission, SelectionSetPaymentMethod,
    SelectionSetLevel, SelectionSetSubLevel,
)
from apps.catalog.models.templates import AccessTemplate

from .base import TemplateWizardBaseView


def _build_levels_tree(ss) -> list[dict]:
    levels = list(
        SelectionSetLevel.objects.filter(selection_set=ss)
        .select_related("level__module")
        .order_by("level__module__name", "level__name")
    )
    sublevels = list(
        SelectionSetSubLevel.objects.filter(selection_set=ss)
        .select_related("sublevel__level__module", "sublevel__level")
        .order_by("sublevel__level__module__name", "sublevel__level__name", "sublevel__name")
    )
    mod_map: dict[int, dict] = {}
    for r in levels:
        m = r.level.module
        bucket = mod_map.setdefault(m.id, {"module": m, "levels": OrderedDict()})
        bucket["levels"].setdefault(r.level.id, {"level": r.level, "sublevels": []})
    for r in sublevels:
        sub = r.sublevel
        lvl = sub.level
        m = lvl.module
        bucket = mod_map.setdefault(m.id, {"module": m, "levels": OrderedDict()})
        lvl_bucket = bucket["levels"].setdefault(lvl.id, {"level": lvl, "sublevels": []})
        lvl_bucket["sublevels"].append(sub)
    out = []
    for _, bucket in sorted(mod_map.items(), key=lambda kv: kv[1]["module"].name):
        out.append({"module": bucket["module"], "levels": list(bucket["levels"].values())})
    return out


def _build_company_payload(base_ss, items_for_company) -> dict:
    levels_tree = _build_levels_tree(base_ss)
    modules = list(base_ss.modules.filter(is_active=True).order_by("name"))
    actions = list(
        SelectionSetActionValue.objects.filter(selection_set=base_ss, is_active=True)
        .select_related("action_permission").order_by("action_permission__group", "action_permission__action")
    )
    actions_by_group = defaultdict(list)
    action_groups_order = []
    for r in actions:
        ap = r.action_permission
        if ap.value_type == "BOOL":
            val = "Sí" if bool(r.value_bool) else "No"
            if val != "Sí":
                continue
        elif ap.value_type == "INT":
            val = "" if r.value_int is None else str(r.value_int)
            if not val:
                continue
        elif ap.value_type in ("DECIMAL", "PERCENT"):
            val = "" if r.value_decimal is None else str(r.value_decimal)
            if not val:
                continue
        else:
            val = (r.value_text or "").strip()
            if not val:
                continue
        if ap.group not in actions_by_group:
            action_groups_order.append(ap.group)
        actions_by_group[ap.group].append({"name": ap.action, "val": val, "value_type": ap.value_type})

    matrix = [
        r for r in SelectionSetMatrixPermission.objects.filter(selection_set=base_ss)
        .select_related("permission").order_by("permission__name")
        if any([r.can_create, r.can_update, r.can_authorize, r.can_close, r.can_cancel, r.can_update_validity])
    ]
    payment_methods = list(
        SelectionSetPaymentMethod.objects.filter(selection_set=base_ss, enabled=True, is_active=True)
        .select_related("payment_method").order_by("payment_method__name")
    )

    return {
        "modules": modules, "levels_tree": levels_tree,
        "action_groups": action_groups_order, "actions_by_group": dict(actions_by_group),
        "matrix": matrix, "payment_methods": [x.payment_method for x in payment_methods],
    }


class TemplateWizardStep5ReviewView(TemplateWizardBaseView):
    step = 3
    progress_percent = 100
    template_name = "catalog/template_wizard/step_5_review.html"

    def _get_template(self, request) -> AccessTemplate:
        tmpl = self.get_template_obj(request)
        if not tmpl:
            raise AccessTemplate.DoesNotExist
        return tmpl

    def _build_context(self, tmpl: AccessTemplate) -> dict:
        item, ensure_error = self.ensure_single_base_item(tmpl)
        if ensure_error or item is None:
            return {"template_obj": tmpl, "payload": None, "review_error": ensure_error}
        payload = _build_company_payload(item.selection_set, [item])
        return {"template_obj": tmpl, "payload": payload, "review_error": None}

    def get(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        ctx = self._build_context(tmpl)
        return render(request, self.template_name, self.wizard_context(**ctx))

    @transaction.atomic
    def post(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        # Activate the template
        tmpl.is_active = True
        tmpl.save(update_fields=["is_active", "updated_at"])

        self.clear_wizard(request)
        messages.success(request, f'Modelo "{tmpl.name}" creado correctamente.')
        return redirect(reverse("catalog:template_detail", args=[tmpl.pk]))
