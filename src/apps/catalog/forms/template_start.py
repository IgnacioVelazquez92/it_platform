# src/apps/catalog/forms/template_start.py
from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin


class TemplateStartForm(BootstrapFormMixin, forms.Form):
    """Paso 0 del wizard de templates: metadatos del perfil."""

    name = forms.CharField(
        max_length=160,
        label="Nombre del modelo de acceso",
        help_text='Ej: "Vendedor — Sucursal estándar"',
    )
    department = forms.CharField(
        max_length=160,
        required=False,
        label="Departamento",
        help_text="Opcional.",
    )
    role_name = forms.CharField(
        max_length=160,
        required=False,
        label="Rol / Puesto",
        help_text='Ej: "Vendedor", "Supervisor de caja".',
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Notas internas",
    )
