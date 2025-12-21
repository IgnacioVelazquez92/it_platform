from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import (
    Company,
    Branch,
    Warehouse,
    CashRegister,
    ControlPanel,
    Seller,
)

# -------------------------------------------------
# Inlines (jerarquía visual clara)
# -------------------------------------------------


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ("name", "is_active")
    ordering = ("name",)
    show_change_link = True


class WarehouseInline(admin.TabularInline):
    model = Warehouse
    extra = 0
    fields = ("name", "is_active")
    ordering = ("name",)
    show_change_link = True


class CashRegisterInline(admin.TabularInline):
    model = CashRegister
    extra = 0
    fields = ("name", "is_active")
    ordering = ("name",)
    show_change_link = True


class ControlPanelInline(admin.TabularInline):
    model = ControlPanel
    extra = 0
    fields = ("name", "is_active")
    ordering = ("name",)
    show_change_link = True


class SellerInline(admin.TabularInline):
    model = Seller
    extra = 0
    fields = ("name", "is_active")
    ordering = ("name",)
    show_change_link = True


# -------------------------------------------------
# Admins principales
# -------------------------------------------------

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)

    inlines = (
        BranchInline,
        ControlPanelInline,
        SellerInline,
    )


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_active", "created_at")
    list_filter = ("is_active", "company")
    search_fields = ("name", "company__name")
    ordering = ("company__name", "name")

    inlines = (
        WarehouseInline,
        CashRegisterInline,
    )


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "is_active", "created_at")
    list_filter = ("is_active", "branch__company")
    search_fields = ("name", "branch__name", "branch__company__name")
    ordering = ("branch__company__name", "branch__name", "name")


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "is_active", "created_at")
    list_filter = ("is_active", "branch__company")
    search_fields = ("name", "branch__name", "branch__company__name")
    ordering = ("branch__company__name", "branch__name", "name")


@admin.register(ControlPanel)
class ControlPanelAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_active", "created_at")
    list_filter = ("is_active", "company")
    search_fields = ("name", "company__name")
    ordering = ("company__name", "name")


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_active", "created_at")
    list_filter = ("is_active", "company")
    search_fields = ("name", "company__name")
    ordering = ("company__name", "name")
