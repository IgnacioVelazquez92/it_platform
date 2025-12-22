# IT Platform — Resumen estructural (prompt vivo)

## Árbol del proyecto

```text
src/
├─ manage.py
├─ config/
│  ├─ urls.py
│  ├─ asgi.py
│  ├─ wsgi.py
│  └─ settings/
│     ├─ base.py
│     ├─ development.py
│     └─ production.py
├─ templates/
│  ├─ base/
│  │  ├─ base.html
│  │  ├─ _sidebar.html
│  │  ├─ _messages.html
│  │  ├─ _form_errors.html
│  │  └─ _form_field.html
│  ├─ home/
│  │  └─ dashboard.html
│  └─ registration/
│     ├─ login.html
│     └─ logged_out.html
├─ static/
│  ├─ vendor/
│  │  └─ bootstrap/
│  │     ├─ css/
│  │     └─ js/
│  └─ app/
│     ├─ css/
│     │  └─ app.css
│     └─ js/
│        └─ app.js
└─ apps/
   ├─ core/
   │  ├─ apps.py
   │  ├─ views.py
   │  ├─ urls.py
   │  ├─ models.py
   │  └─ migrations/
   └─ catalog/
      ├─ apps.py
      ├─ admin.py
      ├─ urls.py
      ├─ views.py
      ├─ admin/
      │  ├─ __init__.py
      │  ├─ modules_admin.py
      │  ├─ scoped_admin.py
      │  ├─ global_ops_admin.py
      │  ├─ rules_admin.py
      │  ├─ selections_admin.py
      │  ├─ requests_admin.py
      │  ├─ templates_admin.py
      │  └─ person_admin.py
      ├─ forms/
      │  ├─ __init__.py
      │  ├─ bootstrap_mixins.py
      │  ├─ helpers.py
      │  ├─ helpers_globals.py
      │  ├─ person.py
      │  ├─ start.py
      │  ├─ step_2_companies.py
      │  ├─ step_3_modules.py
      │  ├─ step_4_globals.py
      │  ├─ step_5_scoped.py
      │  └─ visibility.py
      ├─ models/
      │  ├─ __init__.py
      │  ├─ person.py
      │  ├─ requests.py
      │  ├─ templates.py
      │  ├─ selections.py
      │  ├─ modules.py
      │  ├─ rules.py
      │  └─ permissions/
      │     ├─ __init__.py
      │     ├─ scoped.py
      │     ├─ global_ops.py
      │     └─ assignments.py
      ├─ views/
      │  ├─ __init__.py
      │  ├─ requests.py
      │  ├─ request_list.py
      │  └─ wizard/
      │     ├─ __init__.py
      │     ├─ base.py
      │     ├─ step_0_start.py
      │     ├─ step_1_person.py
      │     ├─ step_2_companies.py
      │     ├─ step_3_modules.py
      │     ├─ step_4_globals.py
      │     ├─ step_5_scoped.py
      │     └─ step_6_review.py
      ├─ templates/
      │  └─ catalog/
      │     ├─ requests/
      │     ├─ template_pick/
      │     ├─ wizard/
      │     │  ├─ _progress.html
      │     │  ├─ step_0_start.html
      │     │  ├─ step_1_person.html
      │     │  ├─ step_2_companies.html
      │     │  ├─ step_3_modules.html
      │     │  ├─ step_4_globals.html
      │     │  ├─ step_5_scoped.html
      │     │  └─ step_6_review_document.html
      │     └─ request/
      │        └─ drafts.html
      ├─ management/
      │  ├─ __init__.py
      │  └─ commands/
      │     ├─ __init__.py
      │     ├─ import_modules_from_excel.py
      │     ├─ import_scoped_from_excel.py
      │     ├─ import_action_permissions_from_excel.py
      │     └─ bootstrap_visibility_rules.py
      └─ migrations/
```

---

## Descripciones por archivo

### apps/catalog/forms

- `bootstrap_mixins.py`  
  BootstrapFormMixin: renderizado automático de forms con clases Bootstrap.

- `helpers.py`  
  Funciones de validación y sincronización de selecciones (sync_through_rows, ensure_global_rows_exist).

- `helpers_globals.py`  
  Helpers para permisos globales y replicación entre selection_sets (replicate_globals).

- `person.py`  
  RequestPersonDataForm: datos de solicitante.

- `start.py`  
  StartForm: selección de plantilla inicial.

- `step_2_companies.py`  
  TemplateCompaniesForm: empresas y flag same_modules_for_all.

- `step_3_modules.py`  
  SelectionSetModulesForm: selección de módulos por empresa.

- `step_4_globals.py`  
  SelectionSetScopeModulesForm, SelectionSetScopedSelectionsForm: scopes globales.

- `step_5_scoped.py`  
  CompanyScopedForm, BranchScopedForm: paneles, vendedores, depósitos, cajas por empresa/sucursal. NoValidationMultipleChoiceField para validación en clean\_\*.

