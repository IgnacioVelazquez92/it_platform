# src/apps/catalog/forms/person.py
from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.person import RequestPersonData


class RequestPersonDataForm(BootstrapFormMixin, forms.ModelForm):
    """
    Paso 1 del wizard: snapshot de datos personales.

    Principios:
    - Validación mínima y clara (evitar reglas ocultas).
    - Sanitizar espacios para consistencia.
    """

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

    # -------------------------
    # Helpers de sanitización
    # -------------------------

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(str(value or "").strip().split())

    def clean_first_name(self) -> str:
        v = self._clean_text(self.cleaned_data.get("first_name"))
        if not v:
            raise forms.ValidationError("El nombre es obligatorio.")
        return v

    def clean_last_name(self) -> str:
        v = self._clean_text(self.cleaned_data.get("last_name"))
        if not v:
            raise forms.ValidationError("El apellido es obligatorio.")
        return v

    def clean_dni(self) -> str:
        v = self._clean_text(self.cleaned_data.get("dni"))
        if not v:
            raise forms.ValidationError("El DNI es obligatorio.")
        return v

    def clean_mobile_phone(self) -> str:
        v = self._clean_text(self.cleaned_data.get("mobile_phone"))
        if not v:
            raise forms.ValidationError("El celular es obligatorio.")
        return v

    def clean_job_title(self) -> str:
        v = self._clean_text(self.cleaned_data.get("job_title"))
        if not v:
            raise forms.ValidationError("El puesto de trabajo es obligatorio.")
        return v

    def clean_direct_manager(self) -> str:
        # Puede ser vacío, pero sanitizamos.
        return self._clean_text(self.cleaned_data.get("direct_manager"))
