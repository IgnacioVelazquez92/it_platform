from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.step_3_modules import Step3ModulesForm
from apps.catalog.forms.helpers import (
    set_selection_set_modules,
    set_selection_set_sublevels,
    active_sublevels_for_modules,
)
from apps.catalog.models.modules import ErpModule, ErpModuleLevel, ErpModuleSubLevel
from apps.catalog.models.requests import AccessRequest
from apps.catalog.models.selections import PermissionSelectionSet

from .base import WizardBaseView


def build_module_tree() -> list[dict]:
    """
    Devuelve estructura lista para template:
    [
      {id, name, levels:[{id,name,sublevels:[{id,name}]}]}
    ]
    Solo activos.
    """
    modules = list(ErpModule.objects.filter(is_active=True).order_by("name"))

    levels = list(
        ErpModuleLevel.objects.filter(is_active=True, module__is_active=True)
        .select_related("module")
        .order_by("module__name", "name")
    )
    sublevels = list(
        ErpModuleSubLevel.objects.filter(
            is_active=True, level__is_active=True, level__module__is_active=True
        )
        .select_related("level", "level__module")
        .order_by("level__module__name", "level__name", "name")
    )

    levels_by_module: dict[int, list[ErpModuleLevel]] = {}
    for lvl in levels:
        levels_by_module.setdefault(lvl.module_id, []).append(lvl)

    subs_by_level: dict[int, list[ErpModuleSubLevel]] = {}
    for s in sublevels:
        subs_by_level.setdefault(s.level_id, []).append(s)

    tree: list[dict] = []
    for m in modules:
        m_levels = []
        for lvl in levels_by_module.get(m.id, []):
            m_levels.append(
                {
                    "id": lvl.id,
                    "name": lvl.name,
                    "sublevels": [{"id": s.id, "name": s.name} for s in subs_by_level.get(lvl.id, [])],
                }
            )
        tree.append({"id": m.id, "name": m.name, "levels": m_levels})

    return tree


