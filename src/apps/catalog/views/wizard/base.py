# apps/catalog/views/wizard/base.py
from __future__ import annotations

from django.shortcuts import redirect
from django.urls import reverse
from django.views import View


WIZARD_SESSION_KEY = "catalog_wizard"


class WizardBaseView(View):
    step: int = 0
    total_steps: int = 5
    progress_percent: int = 0

    def get_wizard(self, request) -> dict:
        return request.session.get(WIZARD_SESSION_KEY, {})

    def set_wizard(self, request, data: dict) -> None:
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
