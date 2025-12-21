# src/apps/catalog/forms/bootstrap_mixins.py
"""
Mixins para integrar Bootstrap 5 con formularios Django.
Aplica automáticamente las clases CSS correctas a los widgets.
"""
from __future__ import annotations

from django import forms


class BootstrapFormMixin:
    """
    Mixin que aplica automáticamente clases Bootstrap 5 a todos los widgets del formulario.

    Uso: class MiFormulario(BootstrapFormMixin, forms.ModelForm):
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()

    def _apply_bootstrap_classes(self):
        """Aplica clases Bootstrap 5 a todos los campos del formulario."""
        for field_name, field in self.fields.items():
            widget = field.widget

            # Input de texto, email, número, URL, password, textarea
            if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.NumberInput,
                                   forms.URLInput, forms.PasswordInput, forms.Textarea)):
                self._add_class(widget, 'form-control')

            # Selects simples
            elif isinstance(widget, forms.Select):
                self._add_class(widget, 'form-select')

            # Selects múltiples (no checkboxes)
            elif isinstance(widget, forms.SelectMultiple):
                self._add_class(widget, 'form-select')
                widget.attrs['multiple'] = True

            # CheckboxSelectMultiple - cada checkbox necesita form-check-input
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                # No agregamos clase al contenedor, solo a los items individuales
                pass

            # Checkboxes individuales
            elif isinstance(widget, forms.CheckboxInput):
                self._add_class(widget, 'form-check-input')

            # Radio buttons
            elif isinstance(widget, forms.RadioSelect):
                # No agregamos clase al contenedor
                pass

            # Date/Time inputs
            elif isinstance(widget, (forms.DateInput, forms.TimeInput, forms.DateTimeInput)):
                self._add_class(widget, 'form-control')

    @staticmethod
    def _add_class(widget, class_name: str):
        """Agrega una clase CSS al widget sin duplicar."""
        current_classes = widget.attrs.get('class', '')
        if current_classes:
            classes = set(current_classes.split())
            classes.add(class_name)
            widget.attrs['class'] = ' '.join(sorted(classes))
        else:
            widget.attrs['class'] = class_name