class WizardStep3ModulesView(WizardBaseView):
    step = 3
    progress_percent = 60
    template_name = "catalog/wizard/step_3_modules.html"

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
                "items__selection_set__modules",
                "items__selection_set__sublevels__sublevel",
            )
            .get(pk=req_id)
        )

    def get(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        items = list(req.items.all().order_by("order", "id"))
        if not items:
            messages.warning(request, "Primero definí empresas y sucursales.")
            return self.redirect_to("catalog:wizard_step_2_companies")

        module_tree = build_module_tree()

        if req.same_modules_for_all:
            ss = items[0].selection_set

            selected_module_ids = list(ss.modules.values_list("id", flat=True))

            # Si ya existen subniveles guardados, usarlos; si no, derivar default desde módulos actuales
            current_sub_ids = list(
                ss.sublevels.values_list("sublevel_id", flat=True))
            if current_sub_ids:
                selected_sublevel_ids = {str(x) for x in current_sub_ids}
            else:
                mods = list(ErpModule.objects.filter(
                    id__in=selected_module_ids, is_active=True))
                selected_sublevel_ids = {
                    str(s.id) for s in active_sublevels_for_modules(mods)}

            form = Step3ModulesForm(initial={"modules": selected_module_ids})

            return render(
                request,
                self.template_name,
                self.wizard_context(
                    request_obj=req,
                    mode="GLOBAL",
                    form=form,
                    items=items,
                    module_tree=module_tree,
                    selected_sublevel_ids=selected_sublevel_ids,
                ),
            )

        # PER_ITEM: forms por item + selected_sublevels por item
        forms_by_item = []
        for it in items:
            ss = it.selection_set
            selected_module_ids = list(ss.modules.values_list("id", flat=True))
            current_sub_ids = list(
                ss.sublevels.values_list("sublevel_id", flat=True))
            if current_sub_ids:
                selected_sub_ids = {str(x) for x in current_sub_ids}
            else:
                mods = list(ErpModule.objects.filter(
                    id__in=selected_module_ids, is_active=True))
                selected_sub_ids = {str(s.id)
                                    for s in active_sublevels_for_modules(mods)}

            forms_by_item.append(
                {
                    "item": it,
                    "form": Step3ModulesForm(prefix=f"it_{it.id}", initial={"modules": selected_module_ids}),
                    "selected_sublevel_ids": selected_sub_ids,
                }
            )

        return render(
            request,
            self.template_name,
            self.wizard_context(
                request_obj=req,
                mode="PER_ITEM",
                forms_by_item=forms_by_item,
                items=items,
                module_tree=module_tree,
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

        module_tree = build_module_tree()

        # bandera: si el usuario tocó refinamiento, llega refine_enabled=1
        refine_enabled = (request.POST.get("refine_enabled") == "1")

        if req.same_modules_for_all:
            form = Step3ModulesForm(data=request.POST)
            if not form.is_valid():
                selected_sublevel_ids = set(request.POST.getlist("sublevels"))
                return render(
                    request,
                    self.template_name,
                    self.wizard_context(
                        request_obj=req,
                        mode="GLOBAL",
                        form=form,
                        items=items,
                        module_tree=module_tree,
                        selected_sublevel_ids=selected_sublevel_ids,
                    ),
                )

            modules = list(form.cleaned_data["modules"])
            for it in items:
                set_selection_set_modules(it.selection_set, modules)

                if refine_enabled:
                    sub_ids = request.POST.getlist("sublevels")
                    sublevels = list(
                        ErpModuleSubLevel.objects.filter(
                            id__in=sub_ids,
                            is_active=True,
                            level__is_active=True,
                            level__module__is_active=True,
                        )
                    )
                    # Normalización: si refinó, guardamos exactamente lo seleccionado
                    set_selection_set_sublevels(it.selection_set, sublevels)
                else:
                    # Default: módulo seleccionado => todo subnivel del módulo
                    sublevels = active_sublevels_for_modules(modules)
                    set_selection_set_sublevels(it.selection_set, sublevels)

            messages.success(
                request, "Módulos (y detalle) guardados para todas las empresas.")
            return self.redirect_to("catalog:wizard_step_4_globals")

        # PER_ITEM
        forms_by_item = []
        all_valid = True

        cleaned_modules: dict[int, list[ErpModule]] = {}
        posted_sublevel_ids_by_item: dict[int, list[str]] = {}

        for it in items:
            f = Step3ModulesForm(data=request.POST, prefix=f"it_{it.id}")
            forms_by_item.append(
                {
                    "item": it,
                    "form": f,
                    "selected_sublevel_ids": set(request.POST.getlist(f"it_{it.id}-sublevels")),
                }
            )
            if not f.is_valid():
                all_valid = False
            else:
                cleaned_modules[it.id] = list(f.cleaned_data["modules"])
                posted_sublevel_ids_by_item[it.id] = request.POST.getlist(
                    f"it_{it.id}-sublevels")

        if not all_valid:
            return render(
                request,
                self.template_name,
                self.wizard_context(
                    request_obj=req,
                    mode="PER_ITEM",
                    forms_by_item=forms_by_item,
                    items=items,
                    module_tree=module_tree,
                ),
            )

        for it in items:
            modules = cleaned_modules[it.id]
            set_selection_set_modules(it.selection_set, modules)

            if refine_enabled:
                sub_ids = posted_sublevel_ids_by_item[it.id]
                sublevels = list(
                    ErpModuleSubLevel.objects.filter(
                        id__in=sub_ids,
                        is_active=True,
                        level__is_active=True,
                        level__module__is_active=True,
                    )
                )
                set_selection_set_sublevels(it.selection_set, sublevels)
            else:
                sublevels = active_sublevels_for_modules(modules)
                set_selection_set_sublevels(it.selection_set, sublevels)

        messages.success(request, "Módulos guardados por empresa/sucursal.")
        return self.redirect_to("catalog:wizard_step_4_globals")
