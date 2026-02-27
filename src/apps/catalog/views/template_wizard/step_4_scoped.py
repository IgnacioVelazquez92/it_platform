# src/apps/catalog/views/template_wizard/step_4_scoped.py
from __future__ import annotations

from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.helpers import clone_selection_set
from apps.catalog.forms.step_5_scoped import CompanyScopedForm, BranchScopedForm
from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
)
from apps.catalog.models.templates import AccessTemplate, AccessTemplateItem

from .base import TemplateWizardBaseView


class TemplateWizardStep4ScopedView(TemplateWizardBaseView):
    step = 4
    progress_percent = 80
    template_name = "catalog/template_wizard/step_4_scoped.html"

    def _get_template(self, request) -> AccessTemplate:
        tmpl = self.get_template_obj(request)
        if not tmpl:
            raise AccessTemplate.DoesNotExist
        return tmpl

    def _group_items(self, items):
        by_company: dict[int, list] = defaultdict(list)
        for it in items:
            by_company[it.selection_set.company_id].append(it)
        return by_company

    def _company_initial(self, items_for_company):
        ss = items_for_company[0].selection_set
        return {
            "control_panels": list(ss.control_panels.values_list("control_panel_id", flat=True)),
            "sellers": list(ss.sellers.values_list("seller_id", flat=True)),
        }

    def _branch_initial(self, ss: PermissionSelectionSet):
        return {
            "warehouses": list(ss.warehouses.values_list("warehouse_id", flat=True)),
            "cash_registers": list(ss.cash_registers.values_list("cash_register_id", flat=True)),
        }

    def get(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        items = list(tmpl.items.all().order_by("order", "id"))
        if not items:
            messages.warning(request, "Primero configurá módulos y permisos globales.")
            return self.redirect_to("catalog:template_wizard_modules")

        wizard = self.get_wizard(request)
        selected_branch_ids = set(wizard.get("branch_ids") or [])
        grouped = self._group_items(items)
        companies_blocks = []

        for company_id, items_for_company in grouped.items():
            company = items_for_company[0].selection_set.company
            company_form = CompanyScopedForm(
                prefix=f"c_{company_id}",
                initial=self._company_initial(items_for_company),
                company=company,
            )
            branches_blocks = []
            for branch in company.branches.filter(is_active=True, id__in=selected_branch_ids).order_by("name"):
                # Look for an existing SS for this branch in the template
                branch_ss = None
                for it in items_for_company:
                    if it.selection_set.branch_id == branch.id:
                        branch_ss = it.selection_set
                        break
                branch_form = BranchScopedForm(
                    prefix=f"b_{branch.id}_c_{company_id}",
                    branch=branch,
                    initial=self._branch_initial(branch_ss) if branch_ss else {},
                )
                branches_blocks.append({"branch": branch, "form": branch_form})

            companies_blocks.append({
                "company": company,
                "company_form": company_form,
                "branches_blocks": branches_blocks,
            })

        return render(request, self.template_name, self.wizard_context(
            template_obj=tmpl, companies_blocks=companies_blocks,
        ))

    @transaction.atomic
    def post(self, request):
        try:
            tmpl = self._get_template(request)
        except AccessTemplate.DoesNotExist:
            return self.redirect_to("catalog:template_wizard_start")

        items = list(tmpl.items.all().order_by("order", "id"))
        if not items:
            return self.redirect_to("catalog:template_wizard_modules")

        wizard = self.get_wizard(request)
        selected_branch_ids = set(wizard.get("branch_ids") or [])
        grouped = self._group_items(items)
        companies_blocks = []
        ok = True

        for company_id, items_for_company in grouped.items():
            company = items_for_company[0].selection_set.company
            company_form = CompanyScopedForm(
                data=request.POST, prefix=f"c_{company_id}", company=company,
            )
            if not company_form.is_valid():
                ok = False

            branches_blocks = []
            for branch in company.branches.filter(
                    is_active=True, id__in=selected_branch_ids).order_by("name"):
                branch_form = BranchScopedForm(
                    data=request.POST,
                    prefix=f"b_{branch.id}_c_{company_id}",
                    branch=branch,
                )
                if not branch_form.is_valid():
                    ok = False
                branches_blocks.append({"branch": branch, "form": branch_form})

            companies_blocks.append({
                "company": company,
                "company_form": company_form,
                "branches_blocks": branches_blocks,
                "items_for_company": items_for_company,
            })

        if not ok:
            return render(request, self.template_name, self.wizard_context(
                template_obj=tmpl, companies_blocks=companies_blocks,
            ))

        # Persist
        for block in companies_blocks:
            company = block["company"]
            company_form: CompanyScopedForm = block["company_form"]
            items_for_company = block["items_for_company"]

            panels_qs = company_form.cleaned_data.get("control_panels")
            sellers_qs = company_form.cleaned_data.get("sellers")
            panel_ids = list(panels_qs.values_list("id", flat=True)) if panels_qs else []
            seller_ids = list(sellers_qs.values_list("id", flat=True)) if sellers_qs else []

            # Base item for this company (without branch)
            base_item = next(
                (it for it in items_for_company if not it.selection_set.branch_id),
                None,
            )
            if not base_item:
                continue
            base_ss = base_item.selection_set

            # Update panels and sellers on the base SS
            SelectionSetControlPanel.objects.filter(selection_set=base_ss).delete()
            SelectionSetSeller.objects.filter(selection_set=base_ss).delete()
            if panel_ids:
                SelectionSetControlPanel.objects.bulk_create([
                    SelectionSetControlPanel(selection_set=base_ss, control_panel_id=pid)
                    for pid in panel_ids
                ])
            if seller_ids:
                SelectionSetSeller.objects.bulk_create([
                    SelectionSetSeller(selection_set=base_ss, seller_id=sid)
                    for sid in seller_ids
                ])

            # Remove existing branch-level items and recreate
            old_branch_items = [it for it in items_for_company if it.selection_set.branch_id]
            old_ss_ids = [it.selection_set_id for it in old_branch_items]
            for it in old_branch_items:
                it.delete()
            for ss_id in old_ss_ids:
                ss = PermissionSelectionSet.objects.filter(pk=ss_id).first()
                if ss and not ss.request_items.exists() and not ss.template_items.exists():
                    ss.delete()

            selected_branches = company.branches.filter(
                is_active=True, id__in=selected_branch_ids,
            ).order_by("name")
            next_order = max((it.order for it in items), default=-1) + 1

            for branch in selected_branches:
                new_ss = clone_selection_set(base_ss, company=company, branch=branch)
                new_item = AccessTemplateItem.objects.create(
                    template=tmpl, selection_set=new_ss, order=next_order,
                )
                next_order += 1

                # Clear cloned scoped data and set branch-specific data
                SelectionSetWarehouse.objects.filter(selection_set=new_ss).delete()
                SelectionSetCashRegister.objects.filter(selection_set=new_ss).delete()

                for bb in block["branches_blocks"]:
                    if bb["branch"].id != branch.id:
                        continue
                    bf: BranchScopedForm = bb["form"]
                    wh_qs = bf.cleaned_data.get("warehouses")
                    cr_qs = bf.cleaned_data.get("cash_registers")
                    wh_ids = list(wh_qs.values_list("id", flat=True)) if wh_qs else []
                    cr_ids = list(cr_qs.values_list("id", flat=True)) if cr_qs else []
                    if wh_ids:
                        SelectionSetWarehouse.objects.bulk_create([
                            SelectionSetWarehouse(selection_set=new_ss, warehouse_id=wid)
                            for wid in wh_ids
                        ])
                    if cr_ids:
                        SelectionSetCashRegister.objects.bulk_create([
                            SelectionSetCashRegister(selection_set=new_ss, cash_register_id=cid)
                            for cid in cr_ids
                        ])

        messages.success(request, "Accesos por empresa y sucursal guardados.")
        return self.redirect_to("catalog:template_wizard_review")
