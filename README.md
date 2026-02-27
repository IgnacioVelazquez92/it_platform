# IT Platform (Pharmacenter)

Aplicación Django para gestionar solicitudes de acceso al ERP mediante un wizard multi-paso, con catálogos importables desde Excel, reglas de visibilidad y generación de plantillas reutilizables.

## Contexto rápido (IA / onboarding)

- Framework: Django `6.0`
- App principal de negocio: `src/apps/catalog`
- Flujo central: wizard de solicitud (`step_0` a `step_6`)
- Objeto principal: `AccessRequest`
- Reutilización de configuraciones: `AccessTemplate`
- Catálogos cargados por management commands desde `permisos.xlsx` y `Configuraciones.xlsx`
- Entorno local por defecto: SQLite (`config.settings.development`)
- Entorno productivo: PostgreSQL vía `DATABASE_URL` (`config.settings.production`)

## Estructura del proyecto

```text
.
├─ src/
│  ├─ manage.py
│  ├─ config/
│  │  ├─ urls.py
│  │  └─ settings/
│  │     ├─ base.py
│  │     ├─ development.py
│  │     └─ production.py
│  ├─ apps/
│  │  ├─ core/
│  │  │  ├─ urls.py
│  │  │  └─ views.py
│  │  └─ catalog/
│  │     ├─ urls.py
│  │     ├─ models/
│  │     │  ├─ modules.py
│  │     │  ├─ rules.py
│  │     │  ├─ selections.py
│  │     │  ├─ requests.py
│  │     │  ├─ templates.py
│  │     │  └─ permissions/
│  │     │     ├─ scoped.py
│  │     │     ├─ global_ops.py
│  │     │     └─ assignments.py
│  │     ├─ forms/
│  │     ├─ views/
│  │     │  ├─ wizard/
│  │     │  ├─ requests.py
│  │     │  ├─ request_list.py
│  │     │  └─ request_templates.py
│  │     ├─ services/
│  │     ├─ admin/
│  │     ├─ management/commands/
│  │     └─ templates/catalog/
│  ├─ templates/
│  │  ├─ base/
│  │  ├─ home/
│  │  └─ registration/
│  └─ static/
├─ requirements.txt
├─ permisos.xlsx
└─ Configuraciones.xlsx
```

## Dominio funcional (catalog)

### Catálogos base

- `ErpModule`, `ErpModuleLevel`, `ErpModuleSubLevel`: árbol Módulo/Nivel/Subnivel.
- Scoped: `Company`, `Branch`, `Warehouse`, `CashRegister`, `ControlPanel`, `Seller`.
- Globales: `ActionPermission`, `MatrixPermission`, `PaymentMethodPermission`.

### Reglas de visibilidad

- `PermissionBlock`: bloque UI gobernable por reglas.
- `PermissionVisibilityRule`: regla con prioridad.
- `PermissionVisibilityTrigger`: dispara por módulo/nivel/subnivel.
- `PermissionVisibilityRuleBlock`: relación regla -> bloques mostrados.

### Selecciones (payload reusable)

- `PermissionSelectionSet`: contenedor de permisos seleccionados para una empresa/sucursal.
- Globales elegidos: `SelectionSetActionValue`, `SelectionSetMatrixPermission`, `SelectionSetPaymentMethod`.
- Scoped elegidos: `SelectionSetWarehouse`, `SelectionSetCashRegister`, `SelectionSetControlPanel`, `SelectionSetSeller`.
- Módulos elegidos: `SelectionSetModule`, `SelectionSetLevel`, `SelectionSetSubLevel`.

### Objetos de negocio

- `AccessRequest`: solicitud principal (estado, solicitante, owner).
- `AccessRequestItem`: línea por empresa/sucursal (multi-empresa).
- `AccessTemplate`: plantilla reutilizable.
- `AccessTemplateItem`: líneas de plantilla (equivalentes a request items).

## Flujo del wizard

Implementación en `src/apps/catalog/views/wizard/`:

1. `step_0_start.py`: modo de inicio (desde cero o template).
2. `step_1_person.py`: datos personales; crea/actualiza `AccessRequest`.
3. `step_2_companies.py`: alcance por empresa y flag `same_modules_for_all`.
4. `step_3_modules.py`: módulos + subniveles (globales o por item).
5. `step_4_globals.py`: permisos globales (acciones, matriz, medios de pago).
6. `step_5_scoped.py`: paneles, vendedores, depósitos, cajas.
7. `step_6_review.py`: revisión final, envío y notificación email.

