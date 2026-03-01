from __future__ import annotations

from django import forms

from apps.catalog.models import Company


class TemplateExcelImportForm(forms.Form):
    excel_file = forms.FileField(label="Excel .xlsx")
    company = forms.ModelChoiceField(
        label="Empresa base",
        queryset=Company.objects.filter(is_active=True).order_by("name"),
        help_text="Se usa solo para el item base tecnico del template.",
    )
    replace_existing = forms.BooleanField(
        label="Reemplazar templates existentes",
        required=False,
        help_text="Si existe un template con el mismo nombre de solapa, lo reconstruye.",
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data["excel_file"]
        if not excel_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Solo se admiten archivos .xlsx.")
        return excel_file
