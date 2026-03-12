# src/apps/catalog/views/template_wizard/step_0_start.py
from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.template_start import TemplateStartForm
from apps.catalog.models.templates import AccessTemplate

from .base import TemplateWizardBaseView


class TemplateWizardStep0StartView(TemplateWizardBaseView):
    step = 0
    progress_percent = 0
    template_name = "catalog/template_wizard/step_0_start.html"

    def _prefill_initial(self, wizard: dict) -> dict:
        initial: dict = {}
        tmpl_id = wizard.get("template_id")
        if tmpl_id:
            tmpl = AccessTemplate.objects.filter(pk=tmpl_id).first()
            if tmpl:
                initial = {
                    "name": tmpl.name,
                    "department": tmpl.department,
                    "role_name": tmpl.role_name,
                    "notes": tmpl.notes,
                }
        return initial

    def get(self, request):
        wizard = self.get_wizard(request)
        form = TemplateStartForm(initial=self._prefill_initial(wizard))
        return render(request, self.template_name, self._context(request, form))

    def _context(self, request, form):
        wizard = self.get_wizard(request)
        tmpl = self.get_template_obj(request) if wizard.get("template_id") else None
        return self.wizard_context(
            form=form,
            template_obj=tmpl,
            is_editing=self.is_edit_mode(request),
        )

    @transaction.atomic
    def post(self, request):
        form = TemplateStartForm(data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context(request, form))

        wizard = self.get_wizard(request)
        tmpl_id = wizard.get("template_id")
        tmpl = None

        if tmpl_id:
            # Actualizar metadata del template existente (usuario retrocedió al paso 0)
            AccessTemplate.objects.filter(pk=tmpl_id).update(
                name=form.cleaned_data["name"],
                department=form.cleaned_data["department"],
                role_name=form.cleaned_data["role_name"],
                notes=form.cleaned_data["notes"],
            )
            tmpl = AccessTemplate.objects.filter(pk=tmpl_id).first()
        else:
            # Crear un template en borrador (is_active=False)
            tmpl = AccessTemplate.objects.create(
                name=form.cleaned_data["name"],
                department=form.cleaned_data["department"],
                role_name=form.cleaned_data["role_name"],
                notes=form.cleaned_data["notes"],
                owner=request.user,
                is_active=False,  # draft hasta el review
            )
            tmpl_id = tmpl.pk

        if tmpl is None:
            return self.redirect_to("catalog:template_wizard_start")

        _, ensure_error = self.ensure_single_base_item(tmpl)
        if ensure_error:
            form.add_error(None, ensure_error)
            return render(request, self.template_name, self._context(request, form))

        wizard["template_id"] = tmpl_id
        wizard.setdefault("is_editing", False)
        self.set_wizard(request, wizard)

        messages.info(request, "Metadatos del modelo guardados.")
        return self.redirect_to("catalog:template_wizard_modules")
