from django.urls import path

from .views.requests import DraftRequestListView, TemplateListView
from .views.wizard import (
    WizardStep1PersonView,
    WizardStep2TemplateCompaniesView,
    WizardStep3BranchesView,
    WizardStep4ScopedView,
    WizardStep5GlobalView,
)

app_name = "catalog"

urlpatterns = [
    # Listados
    path("requests/drafts/", DraftRequestListView.as_view(), name="drafts"),
    path("templates/", TemplateListView.as_view(), name="templates"),

    # Wizard (multi-empresa)
    path("requests/new/", WizardStep1PersonView.as_view(), name="request_new"),
    path("requests/<int:request_id>/step/1/",
         WizardStep1PersonView.as_view(), name="w_step_1"),
    path("requests/<int:request_id>/step/2/",
         WizardStep2TemplateCompaniesView.as_view(), name="w_step_2"),
    path("requests/<int:request_id>/step/3/",
         WizardStep3BranchesView.as_view(), name="w_step_3"),
    path("requests/<int:request_id>/step/4/",
         WizardStep4ScopedView.as_view(), name="w_step_4"),
    path("requests/<int:request_id>/step/5/",
         WizardStep5GlobalView.as_view(), name="w_step_5"),
]
