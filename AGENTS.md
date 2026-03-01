git pull origin main# AGENTS.md — Contexto del proyecto IT Platform

> Fecha de última actualización: 26 de febrero de 2026 (revisión 3).
> Este archivo describe el estado **actual** del proyecto y sirve de referencia para agentes de IA y nuevos colaboradores.
> Regla de ORO: luego de terminar de hacer cualquier cambio venir actualizar el contexto, el contexto es los archivos con sus respectivas funciones  y clases y parametros de entrada y salida para nunca fllar en los imports, una breve descripción de que hace cada función y nada más.

---

## 1. Propósito

Plataforma interna de IT para gestionar **solicitudes de acceso al ERP** (Pharmacenter).
Un solicitante completa un wizard de 7 pasos que captura persona, empresas, módulos ERP seleccionados y permisos asociados (scoped y globales). Al enviar, se notifica al equipo IT por email.

Los **templates de acceso** (`AccessTemplate`) representan perfiles reutilizables (ej. "Cajero — Sucursal estándar"): encapsulan **módulos ERP, permisos globales (acciones, matriz CRUD, medios de pago)** previamente configurados y permiten pre-rellenar nuevas solicitudes. Los datos vinculados a empresa/sucursal (paneles, vendedores, depósitos, cajas) **no** forman parte de un template — el usuario los completa al crear cada solicitud.

---

## 2. Stack técnico

| Item | Detalle |
|---|---|
| Framework | Django 4.x |
| DB (dev) | SQLite (`src/db.sqlite3`) |
| DB (prod) | Configurable via env |
| Frontend | Bootstrap 5, Bootstrap Icons, sin SPA (Django templates puro) |
| Email (dev) | Console backend (cuando `USE_GMAIL_OAUTH=False`) |
| Email (prod) | Google Gmail OAuth2 (`google-auth`, `google-api-python-client`) |
| Auth | Django built-in (`AUTH_USER_MODEL` = `auth.User`) |
| Apps | `apps.core`, `apps.catalog` |
| Sin (a propósito) | DRF, Celery, django-crispy-forms, django-wizard |

---

## 3. Entidades del dominio

### 3.1 Árbol ERP (catálogo importado desde Excel)

```
ErpModule
  └── ErpModuleLevel
        └── ErpModuleSubLevel
```

Todos tienen `is_active`. Se importan con management commands (`bootstrap_catalog`).

### 3.2 Catálogos scoped (ligados a Empresa/Sucursal)

| Modelo | Scope |
|---|---|
| `Company` | Raíz |
| `Branch` | → Company |
| `Warehouse` | → Branch |
| `CashRegister` | → Branch |
| `ControlPanel` | → Company |
| `Seller` | → Company |

### 3.3 Catálogos globales (independientes de Empresa)

| Modelo | Descripción |
|---|---|
| `ActionPermission` | Permiso con valor tipado (Bool/Int/Decimal/Percent/Text). Tiene `group` para agrupar en UI. |
| `MatrixPermission` | Fila de permisos CRUD: can_create/update/authorize/close/cancel/update_validity |
| `PaymentMethodPermission` | Método de pago que se puede habilitar/deshabilitar |

### 3.4 PermissionSelectionSet — contenedor central

`PermissionSelectionSet` registra todo lo que el usuario eligió para un par `(Company, Branch)`:

- `SelectionSetModule` — qué `ErpModule`s están incluidos
- `SelectionSetLevel` / `SelectionSetSubLevel` — niveles/subniveles seleccionados
- `SelectionSetWarehouse`, `SelectionSetCashRegister`, `SelectionSetControlPanel`, `SelectionSetSeller` — asignaciones scoped
- `SelectionSetActionValue` — valor tipado por `ActionPermission`
- `SelectionSetMatrixPermission` — flags CRUD por `MatrixPermission`
- `SelectionSetPaymentMethod` — habilitación por `PaymentMethodPermission`

### 3.5 Solicitudes