Contexto de sesión del wizard:

- Clave de sesión: `catalog_wizard`
- Datos habituales: `request_id`, `template_id`, `company_ids`, `branch_ids`, `same_modules_for_all`

## URLs principales

- Base app: `src/config/urls.py`
- Home/login/logout/password change: `src/apps/core/urls.py`
- Catálogo: `src/apps/catalog/urls.py`

Rutas de catálogo relevantes:

- `/catalog/wizard/start/`
- `/catalog/wizard/person/`
- `/catalog/wizard/companies/`
- `/catalog/wizard/modules/`
- `/catalog/wizard/globals/`
- `/catalog/wizard/scoped/`
- `/catalog/wizard/review/`
- `/catalog/requests/`
- `/catalog/requests/<id>/`
- `/catalog/requests/<id>/make-template/`

## Setup local

### 1) Instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Variables de entorno mínimas

`src/manage.py` carga `.env` desde la raíz del repo y usa por defecto:

- `DJANGO_SETTINGS_MODULE=config.settings.development`

Variables sugeridas para local:

```dotenv
SECRET_KEY=dev-secret
DEBUG=1
DJANGO_SETTINGS_MODULE=config.settings.development
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 3) Migrar y correr

```bash
cd src
python manage.py migrate
python manage.py runserver
```

## Carga de catálogos

Comandos disponibles en `src/apps/catalog/management/commands/`:

```bash
cd src
python manage.py import_modules_from_excel --file ../permisos.xlsx
python manage.py import_scoped_from_excel --file ../Configuraciones.xlsx
python manage.py import_action_permissions_from_excel --file ../Configuraciones.xlsx
python manage.py bootstrap_visibility_rules
```

Bootstrap integral:

```bash
cd src
python manage.py bootstrap_catalog
```

Opcionales:

- `--dry-run` en importadores (simula sin persistir)
- `bootstrap_catalog --create-superuser` (usa variables `DJANGO_SUPERUSER_*`)
- `bootstrap_catalog --create-superuser --write-env` (solo local)

## Plantillas desde solicitudes

- Vista: `src/apps/catalog/views/request_templates.py`
- Servicio: `src/apps/catalog/services/template_from_request.py`

Regla importante:

- Solo se puede crear template desde solicitudes `SUBMITTED` o `APPROVED`.

## Email / notificaciones

En `step_6_review.py` se notifica a IT al enviar solicitud:

- En desarrollo: backend de consola (si no se usa OAuth).
- En producción: Gmail API OAuth (`google-api-python-client`, `google-auth`).

Variables relevantes:

- `CATALOG_IT_NOTIFY_EMAILS`
- `USE_GMAIL_OAUTH`
- `GMAIL_OAUTH_SENDER`
- `GMAIL_OAUTH_CLIENT_ID`
- `GMAIL_OAUTH_CLIENT_SECRET`
- `GMAIL_OAUTH_REFRESH_TOKEN`

## Admin

Registros admin organizados por módulo en `src/apps/catalog/admin/` y cargados desde `src/apps/catalog/admin/__init__.py`.

Cobertura:

- catálogos ERP/scoped/globales
- reglas de visibilidad
- selections
- requests/templates
- datos personales

## Guía de cambios (para IA)

Si necesitás modificar comportamiento, este es el orden recomendado:

1. Verificar modelo afectado en `models/`.
2. Verificar form asociado en `forms/`.
3. Ajustar step del wizard en `views/wizard/`.
4. Ajustar template en `templates/catalog/wizard/`.
5. Revisar admin/commands si impacta catálogos.

Invariantes importantes:

- `AccessRequest.owner` no puede quedar nulo.
- `AccessRequestItem` representa la fuente de verdad multi-empresa.
- `same_modules_for_all` cambia lógica de steps 3 y 4.
- `PermissionSelectionSet.branch` debe pertenecer a `company`.
- Plantillas nuevas se construyen clonando `selection_sets`, no referenciando directo.

## Estado del README

Este README fue actualizado contra el estado actual del código del repositorio.
Para mantenerlo vigente, priorizar cambios en:

- `src/apps/catalog/models/`
- `src/apps/catalog/views/wizard/`
- `src/apps/catalog/management/commands/`
- `src/apps/catalog/urls.py`
