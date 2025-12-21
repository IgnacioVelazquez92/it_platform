from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import (
    ErpModule,
    ErpModuleLevel,
    ErpModuleSubLevel,
)


# -----------------------------
# Inlines (jerarquía visual)
# -----------------------------

class ErpModuleLevelInline(admin.TabularInline):
    model = ErpModuleLevel
    extra = 0
    fields = ("name", "is_active")
    ordering = ("name",)
    show_change_link = True


class ErpModuleSubLevelInline(admin.TabularInline):
    model = ErpModuleSubLevel
    extra = 0
    fields = ("name", "is_active")
    ordering = ("name",)
    show_change_link = True


# -----------------------------
# Admin principal
# -----------------------------

@admin.register(ErpModule)
class ErpModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)

    inlines = (ErpModuleLevelInline,)


@admin.register(ErpModuleLevel)
class ErpModuleLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "module", "is_active", "created_at")
    list_filter = ("is_active", "module")
    search_fields = ("name", "module__name")
    ordering = ("module__name", "name")

    inlines = (ErpModuleSubLevelInline,)


@admin.register(ErpModuleSubLevel)
class ErpModuleSubLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "is_active", "created_at")
    list_filter = ("is_active", "level__module")
    search_fields = ("name", "level__name", "level__module__name")
    ordering = ("level__module__name", "level__name", "name")
