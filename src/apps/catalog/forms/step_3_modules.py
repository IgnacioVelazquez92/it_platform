from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.modules import ErpModule


class Step3ModulesForm(BootstrapFormMixin, forms.Form):
    modules = forms.ModelMultipleChoiceField(
        label="Módulos",
        queryset=ErpModule.objects.filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
