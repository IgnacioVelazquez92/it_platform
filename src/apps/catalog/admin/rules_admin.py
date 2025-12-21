from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import (
    PermissionBlock,
    PermissionVisibilityRule,
    PermissionVisibilityTrigger,
    PermissionVisibilityRuleBlock,
)

# -------------------------------------------------
# PermissionBlock
# -------------------------------------------------


@admin.register(PermissionBlock)
class PermissionBlockAdmin(admin.ModelAdmin):
    """
    Bloques de UI que luego las reglas muestran u ocultan.
    """
    list_display = (
        "code",
        "name",
        "kind",
        "scoped_entity",
        "global_entity",
        "action_group",
        "is_active",
        "order",
    )
    list_filter = (
        "kind",
        "is_active",
        "scoped_entity",
        "global_entity",
    )
    search_fields = ("code", "name", "action_group")
    ordering = ("order", "name")

    list_editable = ("is_active", "order")

    fieldsets = (
        (
            "Identificación",
            {
                "fields": ("code", "name", "kind"),
            },
        ),
        (
            "Configuración SCOPED",
            {
                "fields": ("scoped_entity",),
                "description": "Solo aplica si kind = SCOPED.",
            },
        ),
        (
            "Configuración GLOBAL",
            {
                "fields": ("global_entity", "action_group"),
                "description": "Solo aplica si kind = GLOBAL. "
                "action_group solo para GLOBAL/ACTION.",
            },
        ),
        (
            "Estado",
            {
                "fields": ("is_active", "order"),
            },
        ),
    )


# -------------------------------------------------
# Inlines para reglas
# -------------------------------------------------

class PermissionVisibilityTriggerInline(admin.TabularInline):
    """
    Triggers: cuándo se activa la regla.
    """
    model = PermissionVisibilityTrigger
    extra = 0
    fields = ("module", "level", "sublevel")
    autocomplete_fields = ("module", "level", "sublevel")
    verbose_name = "Trigger"
    verbose_name_plural = "Triggers"


class PermissionVisibilityRuleBlockInline(admin.TabularInline):
    """
    Bloques que la regla muestra.
    """
    model = PermissionVisibilityRuleBlock
    extra = 0
    fields = ("block", "mode", "order")
    autocomplete_fields = ("block",)
    ordering = ("order",)
    verbose_name = "Bloque"
    verbose_name_plural = "Bloques mostrados"


# -------------------------------------------------
# PermissionVisibilityRule
# -------------------------------------------------

@admin.register(PermissionVisibilityRule)
class PermissionVisibilityRuleAdmin(admin.ModelAdmin):
    """
    Regla principal de visibilidad.
    """
    list_display = (
        "name",
        "is_active",
        "priority",
        "match_mode",
        "created_at",
    )
    list_filter = ("is_active", "match_mode")
    search_fields = ("name", "notes")
    ordering = ("-priority", "name")

    list_editable = ("is_active", "priority")

    fieldsets = (
        (
            "Regla",
            {
                "fields": ("name", "is_active"),
            },
        ),
        (
            "Comportamiento",
            {
                "fields": ("priority", "match_mode"),
                "description": (
                    "Prioridad más alta se evalúa primero. "
                    "Si no hay triggers, la regla siempre matchea."
                ),
            },
        ),
        (
            "Notas",
            {
                "fields": ("notes",),
            },
        ),
    )

    inlines = (
        PermissionVisibilityTriggerInline,
        PermissionVisibilityRuleBlockInline,
    )


# -------------------------------------------------
# Opcional: vista directa de triggers (debug)
# -------------------------------------------------

@admin.register(PermissionVisibilityTrigger)
class PermissionVisibilityTriggerAdmin(admin.ModelAdmin):
    """
    Vista directa para debugging.
    Normalmente se gestionan desde la regla.
    """
    list_display = ("rule", "module", "level", "sublevel")
    list_filter = ("rule",)
    search_fields = (
        "rule__name",
        "module__name",
        "level__name",
        "sublevel__name",
    )


@admin.register(PermissionVisibilityRuleBlock)
class PermissionVisibilityRuleBlockAdmin(admin.ModelAdmin):
    """
    Vista directa para debugging.
    """
    list_display = ("rule", "block", "mode", "order")
    list_filter = ("rule", "block")
    ordering = ("rule__priority", "order")
