from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.templates import AccessTemplate


class StartMode:
    TEMPLATE = "TEMPLATE"
    BLANK = "BLANK"


class StartRequestForm(BootstrapFormMixin, forms.Form):
    start_mode = forms.ChoiceField(
        label="¿Cómo querés empezar?",
        choices=[
            (StartMode.TEMPLATE, "Usar un template"),
            (StartMode.BLANK, "Empezar desde cero"),
        ],
        widget=forms.RadioSelect,
        initial=StartMode.TEMPLATE,
    )

    template = forms.ModelChoiceField(
        label="Template",
        queryset=AccessTemplate.objects.filter(
            is_active=True).order_by("-created_at"),
        required=False,
        empty_label="Seleccionar template…",
    )

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("start_mode")
        tpl = cleaned.get("template")

        if mode == StartMode.TEMPLATE and not tpl:
            self.add_error(
                "template", "Seleccioná un template o elegí 'Empezar desde cero'.")
        if mode == StartMode.BLANK:
            cleaned["template"] = None

        return cleaned
