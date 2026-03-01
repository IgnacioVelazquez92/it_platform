from __future__ import annotations

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.db.models import Prefetch

from apps.catalog.forms.template_import import TemplateExcelImportForm
from apps.catalog.models import AccessTemplate, AccessTemplateItem
from apps.catalog.services.template_excel_import import (
    TemplateExcelImportError,
    import_templates_from_excel,
)


@admin.register(AccessTemplateItem)
class AccessTemplateItemAdmin(admin.ModelAdmin):
    """
    Admin opcional (útil para auditoría y búsquedas rápidas).
    """
    list_display = (
        "template",
        "order",
        "company",
        "branch",
        "selection_set",
        "created_at",
    )
    list_filter = (
        "selection_set__company",
        "selection_set__branch",
    )
    search_fields = (
        "template__name",
        "template__department",
        "template__role_name",
        "selection_set__notes",
    )
    ordering = ("template", "order", "id")
    autocomplete_fields = ("template", "selection_set")
    readonly_fields = ("created_at",)

    @admin.display(description="Empresa")
    def company(self, obj: AccessTemplateItem):
        return obj.selection_set.company

    @admin.display(description="Sucursal")
    def branch(self, obj: AccessTemplateItem):
        return obj.selection_set.branch or "-"


class AccessTemplateItemInline(admin.TabularInline):
    """
    Ítems del template: cada línea referencia un PermissionSelectionSet.
    """
    model = AccessTemplateItem
    extra = 0
    fields = ("order", "selection_set", "company",
              "branch", "notes", "created_at")
    readonly_fields = ("company", "branch", "created_at")
    autocomplete_fields = ("selection_set",)
    ordering = ("order", "id")

    @admin.display(description="Empresa")
    def company(self, obj: AccessTemplateItem):
        if not obj.selection_set_id:
            return "-"
        return obj.selection_set.company

    @admin.display(description="Sucursal")
    def branch(self, obj: AccessTemplateItem):
        if not obj.selection_set_id:
            return "-"
        return obj.selection_set.branch or "-"


@admin.register(AccessTemplate)
class AccessTemplateAdmin(admin.ModelAdmin):
    """
    Admin de Templates de acceso.

    Rol:
    - Definir perfiles reutilizables (cabecera)
    - Asociar 1..N selection_sets mediante items (líneas)
    - Activar / desactivar templates
    """

    list_display = (
        "name",
        "department",
        "role_name",
        "companies_summary",
        "branches_summary",
        "items_count",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "department",
        "role_name",
        "items__selection_set__company",
        "items__selection_set__branch",
    )
    search_fields = (
        "name",
        "department",
        "role_name",
        "notes",
    )
    ordering = ("-created_at",)
    list_editable = ("is_active",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Template",
            {
                "fields": ("name", "is_active"),
            },
        ),
        (
            "Perfil",
            {
                "fields": ("department", "role_name"),
                "description": "Datos orientativos del perfil.",
            },
        ),
        (
            "Notas",
            {
                "fields": ("notes",),
            },
        ),
        (
            "Trazabilidad",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    inlines = (AccessTemplateItemInline,)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel_view),
                name="catalog_accesstemplate_import_excel",
            ),
        ]
        return custom_urls + urls

    def import_excel_view(self, request):
        if not self.has_add_permission(request):
            return redirect(reverse("admin:index"))

        if request.method == "POST":
            form = TemplateExcelImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    result = import_templates_from_excel(
                        file_obj=form.cleaned_data["excel_file"],
                        owner=request.user,
                        company=form.cleaned_data["company"],
                        replace_existing=bool(form.cleaned_data["replace_existing"]),
                    )
                except TemplateExcelImportError as exc:
                    form.add_error(None, str(exc))
                else:
                    for warning in result.warnings:
                        self.message_user(request, warning, level=messages.WARNING)
                    self.message_user(
                        request,
                        f"Importacion completada. Templates procesados: {len(result.results)}.",
                        level=messages.SUCCESS,
                    )
                    return redirect(reverse("admin:catalog_accesstemplate_changelist"))
        else:
            form = TemplateExcelImportForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Importar templates desde Excel",
            "form": form,
        }
        return render(request, "admin/catalog/accesstemplate/import_excel.html", context)

    def get_queryset(self, request):
        """
        Evita N+1 al mostrar resumen de empresas/sucursales e items_count.
        """
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            Prefetch(
                "items",
                queryset=AccessTemplateItem.objects.select_related(
                    "selection_set__company",
                    "selection_set__branch",
                ).order_by("order", "id"),
            )
        )

    @admin.display(description="Empresas")
    def companies_summary(self, obj: AccessTemplate) -> str:
        # lista única, estable
        seen = set()
        names = []
        for it in obj.items.all():
            c = it.selection_set.company
            if c_id := getattr(c, "id", None):
                if c_id in seen:
                    continue
                seen.add(c_id)
            s = str(c)
            if s not in names:
                names.append(s)

        if not names:
            return "-"

        shown = names[:2]
        extra = f" (+{len(names) - 2})" if len(names) > 2 else ""
        return ", ".join(shown) + extra

    @admin.display(description="Sucursales")
    def branches_summary(self, obj: AccessTemplate) -> str:
        seen = set()
        names = []
        for it in obj.items.all():
            b = it.selection_set.branch
            if not b:
                continue
            if b_id := getattr(b, "id", None):
                if b_id in seen:
                    continue
                seen.add(b_id)
            s = str(b)
            if s not in names:
                names.append(s)

        if not names:
            return "-"

        shown = names[:2]
        extra = f" (+{len(names) - 2})" if len(names) > 2 else ""
        return ", ".join(shown) + extra

    @admin.display(description="Ítems")
    def items_count(self, obj: AccessTemplate) -> int:
        return obj.items.count()
    change_list_template = "admin/catalog/accesstemplate/change_list.html"