| Modelo | Descripción |
|---|---|
| `RequestPersonData` | Snapshot de la persona al momento del request (nombre, DNI, email, celular, puesto, jefe) |
| `AccessRequest` | Request principal. Status: DRAFT → SUBMITTED → APPROVED/REJECTED. Kind: ALTA/MOD/BAJA. Flag `same_modules_for_all`. |
| `AccessRequestItem` | Una línea por empresa; vincula `AccessRequest` → `PermissionSelectionSet` (ordenado) |

### 3.6 Templates / Perfiles

| Modelo | Descripción |
|---|---|
| `AccessTemplate` | Perfil reutilizable. Campos: `name`, `department`, `role_name`, `notes`, `is_active`, `owner` (FK User). **Representa el concepto de "rol" o "perfil estándar".** |
| `AccessTemplateItem` | Una línea por empresa dentro del template; vincula con `PermissionSelectionSet` |

> ⚠️ **Legacy**: `AccessTemplate` y `AccessRequest` tienen un FK nullable `selection_set` que pasará a deprecarse. No usar en lógica nueva; la arquitectura de items es la correcta.

---

## 4. Flujo wizard (solicitud de acceso)

Estado almacenado en **sesión** bajo clave `catalog_wizard`. Se guarda en DB al final de cada paso.

| Paso | URL | Vista | Qué hace |
|---|---|---|---|
| 0 | `wizard/start/` | `WizardStep0StartView` | Elige modo BLANK o TEMPLATE. Si TEMPLATE: selecciona un `AccessTemplate`. |
| 1 | `wizard/person/` | `WizardStep1PersonView` | Rellena `RequestPersonData`. Crea `AccessRequest` (DRAFT) y guarda `request_id` en sesión. |
| 2 | `wizard/companies/` | `WizardStep2CompaniesView` | Multi-selección de `Company` + flag `same_modules_for_all`. Crea `PermissionSelectionSet` + `AccessRequestItem` por empresa. Clona datos de template si aplica. |
| 3 | `wizard/modules/` | `WizardStep3ModulesView` | Árbol de módulos. Si `same_modules_for_all`, un form compartido; si no, un form por item. Escribe `SelectionSetModule/Level/SubLevel`. |
| 4 | `wizard/globals/` | `WizardStep4GlobalsView` | Formsets de `SelectionSetActionValue`, `SelectionSetMatrixPermission`, `SelectionSetPaymentMethod`. Tabs por `ActionPermission.group`. |
| 5 | `wizard/scoped/` | `WizardStep5ScopedView` | Por empresa: paneles + vendedores. Por sucursal: depósitos + cajas. Usa `NoValidationMultipleChoiceField`. |
| 6 | `wizard/review/` | `WizardStep6ReviewView` | Vista de revisión. Al enviar: status → SUBMITTED, envío de email. |

---

## 5. Wizard de templates (creación directa)

> **Implementado a partir de 26/02/2026.**

Wizard separado con clave de sesión `catalog_template_wizard`. No tiene Step de persona.

| Paso | URL | Vista | Qué hace |
|---|---|---|---|
| 0 | `templates/new/start/` | `TemplateWizardStep0StartView` | Ingresa nombre/departamento/rol/notas. Crea `AccessTemplate(is_active=False)` draft en DB y guarda `template_id` en sesión. |
| 1 | `templates/new/modules/` | `TemplateWizardStep2ModulesView` | Árbol de módulos (siempre GLOBAL para el perfil base). Reutiliza `Step3ModulesForm` y `build_module_tree`. |
| 2 | `templates/new/globals/` | `TemplateWizardStep3GlobalsView` | Formsets de acciones, matriz CRUD, medios de pago (siempre GLOBAL para el perfil base). Reutiliza `ActionValueFormSet`, `MatrixFormSet`, `PaymentFormSet`. |
| 3 | `templates/new/review/` | `TemplateWizardStep5ReviewView` | Vista de revisión del perfil base (sin tabs por empresa). Al confirmar: `tmpl.is_active = True`, limpia sesión, redirige a `template_detail`. |

> ⚠️ **El wizard de templates no tiene pasos de empresa/sucursal ni scoped.** Los templates solo capturan datos independientes de empresa/sucursal: módulos, permisos globales, matriz CRUD y medios de pago.

