from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import AccessRequest, AccessRequestItem


class AccessRequestItemInline(admin.TabularInline):
    model = AccessRequestItem
    extra = 0
    autocomplete_fields = ("selection_set",)
    fields = ("order", "selection_set", "notes", "created_at")
    readonly_fields = ("created_at",)


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    """
    Admin de solicitudes.

    Rol del admin:
    - Visualizar solicitudes
    - Cambiar estado
    - Auditar datos cargados
    """

    list_display = (
        "id",
        "kind",
        "status",
        "person_data",
        "companies",
        "branches",
        "created_at",
    )

    list_filter = (
        "kind",
        "status",
        # Filtro legado (si existe selection_set)
        "selection_set__company",
        "selection_set__branch",
    )

    search_fields = (
        "person_data__first_name",
        "person_data__last_name",
        "person_data__dni",
        "person_data__email",
    )

    ordering = ("-created_at",)
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Solicitud", {"fields": ("kind", "status")}),
        ("Persona", {"fields": ("person_data",)}),
        (
            "Selección de permisos (legacy)",
            {
                "fields": ("selection_set",),
                "description": "Compatibilidad: antes la solicitud tenía un único selection_set.",
            },
        ),
        ("Notas", {"fields": ("notes",)}),
        ("Trazabilidad", {"fields": ("created_at", "updated_at")}),
    )

    autocomplete_fields = ("person_data", "selection_set")
    inlines = (AccessRequestItemInline,)

    @admin.display(description="Empresas")
    def companies(self, obj: AccessRequest) -> str:
        if obj.selection_set_id:
            return str(obj.selection_set.company)

        # multiempresa
        qs = obj.items.select_related("selection_set__company").all()
        if not qs.exists():
            return "-"
        names = []
        for it in qs:
            names.append(str(it.selection_set.company))
        # compactamos
        unique = list(dict.fromkeys(names))
        return ", ".join(unique[:3]) + (" …" if len(unique) > 3 else "")

    @admin.display(description="Sucursales")
    def branches(self, obj: AccessRequest) -> str:
        if obj.selection_set_id:
            return str(obj.selection_set.branch)

        qs = obj.items.select_related(
            "selection_set__branch", "selection_set__company").all()
        if not qs.exists():
            return "-"
        names = []
        for it in qs:
            names.append(str(it.selection_set.branch))
        unique = list(dict.fromkeys(names))
        return ", ".join(unique[:3]) + (" …" if len(unique) > 3 else "")
