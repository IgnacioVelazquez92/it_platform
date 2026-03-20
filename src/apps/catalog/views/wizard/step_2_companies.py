# src/apps/catalog/views/wizard/step_2_companies.py
from __future__ import annotations

from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.start import StartMode
from apps.catalog.forms.step_2_companies import Step2CompaniesForm
from apps.catalog.forms.helpers import clone_selection_set, merge_selection_sets
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
        wizard = self.get_wizard(self.request)
        selected_company_ids = set(wizard.get("company_ids") or [])
        selected_branch_ids = set(wizard.get("branch_ids") or [])
        clone_model_by_company = wizard.get("clone_model_by_company") or {}
        start_mode = wizard.get("start_mode")

        companies_qs = Company.objects.filter(is_active=True).order_by("name")
        branches_qs = (
            Branch.objects.filter(is_active=True)
            .select_related("company")
            .order_by("company__name", "name")
        )

        branches_by_company: dict[int, list[Branch]] = defaultdict(list)
        for branch in branches_qs:
            branches_by_company[branch.company_id].append(branch)

        company_blocks = [
            {"company": company, "branches": branches_by_company.get(company.id, [])}
            for company in companies_qs
        ]

        return self.wizard_context(
            form=form,
            request_obj=req,
            companies_qs=companies_qs,
            company_blocks=company_blocks,
            selected_company_ids=selected_company_ids,
            selected_branch_ids=[str(branch_id) for branch_id in selected_branch_ids],
            clone_model_by_company=clone_model_by_company,
            start_mode=start_mode,
            is_blank_mode=(start_mode == StartMode.BLANK),
            is_model_user_mode=(start_mode == StartMode.MODEL_USER),
        )

    def _get_template_base_selections(self, wizard: dict) -> list[PermissionSelectionSet]:
        template_ids = wizard.get("template_ids") or []
        if not template_ids and wizard.get("template_id"):
            template_ids = [wizard["template_id"]]
        if not template_ids:
            return []

        templates = list(
            AccessTemplate.objects.select_related("selection_set")
            .prefetch_related("items__selection_set")
            .filter(pk__in=template_ids, is_active=True)
        )
        templates_by_id = {tpl.id: tpl for tpl in templates}

        selections: list[PermissionSelectionSet] = []
        for template_id in template_ids:
            tpl = templates_by_id.get(template_id)
            if tpl is None:
                continue
            base_selection = tpl.selection_set
            if base_selection is None:
                first_item = tpl.items.order_by("order", "id").first()
                if first_item:
                    base_selection = first_item.selection_set
            if base_selection is not None:
                selections.append(base_selection)
        return selections

    def get(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        wizard = self.get_wizard(request)

        initial: dict = {}
        if wizard.get("company_ids"):
            initial["companies"] = wizard["company_ids"]
        if wizard.get("same_modules_for_all") is not None:
            initial["same_modules_for_all"] = "1" if wizard["same_modules_for_all"] else "0"

        if not initial.get("companies") and req.items.exists():
            company_ids = []
            for item in req.items.select_related("selection_set__company"):
                company_ids.append(item.selection_set.company_id)

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
        start_mode = wizard.get("start_mode")
        is_model_user_mode = start_mode == StartMode.MODEL_USER

        clone_model_by_company: dict[str, str] = {}
        missing_model_user_companies: list[str] = []

        for company in companies:
            model_user_ref = (request.POST.get(f"clone_user_{company.id}") or "").strip()
            if not model_user_ref:
                if is_model_user_mode:
                    missing_model_user_companies.append(company.name)
                continue
            clone_model_by_company[str(company.id)] = model_user_ref

        if missing_model_user_companies:
            form.add_error(
                None,
                "En modo 'usuario modelo', debes completar el usuario modelo en todas las empresas seleccionadas: "
                + ", ".join(missing_model_user_companies),
            )
            return render(
                request,
                self.template_name,
                self._context_lists(form=form, req=req),
            )

        req.same_modules_for_all = same_modules_for_all
        req.save(update_fields=["same_modules_for_all", "updated_at"])

        old_selection_set_ids = list(req.items.values_list("selection_set_id", flat=True))
        req.items.all().delete()

        for selection_set_id in old_selection_set_ids:
            selection_set = PermissionSelectionSet.objects.filter(pk=selection_set_id).first()
            if not selection_set:
                continue
            if selection_set.request_items.exists():
                continue
            if selection_set.templates_legacy.exists() or selection_set.template_items.exists():
                continue
            selection_set.delete()

        base_selections = self._get_template_base_selections(wizard)

        created_items = 0
        for company in companies:
            if len(base_selections) > 1:
                selection_set = merge_selection_sets(base_selections, company=company, branch=None)
            elif len(base_selections) == 1:
                selection_set = clone_selection_set(base_selections[0], company=company, branch=None)
            else:
                selection_set = PermissionSelectionSet.objects.create(company=company, branch=None)

            model_user_ref = clone_model_by_company.get(str(company.id), "").strip()
            if model_user_ref:
                selection_set.notes = f"Usuario modelo ERP (texto libre): {model_user_ref}"
                selection_set.save(update_fields=["notes"])

            AccessRequestItem.objects.create(
                request=req,
                selection_set=selection_set,
                order=created_items,
            )
            created_items += 1

        wizard["company_ids"] = [company.id for company in companies]
        wizard["branch_ids"] = [branch.id for branch in branches]
        wizard["same_modules_for_all"] = same_modules_for_all
        wizard["clone_model_by_company"] = clone_model_by_company
        self.set_wizard(request, wizard)

        if clone_model_by_company:
            messages.success(
                request,
                f"Se guardo referencia de usuario modelo (texto libre) en {len(clone_model_by_company)} empresa(s).",
            )

        if is_model_user_mode:
            messages.success(
                request,
                "Alcance guardado. Como iniciaste por usuario modelo, pasamos directo a revision para enviar.",
            )
            return self.redirect_to("catalog:wizard_step_6_review")

        if len(base_selections) > 1:
            messages.success(
                request,
                f"Alcance guardado. Se fusionaron {len(base_selections)} templates base y seguimos con modulos y permisos.",
            )
        else:
            messages.success(request, "Alcance guardado. Continuemos con modulos y permisos.")
        return self.redirect_to("catalog:wizard_step_3_modules")
