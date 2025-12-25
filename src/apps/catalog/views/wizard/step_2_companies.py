# src/apps/catalog/views/wizard/step_2_companies.py
from __future__ import annotations

from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.step_2_companies import Step2CompaniesForm
from apps.catalog.forms.helpers import clone_selection_set
from apps.catalog.models.permissions.scoped import Company, Branch
from apps.catalog.models.requests import AccessRequest, AccessRequestItem
from apps.catalog.models.selections import PermissionSelectionSet
from apps.catalog.models.templates import AccessTemplate

from .base import WizardBaseView


class WizardStep2CompaniesView(WizardBaseView):
    step = 2
    progress_percent = 40
    template_name = "catalog/wizard/step_2_companies.html"

    def _get_request(self, request) -> AccessRequest:
        wizard = self.get_wizard(request)
        req_id = wizard.get("request_id")
        if not req_id:
            raise AccessRequest.DoesNotExist
        return AccessRequest.objects.select_related("person_data").get(pk=req_id)

    def _context_lists(self, *, form, req):
        """
        Prepara estructuras para un template estable:
        - companies_qs: empresas activas
        - company_blocks: lista [{company, branches}] para referencia (no para selección)

        Nota: Las sucursales se eligen en Step 5 (scoped), no aquí.
        """
        companies_qs = Company.objects.filter(is_active=True).order_by("name")
        branches_qs = (
            Branch.objects.filter(is_active=True)
            .select_related("company")
            .order_by("company__name", "name")
        )

        branches_by_company: dict[int, list[Branch]] = defaultdict(list)
        for b in branches_qs:
            branches_by_company[b.company_id].append(b)

        company_blocks = [{"company": c, "branches": branches_by_company.get(
            c.id, [])} for c in companies_qs]

        return self.wizard_context(
            form=form,
            request_obj=req,
            companies_qs=companies_qs,
            company_blocks=company_blocks,
        )

    def get(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        wizard = self.get_wizard(request)

        # Prefill desde wizard (si existe) o desde items existentes
        initial: dict = {}
        if wizard.get("company_ids"):
            initial["companies"] = wizard["company_ids"]
        if wizard.get("same_modules_for_all") is not None:
            initial["same_modules_for_all"] = "1" if wizard["same_modules_for_all"] else "0"

        # Si no hay wizard pero ya hay items, prefill desde DB
        if not initial.get("companies") and req.items.exists():
            company_ids = []
            for it in req.items.select_related("selection_set__company"):
                company_ids.append(it.selection_set.company_id)

            initial["companies"] = sorted(set(company_ids))
            initial["same_modules_for_all"] = "1" if req.same_modules_for_all else "0"

        form = Step2CompaniesForm(initial=initial)

        return render(
            request,
            self.template_name,
            self._context_lists(form=form, req=req),
        )

    @transaction.atomic
    def post(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        wizard = self.get_wizard(request)
        form = Step2CompaniesForm(data=request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self._context_lists(form=form, req=req),
            )

        companies = list(form.cleaned_data["companies"])
        branches = list(form.cleaned_data.get("branches") or [])
        same_modules_for_all = form.cleaned_data["same_modules_for_all"] == "1"

        # Guardar flag en request (gobierna UX de pasos siguientes)
        req.same_modules_for_all = same_modules_for_all
        req.save(update_fields=["same_modules_for_all", "updated_at"])

        # Reconstrucción segura de items (si el usuario vuelve a Step 2 y cambia scope)
        old_selection_set_ids = list(
            req.items.values_list("selection_set_id", flat=True))
        req.items.all().delete()

        # Borrar selection_sets huérfanos creados por el wizard
        # (solo si no están usados por request_items ni templates)
        if old_selection_set_ids:
            for ss_id in old_selection_set_ids:
                ss = PermissionSelectionSet.objects.filter(pk=ss_id).first()
                if not ss:
                    continue
                if ss.request_items.exists():
                    continue
                if ss.templates_legacy.exists() or ss.template_items.exists():
                    continue
                ss.delete()

        # Base template (si existe)
        template_id = wizard.get("template_id")
        base_selection = None
        if template_id:
            tpl = (
                AccessTemplate.objects.select_related("selection_set")
                .filter(pk=template_id, is_active=True)
                .first()
            )
            if tpl:
                base_selection = tpl.selection_set

        created_items = 0

        # Crear items + selection sets: UNO POR EMPRESA (sin sucursal)
        # Las sucursales se configuran en Step 5 (scoped), no aquí.
        # El parámetro branches se ignora en la creación de items (solo se usa para UI feedback).
        for company in companies:
            if base_selection:
                ss = clone_selection_set(
                    base_selection, company=company, branch=None)
            else:
                ss = PermissionSelectionSet.objects.create(
                    company=company, branch=None)

            AccessRequestItem.objects.create(
                request=req, selection_set=ss, order=created_items)
            created_items += 1

        # Persistir wizard state para próximos steps
        wizard["company_ids"] = [c.id for c in companies]
        wizard["branch_ids"] = [b.id for b in branches]
        wizard["same_modules_for_all"] = same_modules_for_all
        self.set_wizard(request, wizard)

        messages.success(
            request, "Alcance guardado. Continuemos con módulos y permisos.")
        return self.redirect_to("catalog:wizard_step_3_modules")
