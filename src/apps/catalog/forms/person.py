from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.person import RequestPersonData


class RequestPersonForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RequestPersonData
        fields = [
            "first_name",
            "last_name",
            "dni",
            "email",
            "mobile_phone",
            "job_title",
            "direct_manager",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "dni": forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "mobile_phone": forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
            "job_title": forms.TextInput(attrs={"autocomplete": "organization-title"}),
            "direct_manager": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def clean_dni(self):
        dni = (self.cleaned_data.get("dni") or "").strip()
        # UX: tolerante. Solo limpiamos espacios.
        return dni
