# apps/catalog/views/wizard/step_1_person.py
from __future__ import annotations

from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.person import RequestPersonForm
from apps.catalog.models.requests import AccessRequest, RequestKind
from .base import WizardBaseView


class WizardStep1PersonView(WizardBaseView):
    step = 1
    progress_percent = 20
    template_name = "catalog/wizard/step_1_person.html"

    def get(self, request):
        wizard = self.get_wizard(request)
        req = None

        if wizard.get("request_id"):
            req = AccessRequest.objects.select_related("person_data").get(
                pk=wizard["request_id"]
            )
            form = RequestPersonForm(instance=req.person_data)
        else:
            form = RequestPersonForm()

        return render(
            request,
            self.template_name,
            self.wizard_context(
                form=form,
                request_obj=req,
            ),
        )

    @transaction.atomic
    def post(self, request):
        wizard = self.get_wizard(request)
        req = None

        if wizard.get("request_id"):
            req = AccessRequest.objects.select_related("person_data").get(
                pk=wizard["request_id"]
            )
            form = RequestPersonForm(request.POST, instance=req.person_data)
        else:
            form = RequestPersonForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self.wizard_context(
                    form=form,
                    request_obj=req,
                ),
            )

        person = form.save()

        if not req:
            req = AccessRequest.objects.create(
                kind=RequestKind.ALTA,
                status="DRAFT",
                person_data=person,
            )

        wizard["request_id"] = req.pk
        self.set_wizard(request, wizard)

        return self.redirect_to("catalog:wizard_step_2_companies")
