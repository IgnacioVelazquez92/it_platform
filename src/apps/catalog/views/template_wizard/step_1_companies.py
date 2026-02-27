# src/apps/catalog/views/template_wizard/step_1_companies.py
from __future__ import annotations

from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.step_2_companies import Step2CompaniesForm
from apps.catalog.models.permissions.scoped import Company, Branch
from apps.catalog.models.selections import PermissionSelectionSet
from apps.catalog.models.templates import AccessTemplate, AccessTemplateItem

from .base import TemplateWizardBaseView


class TemplateWizardStep1CompaniesView(TemplateWizardBaseView):
    step = 1
    progress_percent = 20
    template_name = "catalog/template_wizard/step_1_companies.html"

    def _get_template(self, request) -> AccessTemplate:
        tmpl = self.get_template_obj(request)
        if not tmpl:
            raise AccessTemplate.DoesNotExist
        return tmpl

    def _context_lists(self, *, form, tmpl):
        companies_qs = Company.objects.filter(is_active=True).order_by("name")
        branches_qs = (
            Branch.objects.filter(is_active=True)
            .select_related("company")
            .order_by("company__name", "name")
        )
        branches_by_company: dict[int, list] = defaultdict(list)
        for b in branches_qs:
            branches_by_company[b.company_id].append(b)
        company_blocks = [
            {"company": c, "branches": branches_by_company.get(c.id, [])}
            for c in companies_qs
        ]
        return self.wizard_context(
            form=form,
            template_obj=tmpl,
            companies_qs=companies_qs,
            company_blocks=company_blocks,
        )

    def get(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        wizard = self.get_wizard(request)
        initial: dict = {}
        if wizard.get("company_ids"):
            initial["companies"] = wizard["company_ids"]
        if wizard.get("same_modules_for_all") is not None:
            initial["same_modules_for_all"] = "1" if wizard["same_modules_for_all"] else "0"

        if not initial.get("companies") and tmpl.items.exists():
            company_ids = [it.selection_set.company_id for it in tmpl.items.select_related("selection_set__company")]
            initial["companies"] = sorted(set(company_ids))

        form = Step2CompaniesForm(initial=initial)
        return render(request, self.template_name, self._context_lists(form=form, tmpl=tmpl))

    @transaction.atomic
    def post(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        form = Step2CompaniesForm(data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context_lists(form=form, tmpl=tmpl))

        companies = list(form.cleaned_data["companies"])
        branches = list(form.cleaned_data.get("branches") or [])
        same_modules_for_all = form.cleaned_data["same_modules_for_all"] == "1"

        # Reconstruir items (si el usuario retrocedió y cambió empresas)
        old_ss_ids = list(tmpl.items.values_list("selection_set_id", flat=True))
        tmpl.items.all().delete()
        for ss_id in old_ss_ids:
            ss = PermissionSelectionSet.objects.filter(pk=ss_id).first()
            if ss and not ss.request_items.exists() and not ss.template_items.exists():
                ss.delete()

        for order, company in enumerate(companies):
            ss = PermissionSelectionSet.objects.create(company=company, branch=None)
            AccessTemplateItem.objects.create(template=tmpl, selection_set=ss, order=order)

        wizard = self.get_wizard(request)
        wizard["company_ids"] = [c.id for c in companies]
        wizard["branch_ids"] = [b.id for b in branches]
        wizard["same_modules_for_all"] = same_modules_for_all
        self.set_wizard(request, wizard)

        messages.success(request, "Empresas guardadas.")
        return self.redirect_to("catalog:template_wizard_modules")
