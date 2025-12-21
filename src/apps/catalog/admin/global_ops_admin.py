from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import (
    ActionPermission,
    MatrixPermission,
    PaymentMethodPermission,
)

# -------------------------------------------------
# ActionPermission
# -------------------------------------------------


@admin.register(ActionPermission)
class ActionPermissionAdmin(admin.ModelAdmin):
    """
    Acciones globales con tipo de valor.
    Ej: grupo 'Articulos stock y logistica'
    """
    list_display = (
        "group",
        "action",
        "value_type",
        "is_active",
        "created_at",
    )
    list_filter = ("group", "value_type", "is_active")
    search_fields = ("group", "action")
    ordering = ("group", "action")

    list_editable = ("is_active",)


# -------------------------------------------------
# MatrixPermission (modelo simplificado)
# -------------------------------------------------

@admin.register(MatrixPermission)
class MatrixPermissionAdmin(admin.ModelAdmin):
    """
    Permisos funcionales con columnas booleanas.
    Representa una fila completa de la matriz.
    """

    list_display = (
        "name",
        "can_create",
        "can_update",
        "can_authorize",
        "can_close",
        "can_cancel",
        "can_update_validity",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)

    list_editable = (
        "can_create",
        "can_update",
        "can_authorize",
        "can_close",
        "can_cancel",
        "can_update_validity",
        "is_active",
    )

    fieldsets = (
        (
            "Permiso",
            {
                "fields": ("name", "is_active"),
            },
        ),
        (
            "Acciones habilitadas",
            {
                "fields": (
                    "can_create",
                    "can_update",
                    "can_authorize",
                    "can_close",
                    "can_cancel",
                    "can_update_validity",
                ),
            },
        ),
    )


# -------------------------------------------------
# PaymentMethodPermission
# -------------------------------------------------

@admin.register(PaymentMethodPermission)
class PaymentMethodPermissionAdmin(admin.ModelAdmin):
    """
    Medios de pago habilitables.
    """
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)

    list_editable = ("is_active",)