**Item base técnico**: como `PermissionSelectionSet` exige `company` por esquema, el wizard mantiene un único `AccessTemplateItem` base interno (`branch=None`) para persistir módulos/globales. Este dato no se expone en UI del wizard y no implica alcance real por empresa.

**Patrón draft**: el `AccessTemplate` se crea con `is_active=False` en el paso 0 para que todos los `PermissionSelectionSet`/`AccessTemplateItem` tengan FK real desde el inicio. Se activa recién en el paso 3 (review).

**Archivos clave:**
- Vistas: `views/template_wizard/` — `base.py`, `step_0_start.py` … `step_5_review.py`
- Base class: `TemplateWizardBaseView` en `base.py` — session key `TEMPLATE_WIZARD_SESSION_KEY = "catalog_template_wizard"`, método `wizard_context(**extra)` y helper `ensure_single_base_item(tmpl) -> tuple[AccessTemplateItem | None, str | None]`
- HTML: `templates/catalog/template_wizard/` — `_progress.html`, `step_0_start.html` … `step_5_review.html`
- Form paso 0: `forms/template_start.py` — `TemplateStartForm`

---

## 6. URLs del namespace `catalog`

```
catalog:wizard_step_0_start       → wizard/start/
catalog:wizard_step_1_person      → wizard/person/
catalog:wizard_step_2_companies   → wizard/companies/
catalog:wizard_step_3_modules     → wizard/modules/
catalog:wizard_step_4_globals     → wizard/globals/
catalog:wizard_step_5_scoped      → wizard/scoped/
catalog:wizard_step_6_review      → wizard/review/
catalog:wizard_submitted          → requests/<pk>/submitted/
catalog:request_detail            → requests/<pk>/
catalog:request_list              → requests/
catalog:request_make_template     → requests/<id>/make-template/

catalog:template_list             → templates/
catalog:template_detail           → templates/<pk>/
catalog:template_edit             → templates/<pk>/edit/
catalog:template_delete           → templates/<pk>/delete/
catalog:template_wizard_start     → templates/new/start/
catalog:template_wizard_modules   → templates/new/modules/
catalog:template_wizard_globals   → templates/new/globals/
catalog:template_wizard_review    → templates/new/review/
```

---

## 7. Servicios clave

| Función | Archivo | Descripción |
|---|---|---|
| `clone_selection_set(source)` | `services/templates.py` | Deep-clone de un `PermissionSelectionSet`. Usado al inicializar desde template y al crear templates. |
| `create_template_from_request(ar, name, …)` | `services/template_from_request.py` | Crea un `AccessTemplate` desde un request SUBMITTED/APPROVED. |
| `create_template_directly(name, department, role_name, items_data, owner)` | `services/templates.py` | Crea un `AccessTemplate` directamente (sin request previo), a partir de datos del wizard de templates. |
| `import_templates_from_excel(file_obj, owner, company=None, replace_existing=False)` | `services/template_excel_import.py` | Importa templates desde un `.xlsx`; cada solapa se mapea a un `AccessTemplate`, resuelve módulos/subniveles y `ActionPermission`, recrea el item base y sincroniza el `selection_set` legacy para compatibilidad. |

---

## 8. Convenciones del proyecto

- **Forms**: todos usan `BootstrapFormMixin` (en `forms/bootstrap_mixins.py`) → agrega `form-control`/`form-select`/`form-check-input` automáticamente.
- **Vistas**: todas con `LoginRequiredMixin`. Permisos adicionales: staff para operaciones IT.
- **Templates HTML**: `{% extends "base/base.html" %}` + `{% block content %}`. Sidebar en `base/_sidebar.html`.
- **Namespace**: siempre `catalog:` en `{% url %}` y `reverse()`.
- **Sesión wizard**: clave `catalog_wizard` para requests, `catalog_template_wizard` para templates.
- **Sin FKs legacy**: en lógica nueva, siempre usar `items` (AccessRequestItem / AccessTemplateItem), nunca el FK directo `selection_set` en `AccessRequest`/`AccessTemplate`.
- **Permisos CRUD de templates**: editar y eliminar un `AccessTemplate` está restringido a usuarios **staff** (`is_staff=True`). Los usuarios no-staff tienen acceso de solo lectura (lista + detalle).

---

## 9. Estado de implementación

