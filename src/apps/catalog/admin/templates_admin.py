from __future__ import annotations

from django.contrib import admin
from django.db.models import Prefetch

from apps.catalog.models import AccessTemplate, AccessTemplateItem


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
