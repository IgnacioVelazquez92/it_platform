# src/apps/catalog/views/template_wizard/step_2_modules.py
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
from apps.catalog.models.modules import ErpModuleSubLevel
from apps.catalog.models.templates import AccessTemplate
from apps.catalog.views.wizard.step_3_modules import build_module_tree

from .base import TemplateWizardBaseView


class TemplateWizardStep2ModulesView(TemplateWizardBaseView):
    step = 1
    progress_percent = 33
    template_name = "catalog/template_wizard/step_2_modules.html"

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

        ss = item.selection_set
        module_tree = build_module_tree()
        selected_module_ids = list(ss.modules.values_list("id", flat=True))
        current_sub_ids = list(ss.sublevels.values_list("sublevel_id", flat=True))
        selected_sublevel_ids = (
            {str(x) for x in current_sub_ids} if current_sub_ids
            else {str(s.id) for s in active_sublevels_for_modules(
                list(ss.modules.filter(is_active=True).all()))}
        )
        form = Step3ModulesForm(initial={"modules": selected_module_ids})
        return render(request, self.template_name, self.wizard_context(
            template_obj=tmpl, mode="GLOBAL", form=form, items=[item],
            module_tree=module_tree, selected_sublevel_ids=selected_sublevel_ids,
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

        ss = item.selection_set
        module_tree = build_module_tree()
        refine_enabled = (request.POST.get("refine_enabled") == "1")
        form = Step3ModulesForm(data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self.wizard_context(
                template_obj=tmpl, mode="GLOBAL", form=form, items=[item],
                module_tree=module_tree,
                selected_sublevel_ids=set(request.POST.getlist("sublevels")),
            ))

        modules = list(form.cleaned_data["modules"])
        set_selection_set_modules(ss, modules)
        if refine_enabled:
            sub_ids = request.POST.getlist("sublevels")
            sublevels = list(ErpModuleSubLevel.objects.filter(
                id__in=sub_ids, is_active=True,
                level__is_active=True, level__module__is_active=True,
            ))
            set_selection_set_sublevels(ss, sublevels)
        else:
            set_selection_set_sublevels(ss, active_sublevels_for_modules(modules))

        messages.success(request, "Módulos guardados.")
        return self.redirect_to("catalog:template_wizard_globals")
