# src/apps/catalog/views/requests.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, TemplateView

from apps.catalog.models.requests import AccessRequest


class RequestDetailView(LoginRequiredMixin, DetailView):
    model = AccessRequest
    template_name = "catalog/request/detail.html"
    context_object_name = "request_obj"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("person_data")
            .prefetch_related(
                "items__selection_set__company",
                "items__selection_set__branch",
                "items__selection_set__modules",
                "items__selection_set__selected_modules__module",
                "items__selection_set__warehouses__warehouse",
                "items__selection_set__cash_registers__cash_register",
                "items__selection_set__control_panels__control_panel",
                "items__selection_set__sellers__seller",
                "items__selection_set__action_values__action_permission",
                "items__selection_set__matrix_permissions__permission",
                "items__selection_set__payment_methods__payment_method",
            )
        )


class RequestSubmittedView(LoginRequiredMixin, TemplateView):
    template_name = "catalog/request/submitted.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = (
            AccessRequest.objects
            .select_related("person_data")
            .get(pk=self.kwargs["pk"])
        )
        ctx["request_obj"] = req
        return ctx
