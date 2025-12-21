from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "home/dashboard.html"
