# apps/catalog/views/wizard/step_0_start.py
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse

from apps.catalog.forms.start import StartRequestForm, StartMode
from .base import WizardBaseView


class WizardStep0StartView(WizardBaseView):
    step = 0
    progress_percent = 0
    template_name = "catalog/wizard/step_0_start.html"

    def get(self, request):
        wizard = self.get_wizard(request)
        initial = dict(wizard)
        if wizard.get("template_ids"):
            initial["templates"] = wizard["template_ids"]
        elif wizard.get("template_id"):
            initial["templates"] = [wizard["template_id"]]
        form = StartRequestForm(initial=initial)

        return render(
            request,
            self.template_name,
            self.wizard_context(
                form=form,
                request_obj=None,
            ),
        )

    def post(self, request):
        form = StartRequestForm(data=request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self.wizard_context(
                    form=form,
                    request_obj=None,
                ),
            )

        wizard = self.get_wizard(request)
        wizard.update(
            {
                "start_mode": form.cleaned_data["start_mode"],
                "template_ids": [tpl.pk for tpl in form.cleaned_data.get("templates", [])],
                "template_id": (
                    form.cleaned_data["templates"][0].pk
                    if form.cleaned_data.get("templates")
                    else None
                ),
                "request_id": None,
            }
        )
        self.set_wizard(request, wizard)

        messages.info(request, "Inicio configurado correctamente.")
        return self.redirect_to("catalog:wizard_step_1_person")
