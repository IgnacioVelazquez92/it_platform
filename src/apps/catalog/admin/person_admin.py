from __future__ import annotations

from django.contrib import admin

from apps.catalog.models import RequestPersonData


@admin.register(RequestPersonData)
class RequestPersonDataAdmin(admin.ModelAdmin):
    """
    Admin de datos de persona (snapshot).
    Se usa principalmente para autocomplete en Requests.
    """

    list_display = (
        "last_name",
        "first_name",
        "dni",
        "email",
        "job_title",
        "created_at",
    )
    search_fields = (
        "last_name",
        "first_name",
        "dni",
        "email",
    )
    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )
