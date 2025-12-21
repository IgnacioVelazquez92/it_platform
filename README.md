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
│  │  └─ _messages.html
│  ├─ home/
│  │  └─ dashboard.html
│  └─ registration/
│     ├─ login.html
│     └─ logout_confirm.html
├─ static/
│  ├─ vendor/
│  │  ├─ bootstrap/
│  │  └─ bootstrap-icons/
│  └─ app/
│     ├─ css/
│     └─ js/
└─ apps/
   ├─ core/
   │  ├─ apps.py
   │  ├─ views.py
   │  ├─ urls.py
   │  └─ migrations/
   └─ catalog/
      ├─ apps.py
      ├─ admin.py
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
      │  ├─ person.py
      │  ├─ scope_modules.py
      │  ├─ scoped_selections.py
      │  ├─ global_permissions.py
      │  └─ helpers.py
      ├─ models/
      │  ├─ __init__.py
      │  ├─ person.py
      │  ├─ requests.py
      │  ├─ templates.py
      │  ├─ selections.py
      │  ├─ modules.py
      │  ├─ permissions/
      │  │  ├─ __init__.py
      │  │  ├─ scoped.py
      │  │  └─ global_ops.py
      │  └─ rules.py
      ├─ views/
      │  └─ __init__.py
      ├─ migrations/
      └─ management/
         ├─ __init__.py
         └─ commands/
            ├─ __init__.py
            ├─ import_modules_from_excel.py
            ├─ import_scoped_from_excel.py
            ├─ import_action_permissions_from_excel.py
            └─ bootstrap_visibility_rules.py
```

---

## Descripción breve por archivo

### templates/base

- `base.html`  
  Layout base global con Bootstrap y bloques de extensión.

- `_sidebar.html`  
  Sidebar principal de navegación de la plataforma.

- `_messages.html`  
  Render centralizado de mensajes de Django.

---

### templates/home

- `dashboard.html`  
  Home protegido de la plataforma (hub inicial).

---

### templates/registration

- `login.html`  
  Login usando autenticación nativa de Django.

- `logout_confirm.html`  
  Pantalla de confirmación previa al logout (GET).

---

### static

- `vendor/bootstrap/`  
  Assets locales de Bootstrap (CSS/JS).

- `vendor/bootstrap-icons/`  
  Iconos Bootstrap usados en la UI.

- `app/css`  
  Estilos propios de la plataforma.

- `app/js`  
  Scripts propios de la plataforma.

---

### apps/core

- `apps.py`  
  Configuración de la app core de la plataforma.

- `views.py`  
  Vistas transversales (`HomeDashboardView`, `LogoutConfirmView`).

- `urls.py`  
  URLs base (home, login, logout).

---

### apps/catalog/forms

- `person.py`  
  Formulario de carga de `RequestPersonData`.

- `scope_modules.py`  
  Formulario de selección de empresa, sucursal y módulos.

- `scoped_selections.py`  
  Formulario de selecciones scoped dependientes de company/branch.

- `global_permissions.py`  
  Formsets de permisos globales (acciones, matriz, medios de pago).

- `helpers.py`  
  Helpers reutilizables de validación y sincronización de selecciones.
