from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.catalog.models.requests import AccessRequest, RequestStatus


MODEL_USER_NOTE_PREFIX = "Usuario modelo ERP (texto libre):"
TEMPLATE_NOTE_PREFIX = "Templates usados:"


def extract_model_user_reference(raw_note: str) -> str:
    note = (raw_note or "").strip()
    if not note:
        return ""
    if note.startswith(MODEL_USER_NOTE_PREFIX):
        return note[len(MODEL_USER_NOTE_PREFIX):].strip()
    return ""


def extract_template_source(raw_notes: str) -> str:
    for line in (raw_notes or "").splitlines():
        note = line.strip()
        if note.startswith(TEMPLATE_NOTE_PREFIX):
            return note[len(TEMPLATE_NOTE_PREFIX):].strip()
    return ""


class RequestListView(LoginRequiredMixin, ListView):
    model = AccessRequest
    template_name = "catalog/request/list.html"
    context_object_name = "requests"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            AccessRequest.objects
            .select_related("person_data")
            .prefetch_related("items__selection_set__company")
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

        for req in ctx["requests"]:
            req.template_source = extract_template_source(req.notes)
            copy_summary: list[str] = []
            seen: set[str] = set()
            for item in req.items.all():
                model_ref = extract_model_user_reference(item.selection_set.notes)
                if not model_ref:
                    continue
                label = f"{item.selection_set.company.name}: {model_ref}"
                if label in seen:
                    continue
                seen.add(label)
                copy_summary.append(label)
            req.copy_summary = copy_summary
            req.is_copy_request = bool(copy_summary)

        return ctx
