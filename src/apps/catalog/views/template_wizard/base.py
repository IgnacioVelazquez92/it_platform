from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from apps.catalog.models.permissions.scoped import Company
from apps.catalog.models.selections import PermissionSelectionSet
from apps.catalog.models.templates import AccessTemplate, AccessTemplateItem

TEMPLATE_WIZARD_SESSION_KEY = "catalog_template_wizard"


class TemplateWizardBaseView(LoginRequiredMixin, View):
    step: int = 0
    total_steps: int = 3
    progress_percent: int = 0

    def get_wizard(self, request: HttpRequest) -> dict:
        return request.session.get(TEMPLATE_WIZARD_SESSION_KEY, {})

    def set_wizard(self, request: HttpRequest, data: dict) -> None:
        request.session[TEMPLATE_WIZARD_SESSION_KEY] = data
        request.session.modified = True

    def clear_wizard(self, request: HttpRequest) -> None:
        request.session.pop(TEMPLATE_WIZARD_SESSION_KEY, None)
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

    def get_template_id(self, request: HttpRequest) -> int | None:
        return self.get_wizard(request).get("template_id")

    def get_template_obj(self, request: HttpRequest) -> AccessTemplate | None:
        tmpl_id = self.get_template_id(request)
        if not tmpl_id:
            return None
        return get_object_or_404(AccessTemplate, pk=tmpl_id, owner=request.user)

    def ensure_single_base_item(self, tmpl: AccessTemplate) -> tuple[AccessTemplateItem | None, str | None]:
        """
        Garantiza que el template draft tenga un único item base, sin scope de sucursal.
        """
        items = list(tmpl.items.select_related("selection_set").order_by("order", "id"))

        if not items:
            company = Company.objects.filter(is_active=True).order_by("name").first()
            if not company:
                return None, "No hay empresas activas para inicializar el template."
            ss = PermissionSelectionSet.objects.create(company=company, branch=None)
            item = AccessTemplateItem.objects.create(template=tmpl, selection_set=ss, order=0)
            return item, None

        base_item = items[0]
        base_ss = base_item.selection_set
        if base_ss.branch_id is not None:
            base_ss.branch = None
            base_ss.save(update_fields=["branch"])

        if len(items) > 1:
            extra_items = items[1:]
            extra_ss_ids = [it.selection_set_id for it in extra_items]
            tmpl.items.filter(id__in=[it.id for it in extra_items]).delete()
            for ss_id in extra_ss_ids:
                ss = PermissionSelectionSet.objects.filter(pk=ss_id).first()
                if ss and not ss.request_items.exists() and not ss.template_items.exists():
                    ss.delete()

        if base_item.order != 0:
            base_item.order = 0
            base_item.save(update_fields=["order"])

        return base_item, None
