from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import (
    PermissionSelectionSet,
    SelectionSetModule,
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
    SelectionSetActionValue,
    SelectionSetPaymentMethod,
)

# -------------------------------------------------
# Inlines
# -------------------------------------------------


class SelectionSetModuleInline(admin.TabularInline):
    model = SelectionSetModule
    extra = 0
    autocomplete_fields = ("module",)


class SelectionSetWarehouseInline(admin.TabularInline):
    model = SelectionSetWarehouse
    extra = 0
    autocomplete_fields = ("warehouse",)


class SelectionSetCashRegisterInline(admin.TabularInline):
    model = SelectionSetCashRegister
    extra = 0
    autocomplete_fields = ("cash_register",)


class SelectionSetControlPanelInline(admin.TabularInline):
    model = SelectionSetControlPanel
    extra = 0
    autocomplete_fields = ("control_panel",)


class SelectionSetSellerInline(admin.TabularInline):
    model = SelectionSetSeller
    extra = 0
    autocomplete_fields = ("seller",)


class SelectionSetActionValueInline(admin.TabularInline):
    model = SelectionSetActionValue
    extra = 0
    autocomplete_fields = ("action_permission",)
    fields = (
        "action_permission",
        "value_bool",
        "value_int",
        "value_decimal",
        "value_text",
        "is_active",
    )


class SelectionSetPaymentMethodInline(admin.TabularInline):
    model = SelectionSetPaymentMethod
    extra = 0
    autocomplete_fields = ("payment_method",)
    fields = ("payment_method", "enabled", "is_active")


# -------------------------------------------------
# PermissionSelectionSet
# -------------------------------------------------

@admin.register(PermissionSelectionSet)
class PermissionSelectionSetAdmin(admin.ModelAdmin):
    """
    Payload completo de selección.
    Este admin permite cargar TODO lo que el usuario eligió.
    """

    list_display = ("company", "branch", "created_at")
    list_filter = ("company", "branch")
    search_fields = ("company__name", "branch__name")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Scope",
            {
                "fields": ("company", "branch"),
                "description": "Empresa y sucursal son obligatorias.",
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
        SelectionSetModuleInline,
        SelectionSetWarehouseInline,
        SelectionSetCashRegisterInline,
        SelectionSetControlPanelInline,
        SelectionSetSellerInline,
        SelectionSetActionValueInline,
        SelectionSetPaymentMethodInline,
    )