### ✅ Funcional

- Wizard completo de 7 pasos (solicitudes de acceso)
- Multi-empresa con `same_modules_for_all`
- Árbol de módulos ERP de 3 niveles
- Permisos globales (acciones tipadas, matrix CRUD, métodos de pago) vía formsets
- Selecciones scoped (paneles, vendedores, depósitos, cajas) por empresa/sucursal
- Envío de solicitud + notificación por email
- Creación de `AccessTemplate` desde request enviado ("Make Template")
- Wizard pre-cargado desde template (Steps 0 → clona selection_sets)
- Lista de solicitudes (paginada, con búsqueda, scope por usuario/superuser)
- Detalle de solicitud con árbol de módulos y permisos
- Admin Django completo para todos los modelos
- Bootstrap 5 + `BootstrapFormMixin`
- Importación de catálogos desde Excel (management commands)
- **CRUD completo de `AccessTemplate`**: lista (paginada, filtros), detalle (árbol completo), edit metadata, delete con cascada
- **Wizard de creación directa de templates** (6 pasos) — completamente funcional
- **Wizard de creación directa de templates** (4 pasos: start/modules/globals/review) — completamente funcional y sin selección de empresa/sucursal en UI
- **Importación masiva de templates desde Excel**: disponible en Django admin de `AccessTemplate` y con management command `import_access_templates_excel`; procesa una solapa por template y puede reemplazar existentes.

### ⚠️ Pendiente / parcial

| Área | Estado |
|---|---|
| **Visibility Rules** | Modelos + bootstrap command OK. El motor de evaluación (`forms/visibility.py`) existe pero el wizard NO lo llama todavía para mostrar/ocultar bloques condicionalmente. |
| **Transiciones APPROVED/REJECTED** | Los estados existen en `RequestStatus`, pero ninguna vista implementa el flujo de aprobación/rechazo. Solo DRAFT → SUBMITTED está activo. |
| **FKs legacy** | `AccessRequest.selection_set` y `AccessTemplate.selection_set` son nullable y anotados como LEGACY. Pending migración para eliminarlos. |
| **`forms/__init__.py`** | Está vacío; los forms se importan directamente por path en las vistas. |
| **Branches en Step 2** | No existe selección explícita de sucursales en Step 2; emergen implícitamente al asignar items scoped en Step 5. |

---

## 10. Estructura de directorios clave

```
src/
  manage.py
  apps/
    catalog/
      admin/          # Admin por entidad (global_ops, modules, person, requests, rules, scoped, selections, templates)
                      # templates_admin.py agrega URL admin `import-excel/` para carga masiva de templates
      forms/          # bootstrap_mixins, helpers, helpers_globals, person, start, template_meta, template_start, step_2..5, visibility
                      # template_import.py -> TemplateExcelImportForm(excel_file, company, replace_existing)
      management/commands/  # bootstrap_catalog, import_access_templates_excel
      migrations/
      models/         # modules, person, requests, rules, selections, templates + permissions/
      services/       # templates.py (clone_selection_set, create_template_from_request, create_template_directly)
                      # template_excel_import.py -> import_templates_from_excel(file_obj, owner, company=None, replace_existing=False)
      templates/catalog/
        request/      # detail.html, list.html, submitted.html
        template/     # list.html, detail.html, edit.html, delete.html, confirm_delete.html
        template_wizard/  # _progress.html, step_0_start.html … step_5_review.html
        template_pick/    # list.html, _card.html (selector en wizard de requests)
        wizard/       # step_0..6 + _progress.html
      templatetags/   # catalog_extras
      views/
        request_list.py, request_templates.py, requests.py, templates.py
        templates.py  # TemplateListView, TemplateDetailView, TemplateEditView, TemplateDeleteView
        wizard/       # step_0_start.py … step_6_review.py
        template_wizard/  # base.py, step_0_start.py … step_5_review.py
    core/
  config/settings/    # base, development, production
  templates/
    admin/catalog/accesstemplate/  # change_list.html (botón importar), import_excel.html (formulario de carga)
    base/             # base.html, _sidebar.html, _form_field.html, _form_errors.html, _messages.html
    home/dashboard.html
    registration/
```
