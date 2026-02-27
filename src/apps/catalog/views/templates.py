# src/apps/catalog/views/templates.py
from __future__ import annotations

from collections import OrderedDict, defaultdict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, ListView, UpdateView, DeleteView

from apps.catalog.forms.template_meta import AccessTemplateMetaForm
from apps.catalog.models.templates import AccessTemplate
from apps.catalog.models.selections import (
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
    SelectionSetLevel,
    SelectionSetSubLevel,
)


# ──────────────────────────────────────────────
# Lista
# ──────────────────────────────────────────────

class TemplateListView(LoginRequiredMixin, ListView):
    model = AccessTemplate
    template_name = "catalog/template/list.html"
    context_object_name = "templates"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            AccessTemplate.objects
            .select_related("owner")
            .prefetch_related("items")
            .filter(is_active=True)
            .order_by("-created_at")
        )

        q = (self.request.GET.get("q") or "").strip()
        dept = (self.request.GET.get("department") or "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(role_name__icontains=q) |
                Q(department__icontains=q)
            )
        if dept:
            qs = qs.filter(department__icontains=dept)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["department"] = (self.request.GET.get("department") or "").strip()
        return ctx


# ──────────────────────────────────────────────
# Detalle
# ──────────────────────────────────────────────

class TemplateDetailView(LoginRequiredMixin, DetailView):
    model = AccessTemplate
    template_name = "catalog/template/detail.html"
    context_object_name = "template_obj"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "items__selection_set__company",
                "items__selection_set__modules",
                "items__selection_set__action_values__action_permission",
                "items__selection_set__matrix_permissions__permission",
                "items__selection_set__payment_methods__payment_method",
                "items__selection_set__selected_levels__level__module",
                "items__selection_set__sublevels__sublevel__level__module",
            )
        )

    # -- helpers reutilizados del RequestDetailView --

    def _build_levels_tree(self, ss) -> list[dict]:
        levels_qs = (
            getattr(ss, "selected_levels", None).all()
            if hasattr(ss, "selected_levels")
            else SelectionSetLevel.objects.filter(selection_set=ss)
        )
        sublevels_qs = (
            getattr(ss, "sublevels", None).all()
            if hasattr(ss, "sublevels")
            else SelectionSetSubLevel.objects.filter(selection_set=ss)
        )

        levels = list(levels_qs.select_related("level__module").order_by(
            "level__module__name", "level__name"))
        sublevels = list(sublevels_qs.select_related("sublevel__level__module", "sublevel__level").order_by(
            "sublevel__level__module__name", "sublevel__level__name", "sublevel__name"
        ))

        mod_map: dict[int, dict] = {}
        for r in levels:
            m = r.level.module
            mod_bucket = mod_map.setdefault(m.id, {"module": m, "levels": OrderedDict()})
            mod_bucket["levels"].setdefault(r.level.id, {"level": r.level, "sublevels": []})

        for r in sublevels:
            sub = r.sublevel
            lvl = sub.level
            m = lvl.module
            mod_bucket = mod_map.setdefault(m.id, {"module": m, "levels": OrderedDict()})
            lvl_bucket = mod_bucket["levels"].setdefault(lvl.id, {"level": lvl, "sublevels": []})
            lvl_bucket["sublevels"].append(sub)

        out = []
        for _, bucket in sorted(mod_map.items(), key=lambda kv: kv[1]["module"].name):
            out.append({"module": bucket["module"], "levels": list(bucket["levels"].values())})
        return out

    def _build_company_payload(self, base_ss, items_for_company) -> dict:
        modules = list(base_ss.modules.filter(is_active=True).order_by("name"))
        levels_tree = self._build_levels_tree(base_ss)

        actions = list(
            SelectionSetActionValue.objects.filter(selection_set=base_ss, is_active=True)
            .select_related("action_permission")
            .order_by("action_permission__group", "action_permission__action")
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

        matrix = list(
            SelectionSetMatrixPermission.objects.filter(selection_set=base_ss)
            .select_related("permission")
            .order_by("permission__name")
        )
        matrix = [
            r for r in matrix
            if any([r.can_create, r.can_update, r.can_authorize, r.can_close, r.can_cancel, r.can_update_validity])
        ]

        payment_methods = list(
            SelectionSetPaymentMethod.objects.filter(selection_set=base_ss, enabled=True, is_active=True)
            .select_related("payment_method")
            .order_by("payment_method__name")
        )

        return {
            "modules": modules,
            "levels_tree": levels_tree,
            "action_groups": action_groups_order,
            "actions_by_group": dict(actions_by_group),
            "matrix": matrix,
            "payment_methods": [x.payment_method for x in payment_methods],
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tmpl: AccessTemplate = ctx["template_obj"]

        items = list(tmpl.items.all().order_by("order", "id"))

        companies_map: "OrderedDict[int, dict]" = OrderedDict()
        for it in items:
            ss = it.selection_set
            cid = ss.company_id
            bucket = companies_map.get(cid)
            if bucket is None:
                bucket = {"company": ss.company, "items": []}
                companies_map[cid] = bucket
            bucket["items"].append(it)

        companies = []
        for _, bucket in companies_map.items():
            base_ss = bucket["items"][0].selection_set
            companies.append({
                "company": bucket["company"],
                "payload": self._build_company_payload(base_ss, bucket["items"]),
            })

        ctx["companies"] = companies
        ctx["can_edit"] = self.request.user.is_staff
        return ctx


# ──────────────────────────────────────────────
# Editar metadata
# ──────────────────────────────────────────────

class TemplateEditView(LoginRequiredMixin, UpdateView):
    model = AccessTemplate
    form_class = AccessTemplateMetaForm
    template_name = "catalog/template/edit.html"
    context_object_name = "template_obj"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.request.user.is_staff:
            raise PermissionDenied
        return obj

    def get_success_url(self):
        messages.success(self.request, "Template actualizado.")
        return reverse("catalog:template_detail", args=[self.object.pk])


# ──────────────────────────────────────────────
# Eliminar
# ──────────────────────────────────────────────

class TemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = AccessTemplate
    template_name = "catalog/template/confirm_delete.html"
    context_object_name = "template_obj"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.request.user.is_staff:
            raise PermissionDenied
        return obj

    @transaction.atomic
    def form_valid(self, form):
        tmpl = self.get_object()
        # Eliminar PermissionSelectionSets huérfanos asociados vía items
        selection_set_ids = list(
            tmpl.items.values_list("selection_set_id", flat=True)
        )
        response = super().form_valid(form)
        # Después de eliminar el template (y sus items en cascada), limpiar los selection_sets
        from apps.catalog.models.selections import PermissionSelectionSet
        PermissionSelectionSet.objects.filter(
            pk__in=selection_set_ids,
            template_items__isnull=True,
            request_items__isnull=True,
        ).delete()
        return response

    def get_success_url(self):
        messages.success(self.request, "Template eliminado.")
        return reverse("catalog:template_list")
