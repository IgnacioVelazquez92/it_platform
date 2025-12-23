from django.urls import path


from apps.catalog.views.wizard.step_0_start import WizardStep0StartView
from apps.catalog.views.wizard.step_1_person import WizardStep1PersonView
from apps.catalog.views.wizard.step_2_companies import WizardStep2CompaniesView
from apps.catalog.views.wizard.step_3_modules import WizardStep3ModulesView
from apps.catalog.views.wizard.step_4_globals import WizardStep4GlobalsView
from apps.catalog.views.wizard.step_5_scoped import WizardStep5ScopedView
from apps.catalog.views.wizard.step_6_review import WizardStep6ReviewView
from apps.catalog.views.requests import RequestSubmittedView, RequestDetailView
from apps.catalog.views.request_list import RequestListView
from apps.catalog.views.request_templates import RequestMakeTemplateView


app_name = "catalog"

urlpatterns = [
    path("wizard/start/", WizardStep0StartView.as_view(),
         name="wizard_step_0_start"),
    path("wizard/person/", WizardStep1PersonView.as_view(),
         name="wizard_step_1_person"),
    path("wizard/companies/", WizardStep2CompaniesView.as_view(),
         name="wizard_step_2_companies"),

    path("wizard/modules/", WizardStep3ModulesView.as_view(),
         name="wizard_step_3_modules"),
    path("wizard/globals/", WizardStep4GlobalsView.as_view(),
         name="wizard_step_4_globals"),
    path("wizard/scoped/", WizardStep5ScopedView.as_view(),
         name="wizard_step_5_scoped"),
    path("wizard/review/", WizardStep6ReviewView.as_view(),
         name="wizard_step_6_review"),
    # confirmación de envío
    path("requests/<int:pk>/submitted/",
         RequestSubmittedView.as_view(), name="wizard_submitted"),

    # detalle (para ver/validar/compartir)
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="request_detail"),
    path("requests/", RequestListView.as_view(), name="request_list"),

    path(
        "requests/<int:request_id>/make-template/",
        RequestMakeTemplateView.as_view(),
        name="request_make_template",
    ),
]
