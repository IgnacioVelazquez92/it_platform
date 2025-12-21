from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.catalog.models.requests import AccessRequest


class RequestListView(LoginRequiredMixin, ListView):
    model = AccessRequest
    template_name = "catalog/request/list.html"
    context_object_name = "requests"
    paginate_by = 20

    def get_queryset(self):
        # Simple y robusto: lo último arriba
        return (
            AccessRequest.objects
            .select_related("person_data")
            .order_by("-created_at")
        )
