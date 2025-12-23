# src/apps/catalog/views/requests.py
from __future__ import annotations

from collections import OrderedDict, defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, TemplateView

from apps.catalog.models.requests import AccessRequest
from apps.catalog.models.selections import (
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
    SelectionSetControlPanel,
    SelectionSetSeller,
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetLevel,
    SelectionSetSubLevel,
)


class RequestDetailView(LoginRequiredMixin, DetailView):
    model = AccessRequest
    template_name = "catalog/request/detail.html"
    context_object_name = "request_obj"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("person_data")
            .prefetch_related(
                "items__selection_set__company",
                "items__selection_set__branch",
                "items__selection_set__modules",
                "items__selection_set__selected_modules__module",
                "items__selection_set__warehouses__warehouse",
                "items__selection_set__cash_registers__cash_register",
                "items__selection_set__control_panels__control_panel",
                "items__selection_set__sellers__seller",
                "items__selection_set__action_values__action_permission",
                "items__selection_set__matrix_permissions__permission",
                "items__selection_set__payment_methods__payment_method",
                # Árbol:
                "items__selection_set__selected_levels__level__module",
                "items__selection_set__sublevels__sublevel__level__module",
            )
        )

    # -------- helpers (solo lectura) --------
    def _build_levels_tree(self, ss) -> list[dict]:
        # Usa prefetch si está, y si no, igual funciona por query.
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
            mod_bucket = mod_map.setdefault(
                m.id, {"module": m, "levels": OrderedDict()})
            mod_bucket["levels"].setdefault(
                r.level.id, {"level": r.level, "sublevels": []})

        for r in sublevels:
            sub = r.sublevel
            lvl = sub.level
            m = lvl.module
            mod_bucket = mod_map.setdefault(
                m.id, {"module": m, "levels": OrderedDict()})
            lvl_bucket = mod_bucket["levels"].setdefault(
                lvl.id, {"level": lvl, "sublevels": []})
            lvl_bucket["sublevels"].append(sub)

        out = []
        for _, bucket in sorted(mod_map.items(), key=lambda kv: kv[1]["module"].name):
            out.append({"module": bucket["module"], "levels": list(
                bucket["levels"].values())})
        return out

    def _build_company_payload(self, base_ss, items_for_company) -> dict:
        # Módulos
        modules = list(base_ss.modules.filter(is_active=True).order_by("name"))
        levels_tree = self._build_levels_tree(base_ss)

        # Paneles / vendedores (por empresa)
        control_panels = list(
            SelectionSetControlPanel.objects.filter(selection_set=base_ss)
            .select_related("control_panel")
            .order_by("control_panel__name")
        )
        sellers = list(
            SelectionSetSeller.objects.filter(selection_set=base_ss)
            .select_related("seller")
            .order_by("seller__name")
        )

        # Acciones (solo las activas y con “valor útil”)
        actions = list(
            SelectionSetActionValue.objects.filter(
                selection_set=base_ss, is_active=True)
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
            actions_by_group[ap.group].append(
                {"name": ap.action, "val": val, "value_type": ap.value_type})

        # Matriz (solo filas con checks)
        matrix = list(
            SelectionSetMatrixPermission.objects.filter(selection_set=base_ss)
            .select_related("permission")
            .order_by("permission__name")
        )
        matrix = [
            r for r in matrix
            if any([r.can_create, r.can_update, r.can_authorize, r.can_close, r.can_cancel, r.can_update_validity])
        ]

        # Medios de pago (solo habilitados)
        payment_methods = list(
            SelectionSetPaymentMethod.objects.filter(
                selection_set=base_ss, enabled=True, is_active=True)
            .select_related("payment_method")
            .order_by("payment_method__name")
        )

        # Scoped por sucursal (solo depósitos y cajas)
        branches = []
        for it in items_for_company:
            ss = it.selection_set

            warehouses = list(
                SelectionSetWarehouse.objects.filter(selection_set=ss)
                .select_related("warehouse")
                .order_by("warehouse__name")
            )
            cash_registers = list(
                SelectionSetCashRegister.objects.filter(selection_set=ss)
                .select_related("cash_register")
                .order_by("cash_register__name")
            )

            # Si no hay nada scoped y querés ocultar la fila, podés filtrar acá.
            branches.append({
                "branch": ss.branch,
                "warehouses": [x.warehouse for x in warehouses],
                "cash_registers": [x.cash_register for x in cash_registers],
            })

        return {
            "modules": modules,
            "levels_tree": levels_tree,
            "control_panels": [x.control_panel for x in control_panels],
            "sellers": [x.seller for x in sellers],
            "action_groups": action_groups_order,
            "actions_by_group": dict(actions_by_group),
            "matrix": matrix,
            "payment_methods": [x.payment_method for x in payment_methods],
            "branches": branches,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req: AccessRequest = ctx["request_obj"]

        items = list(req.items.all().order_by("order", "id"))

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
        ctx["items"] = items
        return ctx


class RequestSubmittedView(LoginRequiredMixin, TemplateView):
    template_name = "catalog/request/submitted.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = AccessRequest.objects.select_related(
            "person_data").get(pk=self.kwargs["pk"])
        ctx["request_obj"] = req
        return ctx
