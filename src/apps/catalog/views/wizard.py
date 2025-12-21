from __future__ import annotations
from django.forms import BaseFormSet, formset_factory

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.catalog.forms import (
    BootstrapFormMixin,
    RequestPersonDataForm,
    SelectionSetScopeModulesForm,
    SelectionSetScopedSelectionsForm,
    make_action_value_formset,
    make_matrix_permission_formset,
    make_payment_method_formset,
)
from apps.catalog.forms.helpers import ensure_global_rows_exist
from apps.catalog.models.permissions.scoped import Branch, Company
from apps.catalog.models.requests import AccessRequest, AccessRequestItem, RequestKind, RequestStatus
from apps.catalog.models.selections import PermissionSelectionSet
from apps.catalog.models.templates import AccessTemplate


# ---------------------------
# Forms auxiliares del wizard
# ---------------------------

class TemplateCompaniesForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=AccessTemplate.objects.filter(
            is_active=True).order_by("name"),
        required=False,
        empty_label="(Sin template)",
        label="Template",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    companies = forms.ModelMultipleChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by("name"),
        required=True,
        label="Empresas",
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'form-check-input'}),
        help_text="Seleccioná una o más empresas. Luego vas a asignar sucursal y scopes por cada una.",
    )
    kind = forms.ChoiceField(
        choices=RequestKind.choices,
        initial=RequestKind.ALTA,
        required=True,
        label="Tipo de solicitud",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class BranchPerItemForm(forms.Form):
    item_id = forms.IntegerField(widget=forms.HiddenInput)
    company_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"readonly": "readonly", "class": "form-control"}))
    branches = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.none(),
        required=True,
        label="Sucursales",
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, company: Company, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branches"].queryset = Branch.objects.filter(
            company=company, is_active=True).order_by("name")


class BaseBranchPerItemFormSet(BaseFormSet):
    """
    Inyecta 'company' en cada form según el item correspondiente.
    """

    def __init__(self, *args, items=None, **kwargs):
        self.items = list(items or [])
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kw = super().get_form_kwargs(index)
        # index puede ser None en algunos casos; lo cubrimos.
        if index is None:
            return kw
        company = self.items[index].selection_set.company
        kw["company"] = company
        return kw


BranchPerItemFormSet = formset_factory(
    BranchPerItemForm,
    formset=BaseBranchPerItemFormSet,
    extra=0,
)

# ---------------------------
# Helpers de clonación
# ---------------------------


def clone_selection_set_from_template(*, template: AccessTemplate, company: Company) -> PermissionSelectionSet:
    """
    Clona el selection_set base del template, pero forzando company (branch queda para el step 3).
    Replica módulos + globales (action/matrix/payment).
    """
    src = template.selection_set

    ss = PermissionSelectionSet.objects.create(
        company=company,
        branch=None,
        notes=f"Clonado desde template: {template.name}",
    )

    # módulos (through)
    ss.modules.set(src.modules.all())

    # global bootstrap + copy valores
    ensure_global_rows_exist(ss)
    ensure_global_rows_exist(src)

    # Copiar ActionValues
    src_actions = {x.action_permission_id: x for x in src.action_values.all()}
    for row in ss.action_values.all():
        src_row = src_actions.get(row.action_permission_id)
        if src_row:
            row.value_bool = src_row.value_bool
            row.value_int = src_row.value_int
            row.value_decimal = src_row.value_decimal
            row.value_text = src_row.value_text
            row.is_active = src_row.is_active
            row.save(update_fields=["value_bool", "value_int",
                     "value_decimal", "value_text", "is_active"])

    # Copiar PaymentMethods
    src_pm = {x.payment_method_id: x for x in src.payment_methods.all()}
    for row in ss.payment_methods.all():
        src_row = src_pm.get(row.payment_method_id)
        if src_row:
            row.enabled = src_row.enabled
            row.is_active = src_row.is_active
            row.save(update_fields=["enabled", "is_active"])

    # Copiar Matrix
    src_mx = {x.permission_id: x for x in src.matrix_permissions.all()}
    for row in ss.matrix_permissions.all():
        src_row = src_mx.get(row.permission_id)
        if src_row:
            row.can_create = src_row.can_create
            row.can_update = src_row.can_update
            row.can_authorize = src_row.can_authorize
            row.can_close = src_row.can_close
            row.can_cancel = src_row.can_cancel
            row.can_update_validity = src_row.can_update_validity
            row.save(update_fields=[
                "can_create", "can_update", "can_authorize", "can_close",
                "can_cancel", "can_update_validity"
            ])

    return ss


