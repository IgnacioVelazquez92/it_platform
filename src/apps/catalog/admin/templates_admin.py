from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import AccessTemplate


@admin.register(AccessTemplate)
class AccessTemplateAdmin(admin.ModelAdmin):
    """
    Admin de Templates de acceso.

    Rol del admin:
    - Definir perfiles reutilizables
    - Referenciar un SelectionSet ya cargado
    - Activar / desactivar templates
    """

    list_display = (
        "name",
        "department",
        "role_name",
        "company",
        "branch",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "department",
        "role_name",
        "selection_set__company",
        "selection_set__branch",
    )
    search_fields = (
        "name",
        "department",
        "role_name",
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
            "Selección de permisos",
            {
                "fields": ("selection_set",),
                "description": (
                    "Referencia a una selección completa. "
                    "Este SelectionSet se clona al crear una nueva solicitud."
                ),
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

    autocomplete_fields = ("selection_set",)

    def company(self, obj):
        return obj.selection_set.company

    def branch(self, obj):
        return obj.selection_set.branch

    company.short_description = "Empresa"
    branch.short_description = "Sucursal"
