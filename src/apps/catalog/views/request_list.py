from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.catalog.models.requests import AccessRequest, RequestStatus


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

        user = self.request.user

        # Non-superusers only see their own requests.
        # Superusers see all users' requests but NOT drafts (to avoid huge lists).
        if user.is_superuser:
            qs = qs.exclude(status=RequestStatus.DRAFT)
        else:
            qs = qs.filter(owner=user)

        # Apply status filter if provided. Superusers cannot filter drafts.
        if status:
            if user.is_superuser and status == RequestStatus.DRAFT:
                qs = qs.none()
            else:
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
