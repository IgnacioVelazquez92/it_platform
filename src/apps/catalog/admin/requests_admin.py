from __future__ import annotations

from django.contrib import admin
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from apps.catalog.models import AccessRequest, AccessRequestItem


class AccessRequestItemInline(admin.TabularInline):
    model = AccessRequestItem
    extra = 0
    autocomplete_fields = ("selection_set",)
    fields = (
        "order",
        "selection_set_link",
        "company",
        "branch",
        "notes",
        "created_at",
    )
    readonly_fields = ("selection_set_link", "company", "branch", "created_at")
    ordering = ("order", "id")
    show_change_link = True

    @admin.display(description="Seleccion")
    def selection_set_link(self, obj: AccessRequestItem) -> str:
        if not obj.selection_set_id:
            return "-"

        opts = obj.selection_set._meta
        url = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.selection_set_id])
        return format_html('<a href="{}">#{}</a>', url, obj.selection_set_id)

    @admin.display(description="Empresa")
    def company(self, obj: AccessRequestItem) -> str:
        if not obj.selection_set_id:
            return "-"
        return str(obj.selection_set.company)

    @admin.display(description="Sucursal")
    def branch(self, obj: AccessRequestItem) -> str:
        if not obj.selection_set_id or not obj.selection_set.branch:
            return "-"
        return str(obj.selection_set.branch)


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
        "owner_display",
        "person_data",
        "companies",
        "branches",
        "items_count",
        "created_at",
    )

    list_filter = (
        "kind",
        "status",
        "owner",
        # Filtro legado (si existe selection_set)
        "selection_set__company",
        "selection_set__branch",
    )

    search_fields = (
        "owner__username",
        "owner__email",
        "owner__first_name",
        "owner__last_name",
        "person_data__first_name",
        "person_data__last_name",
        "person_data__dni",
        "person_data__email",
    )

    ordering = ("-created_at",)
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at", "items_overview")
    list_select_related = ("person_data", "owner")

    fieldsets = (
        ("Solicitud", {"fields": ("kind", "status", "owner")}),
        ("Persona", {"fields": ("person_data",)}),
        (
            "Resumen de carga",
            {
                "fields": ("items_overview",),
            },
        ),
        (
            "Seleccion de permisos (legacy)",
            {
                "fields": ("selection_set",),
                "description": "Compatibilidad: antes la solicitud tenia un unico selection_set.",
            },
        ),
        ("Notas", {"fields": ("notes",)}),
        ("Trazabilidad", {"fields": ("created_at", "updated_at")}),
    )

    autocomplete_fields = ("person_data", "selection_set")
    inlines = (AccessRequestItemInline,)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:
            readonly.append("owner")
        return tuple(readonly)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "person_data",
            "owner",
            "selection_set__company",
            "selection_set__branch",
        ).prefetch_related(
            Prefetch(
                "items",
                queryset=AccessRequestItem.objects.select_related(
                    "selection_set__company",
                    "selection_set__branch",
                ).order_by("order", "id"),
            )
        )

    @admin.display(description="Cargado por")
    def owner_display(self, obj: AccessRequest) -> str:
        if not obj.owner_id:
            return "-"

        full_name = obj.owner.get_full_name().strip()
        if full_name:
            return full_name
        return getattr(obj.owner, "username", None) or str(obj.owner)

    @admin.display(description="Empresas")
    def companies(self, obj: AccessRequest) -> str:
        if obj.selection_set_id:
            return str(obj.selection_set.company)

        # multiempresa
        qs = obj.items.select_related("selection_set__company").all()
        if not qs.exists():
            return "-"

        names = [str(it.selection_set.company) for it in qs]
        unique = list(dict.fromkeys(names))
        return ", ".join(unique[:3]) + (" ..." if len(unique) > 3 else "")

    @admin.display(description="Sucursales")
    def branches(self, obj: AccessRequest) -> str:
        if obj.selection_set_id:
            return str(obj.selection_set.branch)

        qs = obj.items.select_related("selection_set__branch", "selection_set__company").all()
        if not qs.exists():
            return "-"

        names = [str(it.selection_set.branch) for it in qs if it.selection_set.branch]
        unique = list(dict.fromkeys(names))
        return ", ".join(unique[:3]) + (" ..." if len(unique) > 3 else "") if unique else "-"

    @admin.display(description="Items")
    def items_count(self, obj: AccessRequest) -> int:
        if obj.selection_set_id:
            return 1
        return obj.items.count()

    @admin.display(description="Detalle completo")
    def items_overview(self, obj: AccessRequest) -> str:
        if obj.selection_set_id:
            s = obj.selection_set
            return format_html(
                "Legacy: {} / {} (selection_set #{})",
                s.company,
                s.branch or "-",
                s.id,
            )

        items = list(obj.items.all())
        if not items:
            return "-"

        rows = []
        for it in items:
            s = it.selection_set
            opts = s._meta
            url = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[s.id])
            notes = format_html(" ({})", it.notes) if it.notes else ""
            rows.append((it.order, s.company, s.branch or "-", url, s.id, notes))

        return format_html(
            "<ol>{}</ol>",
            format_html_join(
                "",
                "<li><strong>{}</strong>. {} / {} - <a href=\"{}\">selection_set #{}</a>{}</li>",
                rows,
            ),
        )