def replicate_globals(*, src: PermissionSelectionSet, targets: List[PermissionSelectionSet]) -> None:
    """
    Aplica globales (módulos + action/matrix/payment) de src a todos los targets.
    """
    ensure_global_rows_exist(src)

    for t in targets:
        t.modules.set(src.modules.all())
        ensure_global_rows_exist(t)

        # actions
        src_actions = {
            x.action_permission_id: x for x in src.action_values.all()}
        for row in t.action_values.all():
            s = src_actions.get(row.action_permission_id)
            if s:
                row.value_bool = s.value_bool
                row.value_int = s.value_int
                row.value_decimal = s.value_decimal
                row.value_text = s.value_text
                row.is_active = s.is_active
                row.save(update_fields=[
                         "value_bool", "value_int", "value_decimal", "value_text", "is_active"])

        # payments
        src_pm = {x.payment_method_id: x for x in src.payment_methods.all()}
        for row in t.payment_methods.all():
            s = src_pm.get(row.payment_method_id)
            if s:
                row.enabled = s.enabled
                row.is_active = s.is_active
                row.save(update_fields=["enabled", "is_active"])

        # matrix
        src_mx = {x.permission_id: x for x in src.matrix_permissions.all()}
        for row in t.matrix_permissions.all():
            s = src_mx.get(row.permission_id)
            if s:
                row.can_create = s.can_create
                row.can_update = s.can_update
                row.can_authorize = s.can_authorize
                row.can_close = s.can_close
                row.can_cancel = s.can_cancel
                row.can_update_validity = s.can_update_validity
                row.save(update_fields=[
                    "can_create", "can_update", "can_authorize", "can_close",
                    "can_cancel", "can_update_validity"
                ])


# ---------------------------
# Wizard Steps
# ---------------------------

class WizardStep1PersonView(LoginRequiredMixin, View):
    template_name = "catalog/wizard/step_1_person.html"

    def get(self, request, request_id: Optional[int] = None):
        if request_id:
            ar = get_object_or_404(AccessRequest, pk=request_id)
            form = RequestPersonDataForm(instance=ar.person_data)
        else:
            ar = None
            form = RequestPersonDataForm()
        return render(request, self.template_name, {"form": form, "request_obj": ar, "step": 1})

    @transaction.atomic
    def post(self, request, request_id: Optional[int] = None):
        ar = None
        if request_id:
            ar = get_object_or_404(AccessRequest, pk=request_id)
            form = RequestPersonDataForm(request.POST, instance=ar.person_data)
        else:
            form = RequestPersonDataForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "request_obj": ar, "step": 1})

        person = form.save()

        if not ar:
            ar = AccessRequest.objects.create(
                kind=RequestKind.ALTA,
                status=RequestStatus.DRAFT,
                person_data=person,
                selection_set=None,
            )
            messages.success(
                request, "Datos de persona guardados. Continuá con el modelo y empresas.")
        else:
            messages.success(request, "Datos de persona actualizados.")

        return redirect("catalog:w_step_2", request_id=ar.id)


class WizardStep2TemplateCompaniesView(LoginRequiredMixin, View):
    template_name = "catalog/wizard/step_2_template_companies.html"

    def get(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        form = TemplateCompaniesForm(initial={"kind": ar.kind})
        return render(request, self.template_name, {"form": form, "request_obj": ar, "step": 2})

    @transaction.atomic
    def post(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        form = TemplateCompaniesForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "request_obj": ar, "step": 2})

        ar.kind = form.cleaned_data["kind"]
        ar.save(update_fields=["kind"])

        template: Optional[AccessTemplate] = form.cleaned_data["template"]
        companies = list(form.cleaned_data["companies"])

        # Rehacer items para mantener simple (modo wizard).
        ar.items.all().delete()

        for idx, company in enumerate(companies):
            if template:
                ss = clone_selection_set_from_template(
                    template=template, company=company)
            else:
                ss = PermissionSelectionSet.objects.create(
                    company=company, branch=None, notes="")
                ensure_global_rows_exist(ss)  # prepara tablas globales

            AccessRequestItem.objects.create(
                request=ar, selection_set=ss, order=idx)

        messages.success(
            request, "Empresas asignadas. Ahora definí la sucursal por empresa.")
        return redirect("catalog:w_step_3", request_id=ar.id)


