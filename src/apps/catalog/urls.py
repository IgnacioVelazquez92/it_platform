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
from apps.catalog.views.templates import (
    TemplateListView,
    TemplateDetailView,
    TemplateEditView,
    TemplateDeleteView,
)
from apps.catalog.views.template_wizard.step_0_start import TemplateWizardStep0StartView
from apps.catalog.views.template_wizard.step_2_modules import TemplateWizardStep2ModulesView
from apps.catalog.views.template_wizard.step_3_globals import TemplateWizardStep3GlobalsView
from apps.catalog.views.template_wizard.step_5_review import TemplateWizardStep5ReviewView


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

    # ── Templates / Modelos de acceso ──────────────────────────────────────────
    path("templates/", TemplateListView.as_view(), name="template_list"),
    path("templates/<int:pk>/", TemplateDetailView.as_view(), name="template_detail"),
    path("templates/<int:pk>/edit/", TemplateEditView.as_view(), name="template_edit"),
    path("templates/<int:pk>/delete/", TemplateDeleteView.as_view(), name="template_delete"),

    # ── Template wizard (creación directa) ─────────────────────────────────────
    path("templates/new/start/", TemplateWizardStep0StartView.as_view(), name="template_wizard_start"),
    path("templates/new/modules/", TemplateWizardStep2ModulesView.as_view(), name="template_wizard_modules"),
    path("templates/new/globals/", TemplateWizardStep3GlobalsView.as_view(), name="template_wizard_globals"),
    path("templates/new/review/", TemplateWizardStep5ReviewView.as_view(), name="template_wizard_review"),
]
