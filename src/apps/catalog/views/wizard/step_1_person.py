# apps/catalog/views/wizard/step_1_person.py
from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404, render

from apps.catalog.forms.person import RequestPersonForm
from apps.catalog.models.requests import AccessRequest, RequestKind, RequestStatus
from .base import WizardBaseView


class WizardStep1PersonView(WizardBaseView):
    step = 1
    progress_percent = 20
    template_name = "catalog/wizard/step_1_person.html"

    def _get_owned_request(self, request, wizard: dict) -> AccessRequest | None:
        """
        Recupera la solicitud del wizard pero SOLO si pertenece al usuario autenticado.
        """
        req_id = wizard.get("request_id")
        if not req_id:
            return None
        return get_object_or_404(
            AccessRequest.objects.select_related("person_data"),
            pk=req_id,
            owner=request.user,
        )

    def get(self, request):
        wizard = self.get_wizard(request)
        req = self._get_owned_request(request, wizard)

        if req:
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
        req = self._get_owned_request(request, wizard)

        if req:
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
                owner=request.user,  # <-- CLAVE: evita NOT NULL constraint failed
                kind=RequestKind.ALTA,
                status=RequestStatus.DRAFT,
                person_data=person,
            )
        else:
            # Por si el form guardó una nueva instancia (en general no pasa),
            # aseguramos consistencia.
            if req.person_data_id != person.pk:
                req.person_data = person
                req.save(update_fields=["person_data"])

        wizard["request_id"] = req.pk
        self.set_wizard(request, wizard)

        return self.redirect_to("catalog:wizard_step_2_companies")