- `visibility.py`  
  VisibilityRulesForm: reglas de visibilidad de módulos.

### apps/catalog/models

- `person.py`  
  RequestPersonData: datos personales del solicitante.

- `requests.py`  
  AccessRequest, AccessRequestItem: solicitudes de acceso con flag same_modules_for_all.

- `templates.py`  
  SelectionTemplate, SelectionTemplateModule: plantillas reutilizables.

- `selections.py`  
  PermissionSelectionSet, SelectionSetModule, SelectionSetLevel, SelectionSetSublevel: scopes y módulos.

- `modules.py`  
  Module, ModuleAction: módulos del sistema y acciones.

- `rules.py`  
  ModuleVisibilityRule: visibilidad condicional de módulos.

- `permissions/scoped.py`  
  Company, Branch, Warehouse, CashRegister, ControlPanel, Seller: entidades de scope (empresa/sucursal/depósito/caja/panel/vendedor).

- `permissions/global_ops.py`  
  ActionPermission, MatrixPermission, PaymentMethod: permisos globales.

- `permissions/assignments.py`  
  SelectionSetControlPanel, SelectionSetSeller, SelectionSetWarehouse, SelectionSetCashRegister: asignaciones de scope a selection_set.

### apps/catalog/views

- `wizard/base.py`  
  WizardBaseView: clase base del wizard con gestión de sesión y contexto.

- `wizard/step_0_start.py`  
  WizardStep0StartView: selección de modo (desde plantilla o desde cero) y plantilla inicial.

- `wizard/step_1_person.py`  
  WizardStep1PersonView: datos personales del solicitante.

- `wizard/step_2_companies.py`  
  WizardStep2CompaniesView: empresas, sucursales y flag same_modules_for_all.

- `wizard/step_3_modules.py`  
  WizardStep3ModulesView: selección de módulos por empresa.

- `wizard/step_4_globals.py`  
  WizardStep4GlobalsView: scopes globales y permisos.

- `wizard/step_5_scoped.py`  
  WizardStep5ScopedView: paneles, vendedores, depósitos, cajas por empresa/sucursal.

- `wizard/step_6_review.py`  
  WizardStep6ReviewView: revisión, generación de documento y envío de solicitud.

- `request_list.py`  
  RequestListView: listado de solicitudes.

- `requests.py`  
  RequestDetailView, RequestSubmittedView: detalle y confirmación de solicitudes.

### apps/catalog/admin

- `person_admin.py`  
  RequestPersonDataAdmin.

- `requests_admin.py`  
  AccessRequestAdmin, AccessRequestItemAdmin.

- `templates_admin.py`  
  SelectionTemplateAdmin, SelectionTemplateModuleAdmin.

- `selections_admin.py`  
  PermissionSelectionSetAdmin, SelectionSetModuleAdmin, SelectionSetLevelAdmin, SelectionSetSublevelAdmin.

- `modules_admin.py`  
  ModuleAdmin, ModuleActionAdmin.

- `rules_admin.py`  
  ModuleVisibilityRuleAdmin.

- `scoped_admin.py`  
  CompanyAdmin, BranchAdmin, WarehouseAdmin, CashRegisterAdmin, ControlPanelAdmin, SellerAdmin.

- `global_ops_admin.py`  
  ActionPermissionAdmin, MatrixPermissionAdmin, PaymentMethodAdmin, SelectionSetControlPanelAdmin, SelectionSetSellerAdmin, SelectionSetWarehouseAdmin, SelectionSetCashRegisterAdmin.

### apps/catalog/management/commands

- `import_modules_from_excel.py`  
  Importa módulos desde Excel.

- `import_scoped_from_excel.py`  
  Importa entidades de scope (companies, branches, warehouses, cash registers, control panels, sellers) desde Excel.

- `import_action_permissions_from_excel.py`  
  Importa permisos de acciones desde Excel.

- `bootstrap_visibility_rules.py`  
  Crea reglas de visibilidad predeterminadas.

### templates/catalog/wizard

- `_progress.html`  
  Barra de progreso del wizard.

- `step_0_start.html`  
  Selección de modo y plantilla inicial.

- `step_1_person.html`  
  Carga de datos personales.

- `step_2_companies.html`  
  Selección de empresas, sucursales e indicador de módulos compartidos.

- `step_3_modules.html`  
  Selección de módulos por empresa.

- `step_4_globals.html`  
  Permisos globales (acciones, matriz, medios de pago).

- `step_5_scoped.html`  
  Paneles, vendedores, depósitos, cajas por empresa/sucursal (accordion).

- `step_6_review_document.html`  
  Revisión final y generación de documento de solicitud.

### apps/core

- `views.py`  
  HomeDashboardView, LogoutConfirmView.

- `urls.py`  
  Rutas base (home, login, logout).

- `models.py`  
  Modelos transversales (si aplican).
