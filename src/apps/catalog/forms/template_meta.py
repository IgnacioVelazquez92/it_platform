# src/apps/catalog/forms/template_meta.py
from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.templates import AccessTemplate


class AccessTemplateMetaForm(BootstrapFormMixin, forms.ModelForm):
    """Formulario para editar los metadatos de un AccessTemplate."""

    class Meta:
        model = AccessTemplate
        fields = ["name", "department", "role_name", "notes", "is_active"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "name": "Nombre del template",
            "department": "Departamento",
            "role_name": "Rol / puesto",
            "notes": "Notas internas",
            "is_active": "Activo",
        }
