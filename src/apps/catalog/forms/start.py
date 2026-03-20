from __future__ import annotations

from django import forms

from apps.catalog.forms.bootstrap_mixins import BootstrapFormMixin
from apps.catalog.models.templates import AccessTemplate


class StartMode:
    TEMPLATE = "TEMPLATE"
    BLANK = "BLANK"
    MODEL_USER = "MODEL_USER"


class StartRequestForm(BootstrapFormMixin, forms.Form):
    start_mode = forms.ChoiceField(
        label="Como queres empezar?",
        choices=[
            (StartMode.TEMPLATE, "Usar template"),
            (StartMode.BLANK, "Empezar desde cero"),
            (StartMode.MODEL_USER, "Completar con usuario modelo (ERP)"),
        ],
        widget=forms.RadioSelect,
        initial=StartMode.TEMPLATE,
    )

    templates = forms.ModelMultipleChoiceField(
        label="Templates",
        queryset=AccessTemplate.objects.filter(is_active=True).order_by("-created_at"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("start_mode")
        templates = cleaned.get("templates")

        if mode == StartMode.TEMPLATE and not templates:
            self.add_error(
                "templates",
                "Selecciona al menos un template o elige 'Empezar desde cero'.",
            )
        if mode in (StartMode.BLANK, StartMode.MODEL_USER):
            cleaned["templates"] = AccessTemplate.objects.none()

        return cleaned
