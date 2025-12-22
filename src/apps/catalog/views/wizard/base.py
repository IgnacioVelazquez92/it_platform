from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from apps.catalog.models import AccessRequest
from apps.catalog.models.requests import RequestKind, RequestStatus


WIZARD_SESSION_KEY = "catalog_wizard"
WIZARD_REQUEST_ID_KEY = "access_request_id"


class WizardBaseView(LoginRequiredMixin, View):
    step: int = 0
    total_steps: int = 6
    progress_percent: int = 0

    def get_wizard(self, request: HttpRequest) -> dict:
        return request.session.get(WIZARD_SESSION_KEY, {})

    def set_wizard(self, request: HttpRequest, data: dict) -> None:
        request.session[WIZARD_SESSION_KEY] = data
        request.session.modified = True

    def wizard_context(self, **extra):
        return {
            "step": self.step,
            "total_steps": self.total_steps,
            "progress_percent": self.progress_percent,
            **extra,
        }

    def redirect_to(self, name: str):
        return redirect(reverse(name))

    # -----------------------------
    # Request actual del wizard
    # -----------------------------
    def get_current_request_id(self, request: HttpRequest) -> int | None:
        wiz = self.get_wizard(request)
        return wiz.get(WIZARD_REQUEST_ID_KEY)

    def set_current_request_id(self, request: HttpRequest, request_id: int) -> None:
        wiz = self.get_wizard(request)
        wiz[WIZARD_REQUEST_ID_KEY] = request_id
        self.set_wizard(request, wiz)

    def get_current_request_obj(self, request: HttpRequest) -> AccessRequest | None:
        req_id = self.get_current_request_id(request)
        if not req_id:
            return None
        # Seguridad: el request debe pertenecer al usuario
        return get_object_or_404(AccessRequest, pk=req_id, owner=request.user)

    def ensure_request_obj(self, request: HttpRequest) -> AccessRequest:
        """
        Garantiza que exista un AccessRequest asociado al wizard.
        IMPORTANTE: no crea person_data aquí porque se carga en Step 1.
        Por eso, este método NO crea AccessRequest hasta que exista person_data.
        """
        obj = self.get_current_request_obj(request)
        if obj:
            return obj
        return None  # Step 1 lo crea cuando tenga person_data
