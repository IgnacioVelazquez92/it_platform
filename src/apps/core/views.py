from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.utils.safestring import mark_safe
import json
from apps.catalog.models.requests import AccessRequest, RequestStatus
from apps.catalog.models.permissions.scoped import Company


class HomeDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "home/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_staff:
            # Admin: datos agregados de todas las solicitudes
            context.update(self._get_admin_stats())
        else:
            # No-admin: solo sus propias solicitudes recientes
            context.update(self._get_user_stats(user))

        return context

    def _get_admin_stats(self):
        """Estadísticas para staff/admin."""
        # Total y por estado (excluyendo DRAFT)
        active_requests = AccessRequest.objects.exclude(status=RequestStatus.DRAFT)
        stats = {
            "total_requests": active_requests.count(),
            "submitted_count": active_requests.filter(status=RequestStatus.SUBMITTED).count(),
            "approved_count": active_requests.filter(status=RequestStatus.APPROVED).count(),
            "rejected_count": active_requests.filter(status=RequestStatus.REJECTED).count(),
        }

        # Gráfico: distribución por estado
        status_data = (
            active_requests
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        status_labels = []
        status_counts = []
        for s in status_data:
            status_labels.append(dict(RequestStatus.choices).get(s["status"], s["status"]))
            status_counts.append(s["count"])
        
        stats["status_chart"] = {
            "labels": mark_safe(json.dumps(status_labels)),
            "data": mark_safe(json.dumps(status_counts)),
        }

        # Gráfico: top 10 empresas con más solicitudes
        company_data = (
            active_requests
            .prefetch_related("items__selection_set__company")
            .values("items__selection_set__company__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        company_labels = []
        company_counts = []
        for c in company_data:
            if c["items__selection_set__company__name"]:
                company_labels.append(c["items__selection_set__company__name"])
                company_counts.append(c["count"])
        
        stats["company_chart"] = {
            "labels": mark_safe(json.dumps(company_labels)),
            "data": mark_safe(json.dumps(company_counts)),
        }

        # Últimas 5 solicitudes enviadas
        stats["recent_requests"] = (
            active_requests
            .select_related("person_data", "owner")
            .order_by("-created_at")[:5]
        )

        return stats

    def _get_user_stats(self, user):
        """Estadísticas para usuarios no-admin."""
        user_requests = AccessRequest.objects.filter(owner=user).exclude(status=RequestStatus.DRAFT)
        return {
            "user_requests": user_requests.select_related("person_data").order_by("-created_at")[:10],
            "user_total": user_requests.count(),
            "user_submitted": user_requests.filter(status=RequestStatus.SUBMITTED).count(),
            "user_approved": user_requests.filter(status=RequestStatus.APPROVED).count(),
            "user_rejected": user_requests.filter(status=RequestStatus.REJECTED).count(),
        }