class WizardStep3BranchesView(LoginRequiredMixin, View):
    template_name = "catalog/wizard/step_3_branches.html"

    def get(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        items = list(ar.items.select_related(
            "selection_set__company").order_by("order"))

        initial = []
        for it in items:
            ss = it.selection_set
            initial.append({
                "item_id": it.id,
                "company_name": ss.company.name,
                "branch": ss.branch_id,
            })

        formset = BranchPerItemFormSet(initial=initial, items=items)

        return render(
            request,
            self.template_name,
            {"formset": formset, "items": items, "request_obj": ar, "step": 3},
        )

    @transaction.atomic
    def post(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        placeholders = list(ar.items.select_related(
            "selection_set__company").order_by("order"))

        formset = BranchPerItemFormSet(request.POST, items=placeholders)
        if not formset.is_valid():
            return render(...)

        # Para orden estable
        new_items: list[AccessRequestItem] = []
        order = 0

        # Map placeholder por id
        by_id = {it.id: it for it in placeholders}

        for f in formset:
            item_id = f.cleaned_data["item_id"]
            branches = list(f.cleaned_data["branches"])
            placeholder_item = by_id[item_id]
            placeholder_ss = placeholder_item.selection_set
            company = placeholder_ss.company

            # Eliminamos placeholder (y su selection_set)
            placeholder_item.delete()
            placeholder_ss.delete()

            # Creamos items reales por sucursal
            for br in branches:
                ss = PermissionSelectionSet.objects.create(
                    company=company,
                    branch=br,
                    notes=f"{company.name} / {br.name}",
                )

                # Copiar globales desde un “base” común:
                # Si estás usando template o cargaste global una vez,
                # podés replicar desde el selection_set base del request
                ensure_global_rows_exist(ss)
                # replicate_globals(src=BASE_GLOBAL_SS, targets=[ss])  # recomendado

                new_items.append(AccessRequestItem.objects.create(
                    request=ar,
                    selection_set=ss,
                    order=order,
                ))
                order += 1

        messages.success(
            request, "Sucursales guardadas. Ahora completá los scopes por sucursal.")
        return redirect("catalog:w_step_4", request_id=ar.id)


class WizardStep4ScopedView(LoginRequiredMixin, View):
    template_name = "catalog/wizard/step_4_scoped.html"

    def get(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        items = list(ar.items.select_related(
            "selection_set__company", "selection_set__branch").order_by("order"))

        forms = []
        for it in items:
            ss = it.selection_set
            forms.append((it, SelectionSetScopedSelectionsForm(
                instance=ss, prefix=f"item-{it.id}")))

        return render(request, self.template_name, {"request_obj": ar, "items_forms": forms, "step": 4})

    @transaction.atomic
    def post(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        items = list(ar.items.select_related(
            "selection_set__company", "selection_set__branch").order_by("order"))

        forms = []
        ok = True
        for it in items:
            ss = it.selection_set
            f = SelectionSetScopedSelectionsForm(
                request.POST, instance=ss, prefix=f"item-{it.id}")
            forms.append((it, f))
            ok = ok and f.is_valid()

        if not ok:
            return render(request, self.template_name, {"request_obj": ar, "items_forms": forms, "step": 4})

        for it, f in forms:
            f.save()

        messages.success(
            request, "Scopes guardados. Ahora revisá/cargá permisos globales (una sola vez).")
        return redirect("catalog:w_step_5", request_id=ar.id)


class WizardStep5GlobalView(LoginRequiredMixin, View):
    template_name = "catalog/wizard/step_5_global.html"

    def _get_base_selection_set(self, ar: AccessRequest) -> PermissionSelectionSet:
        # Elegimos el primer item como base global.
        item = ar.items.select_related(
            "selection_set").order_by("order").first()
        return item.selection_set

    def get(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        base_ss = self._get_base_selection_set(ar)

        scope_form = SelectionSetScopeModulesForm(
            instance=base_ss, prefix="scope_modules")

        actions_fs = make_action_value_formset(
            selection_set=base_ss, prefix="actions")
        matrix_fs = make_matrix_permission_formset(
            selection_set=base_ss, prefix="matrix")
        payments_fs = make_payment_method_formset(
            selection_set=base_ss, prefix="payments")

        return render(
            request,
            self.template_name,
            {
                "request_obj": ar,
                "base_ss": base_ss,
                "scope_form": scope_form,
                "actions_fs": actions_fs,
                "matrix_fs": matrix_fs,
                "payments_fs": payments_fs,
                "step": 5,
            },
        )

    @transaction.atomic
    def post(self, request, request_id: int):
        ar = get_object_or_404(AccessRequest, pk=request_id)
        base_ss = self._get_base_selection_set(ar)

        scope_form = SelectionSetScopeModulesForm(
            request.POST, instance=base_ss, prefix="scope_modules")
        actions_fs = make_action_value_formset(
            selection_set=base_ss, data=request.POST, prefix="actions")
        matrix_fs = make_matrix_permission_formset(
            selection_set=base_ss, data=request.POST, prefix="matrix")
        payments_fs = make_payment_method_formset(
            selection_set=base_ss, data=request.POST, prefix="payments")

        ok = scope_form.is_valid() and actions_fs.is_valid(
        ) and matrix_fs.is_valid() and payments_fs.is_valid()
        if not ok:
            return render(
                request,
                self.template_name,
                {
                    "request_obj": ar,
                    "base_ss": base_ss,
                    "scope_form": scope_form,
                    "actions_fs": actions_fs,
                    "matrix_fs": matrix_fs,
                    "payments_fs": payments_fs,
                    "step": 5,
                },
            )

        scope_form.save()
        actions_fs.save()
        matrix_fs.save()
        payments_fs.save()

        # Replicar globales a todas las empresas del request
        targets = [it.selection_set for it in ar.items.select_related(
            "selection_set").order_by("order")[1:]]
        replicate_globals(src=base_ss, targets=targets)

        messages.success(
            request, "Permisos globales guardados y aplicados a todas las empresas.")
        return redirect("catalog:drafts")
