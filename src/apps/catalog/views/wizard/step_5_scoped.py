from __future__ import annotations

import logging
from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.catalog.forms.helpers import clone_selection_set
from apps.catalog.forms.step_5_scoped import (
    CompanyScopedForm,
    BranchScopedForm,
)
from apps.catalog.models.requests import AccessRequest, AccessRequestItem
from apps.catalog.models.selections import (
    PermissionSelectionSet,
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
)

from .base import WizardBaseView

logger = logging.getLogger("apps.catalog")


class WizardStep5ScopedView(WizardBaseView):
    step = 5
    progress_percent = 90
    template_name = "catalog/wizard/step_5_scoped.html"

    # -------------------------------------------------
    # Debug helpers
    # -------------------------------------------------
    def _dbg_post_list(self, request, form, field_name: str, label: str, extra: str = ""):
        html_name = f"{form.prefix}-{field_name}"
        posted = request.POST.getlist(html_name)
        logger.debug(
            "[STEP5][POST] %s %s | prefix=%s field=%s posted_raw=%s",
            label, extra, form.prefix, field_name, posted,
        )

    def _dbg_mmcf(self, request, form, field_name: str, label: str, extra: str = ""):
        html_name = f"{form.prefix}-{field_name}"
        posted_ids = request.POST.getlist(html_name)

        try:
            qs_ids = list(
                form.fields[field_name].queryset.values_list("id", flat=True))
        except Exception:
            qs_ids = []

        logger.debug(
            "[STEP5][INVALID] %s %s | prefix=%s field=%s posted=%s valid_qs=%s field_errors=%s",
            label, extra, form.prefix, field_name, posted_ids, qs_ids[:200], form.errors.get(
                field_name),
        )

    def _dbg_form(self, request, form, label: str, extra: str = ""):
        # OJO: llamar form.is_valid() acá re-ejecuta validación.
        # Preferimos asumir que ya fue evaluado y solo loguear errores.
        logger.debug(
            "[STEP5][FORM] %s %s | prefix=%s",
            label, extra, form.prefix,
        )

        if form.is_valid():
            logger.debug("[STEP5][OK] %s %s | prefix=%s",
                         label, extra, form.prefix)
            return

        logger.debug("[STEP5][ERRORS] %s %s | errors=%s",
                     label, extra, dict(form.errors))

        for fn in ("control_panels", "sellers", "warehouses", "cash_registers"):
            if fn in form.fields:
                self._dbg_post_list(request, form, fn,
                                    label=label, extra=extra)
                self._dbg_mmcf(request, form, fn, label=label, extra=extra)

    # -------------------------------------------------
    # Internals
    # -------------------------------------------------
    def _get_request(self, request) -> AccessRequest:
        wizard = self.get_wizard(request)
        req_id = wizard.get("request_id")
        if not req_id:
            raise AccessRequest.DoesNotExist

        return (
            AccessRequest.objects
            .select_related("person_data")
            .prefetch_related(
                "items__selection_set__company",
                "items__selection_set__branch",
            )
            .get(pk=req_id)
        )

    def _company_initial(self, company, items_for_company):
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

    def _group_items(self, items):
        by_company = defaultdict(list)
        for it in items:
            by_company[it.selection_set.company_id].append(it)
        for cid in by_company:
            by_company[cid] = sorted(
                by_company[cid], key=lambda x: (x.order, x.id))
        return by_company

    # -------------------------------------------------
    # GET
    # -------------------------------------------------
    def get(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        items = list(req.items.all().order_by("order", "id"))
        if not items:
            messages.warning(request, "Primero definí empresas.")
            return self.redirect_to("catalog:wizard_step_2_companies")

        # Obtener sucursales elegidas del wizard
        wizard = self.get_wizard(request)
        selected_branch_ids = set(wizard.get("branch_ids") or [])

        grouped = self._group_items(items)
        companies_blocks = []

        for company_id, items_for_company in grouped.items():
            company = items_for_company[0].selection_set.company

            # Form de permisos globales (paneles, vendedores por empresa)
            company_form = CompanyScopedForm(
                prefix=f"c_{company_id}",
                initial=self._company_initial(company, items_for_company),
                company=company,
            )

            # Construir branches_blocks solo con sucursales elegidas en Step 2
            branches_blocks = []
            for branch in company.branches.filter(is_active=True, id__in=selected_branch_ids).order_by("name"):
                branch_form = BranchScopedForm(
                    prefix=f"b_{branch.id}_c_{company_id}",
                    branch=branch,
                )

                branches_blocks.append(
                    {
                        "branch": branch,
                        "form": branch_form,
                    }
                )

            companies_blocks.append(
                {
                    "company": company,
                    "company_form": company_form,
                    "branches_blocks": branches_blocks,
                }
            )

        return render(
            request,
            self.template_name,
            self.wizard_context(
                request_obj=req, companies_blocks=companies_blocks),
        )

    # -------------------------------------------------
    # POST
    # -------------------------------------------------
    @transaction.atomic
    def post(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        items = list(req.items.all().order_by("order", "id"))
        if not items:
            return self.redirect_to("catalog:wizard_step_2_companies")

        # Obtener sucursales elegidas del wizard
        wizard = self.get_wizard(request)
        selected_branch_ids = set(wizard.get("branch_ids") or [])

        grouped = self._group_items(items)
        companies_blocks = []
        ok = True

        # 1) Validación (company scoped + branch scoped)
        for company_id, items_for_company in grouped.items():
            company = items_for_company[0].selection_set.company

            # Validar permisos globales (paneles, vendedores)
            company_form = CompanyScopedForm(
                data=request.POST,
                prefix=f"c_{company_id}",
                company=company,
            )
            if not company_form.is_valid():
                ok = False
                self._dbg_form(
                    request,
                    company_form,
                    label="COMPANY",
                    extra=f"company={company_id}({company.name})",
                )

            # Validar depósitos/cajas solo para sucursales elegidas
            branches_blocks = []
            for branch in company.branches.filter(is_active=True, id__in=selected_branch_ids).order_by("name"):
                branch_form = BranchScopedForm(
                    data=request.POST,
                    prefix=f"b_{branch.id}_c_{company_id}",
                    branch=branch,
                )
                if not branch_form.is_valid():
                    ok = False
                    self._dbg_form(
                        request,
                        branch_form,
                        label="BRANCH",
                        extra=f"company={company_id}({company.name}) branch={branch.id}({branch.name})",
                    )

                branches_blocks.append(
                    {
                        "branch": branch,
                        "form": branch_form,
                    }
                )

            companies_blocks.append(
                {
                    "company": company,
                    "company_form": company_form,
                    "branches_blocks": branches_blocks,
                }
            )

        if not ok:
            logger.debug(
                "[STEP5] Validation failed. request_id=%s posted_keys=%s",
                req.id,
                sorted(list(request.POST.keys()))[:200],
            )
            return render(
                request,
                self.template_name,
                self.wizard_context(
                    request_obj=req, companies_blocks=companies_blocks),
            )

        # 2) Persistencia
        # Actualizar permisos globales y crear items para sucursales elegidas
        for block in companies_blocks:
            company = block["company"]
            company_form: CompanyScopedForm = block["company_form"]

            panels_qs = company_form.cleaned_data.get("control_panels")
            sellers_qs = company_form.cleaned_data.get("sellers")

            panel_ids = list(panels_qs.values_list(
                "id", flat=True)) if panels_qs is not None else []
            seller_ids = list(sellers_qs.values_list(
                "id", flat=True)) if sellers_qs is not None else []

            # Obtener el item base de la empresa (sin sucursal)
            base_item = None
            for it in items:
                if it.selection_set.company_id == company.id and not it.selection_set.branch_id:
                    base_item = it
                    break

            if not base_item:
                continue

            base_ss = base_item.selection_set

            # Actualizar permisos globales en el selection_set base
            SelectionSetControlPanel.objects.filter(
                selection_set=base_ss).delete()
            SelectionSetSeller.objects.filter(selection_set=base_ss).delete()

            if panel_ids:
                SelectionSetControlPanel.objects.bulk_create(
                    [
                        SelectionSetControlPanel(
                            selection_set=base_ss, control_panel_id=pid)
                        for pid in panel_ids
                    ]
                )
            if seller_ids:
                SelectionSetSeller.objects.bulk_create(
                    [
                        SelectionSetSeller(
                            selection_set=base_ss, seller_id=sid)
                        for sid in seller_ids
                    ]
                )

            # Borrar items con sucursal existentes y recrearlos con sucursales elegidas
            old_branch_items = list(
                req.items.filter(selection_set__company_id=company.id,
                                 selection_set__branch_id__isnull=False)
            )
            old_ss_ids = [it.selection_set_id for it in old_branch_items]

            # Borrar items y sus selection_sets si no están en uso
            for it in old_branch_items:
                it.delete()

            for ss_id in old_ss_ids:
                ss = PermissionSelectionSet.objects.filter(pk=ss_id).first()
                if ss and not ss.request_items.exists():
                    ss.delete()

            # Crear nuevos items para sucursales elegidas en Step 2
            selected_branches = company.branches.filter(
                is_active=True, id__in=selected_branch_ids
            ).order_by("name")

            next_order = max([it.order for it in items], default=-1) + 1

            for branch in selected_branches:
                ss = clone_selection_set(
                    base_ss, company=company, branch=branch)
                AccessRequestItem.objects.create(
                    request=req, selection_set=ss, order=next_order)
                next_order += 1

                # Guardar depósitos y cajas para esta sucursal
                # Primero borrar los que fueron clonados (si los hay)
                SelectionSetWarehouse.objects.filter(selection_set=ss).delete()
                SelectionSetCashRegister.objects.filter(
                    selection_set=ss).delete()

                for bb in block["branches_blocks"]:
                    if bb["branch"].id != branch.id:
                        continue

                    bf: BranchScopedForm = bb["form"]
                    warehouses_qs = bf.cleaned_data.get("warehouses")
                    cash_qs = bf.cleaned_data.get("cash_registers")

                    wh_ids = list(warehouses_qs.values_list(
                        "id", flat=True)) if warehouses_qs is not None else []
                    cr_ids = list(cash_qs.values_list("id", flat=True)
                                  ) if cash_qs is not None else []

                    if wh_ids:
                        SelectionSetWarehouse.objects.bulk_create(
                            [
                                SelectionSetWarehouse(
                                    selection_set=ss, warehouse_id=wid)
                                for wid in wh_ids
                            ]
                        )
                    if cr_ids:
                        SelectionSetCashRegister.objects.bulk_create(
                            [
                                SelectionSetCashRegister(
                                    selection_set=ss, cash_register_id=cid)
                                for cid in cr_ids
                            ]
                        )

        messages.success(request, "Accesos por empresa y sucursal guardados.")
        return self.redirect_to("catalog:wizard_step_6_review")
