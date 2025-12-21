# src/apps/catalog/forms/bootstrap_mixins.py
from __future__ import annotations

from django import forms


class BootstrapFormMixin:
    """
    Aplica clases Bootstrap 5 a widgets típicos.
    - Inputs: form-control
    - Select: form-select
    - CheckboxInput: form-check-input
    Además:
    - Si un campo tiene errores -> agrega is-invalid
    """

    input_widgets = (
        forms.TextInput,
        forms.EmailInput,
        forms.NumberInput,
        forms.URLInput,
        forms.PasswordInput,
        forms.Textarea,
        forms.DateInput,
        forms.TimeInput,
        forms.DateTimeInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()
        self._apply_invalid_classes()

    def _apply_bootstrap_classes(self) -> None:
        for name, field in self.fields.items():
            widget = field.widget

            # Radio/checkbox groups: mejor render manual en template (no forzamos clases aquí)
            if isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                continue

            # Text-like inputs
            if isinstance(widget, self.input_widgets):
                self._add_class(widget, "form-control")
                continue

            # Select (incluye ModelChoiceField -> Select)
            if isinstance(widget, forms.Select):
                self._add_class(widget, "form-select")
                continue

            # Multi-select
            if isinstance(widget, forms.SelectMultiple):
                self._add_class(widget, "form-select")
                widget.attrs["multiple"] = True
                continue

            # Single checkbox
            if isinstance(widget, forms.CheckboxInput):
                self._add_class(widget, "form-check-input")
                continue

    def _apply_invalid_classes(self) -> None:
        """
        Agrega is-invalid a los widgets con errores.
        Esto funciona bien con form-control y form-select.
        """
        for name, errors in self.errors.items():
            field = self.fields.get(name)
            if not field:
                continue
            widget = field.widget
            # no forzar en grupos
            if isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                continue
            self._add_class(widget, "is-invalid")

    @staticmethod
    def _add_class(widget: forms.Widget, class_name: str) -> None:
        current = widget.attrs.get("class", "")
        classes = set(current.split()) if current else set()
        classes.add(class_name)
        widget.attrs["class"] = " ".join(sorted(classes))
