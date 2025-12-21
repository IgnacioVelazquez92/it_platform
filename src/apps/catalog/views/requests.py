from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.catalog.models.requests import AccessRequest, RequestStatus
from apps.catalog.models.templates import AccessTemplate


class DraftRequestListView(LoginRequiredMixin, ListView):
    template_name = "catalog/requests/drafts.html"
    context_object_name = "requests"
    paginate_by = 25

    def get_queryset(self):
        return (
            AccessRequest.objects
            .select_related("person_data")
            .prefetch_related("items__selection_set__company", "items__selection_set__branch")
            .filter(status=RequestStatus.DRAFT)
            .order_by("-created_at")
        )


class TemplateListView(LoginRequiredMixin, ListView):
    template_name = "catalog/requests/templates.html"
    context_object_name = "templates"
    paginate_by = 25

    def get_queryset(self):
        return AccessTemplate.objects.select_related("selection_set__company", "selection_set__branch").order_by("name")
