from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.catalog.models.requests import AccessRequest


class RequestListView(LoginRequiredMixin, ListView):
    model = AccessRequest
    template_name = "catalog/request/list.html"
    context_object_name = "requests"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            AccessRequest.objects
            .select_related("person_data")
            .order_by("-created_at")
        )

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()

        if status:
            qs = qs.filter(status=status)

        if q:
            qs = qs.filter(
                Q(id__icontains=q) |
                Q(person_data__first_name__icontains=q) |
                Q(person_data__last_name__icontains=q) |
                Q(person_data__dni__icontains=q) |
                Q(person_data__email__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["status"] = (self.request.GET.get("status") or "").strip()
        return ctx
