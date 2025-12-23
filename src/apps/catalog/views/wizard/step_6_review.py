from __future__ import annotations

from collections import defaultdict, OrderedDict
import base64
import logging
from email.mime.text import MIMEText

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect

from apps.catalog.models.requests import AccessRequest, RequestStatus
from apps.catalog.models.selections import (
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
    SelectionSetActionValue,
    SelectionSetMatrixPermission,
    SelectionSetPaymentMethod,
    SelectionSetLevel,
    SelectionSetSubLevel,
)

from .base import WizardBaseView

logger = logging.getLogger("apps.catalog")


# -------------------------------------------------
# EMAIL: DEV (consola) / PROD (Gmail API OAuth)
# -------------------------------------------------
def _send_email_console(subject: str, body: str, recipients: list[str]) -> None:
    from django.core.mail import send_mail

    if not recipients:
        return

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@local"),
        recipient_list=recipients,
        fail_silently=False,
    )


def _send_email_gmail_oauth(subject: str, body: str, recipients: list[str]) -> None:
    logger.info(f"[EMAIL] _send_email_gmail_oauth called. Recipients: {recipients}")
    if not recipients:
        logger.warning("[EMAIL] No recipients for OAuth email, returning.")
        return

    client_id = getattr(settings, "GMAIL_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GMAIL_OAUTH_CLIENT_SECRET", "")
    refresh_token = getattr(settings, "GMAIL_OAUTH_REFRESH_TOKEN", "")
    sender = getattr(settings, "GMAIL_OAUTH_SENDER", "")

    missing = [
        k
        for k, v in {
            "GMAIL_OAUTH_CLIENT_ID": client_id,
            "GMAIL_OAUTH_CLIENT_SECRET": client_secret,
            "GMAIL_OAUTH_REFRESH_TOKEN": refresh_token,
            "GMAIL_OAUTH_SENDER": sender,
        }.items()
        if not v
    ]
    if missing:
        raise RuntimeError(
            f"Faltan settings OAuth Gmail: {', '.join(missing)}")
    
    logger.info(f"[EMAIL] OAuth settings found. ClientID: ...{client_id[-5:] if client_id else ''}")

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg = MIMEText(body, "plain", "utf-8")
    msg["to"] = ", ".join(recipients)
    msg["from"] = sender
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    logger.info("[EMAIL] Enviando mensaje a Gmail API...")
    ret = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"[EMAIL] Mensaje enviado. Response ID: {ret.get('id')}")


def _notify_it(request_obj: AccessRequest) -> None:
    subject = (
        f"[IT] Nueva solicitud #{request_obj.id} — "
        f"{request_obj.person_data.last_name}, {request_obj.person_data.first_name}"
    )
    body = (
        "Se envió una nueva solicitud.\n\n"
        f"Solicitud: #{request_obj.id}\n"
        f"Tipo: {request_obj.get_kind_display()}\n"
        f"Estado: {request_obj.get_status_display()}\n"
        f"Persona: {request_obj.person_data.last_name}, {request_obj.person_data.first_name}\n"
        f"DNI: {request_obj.person_data.dni}\n"
        f"Email: {request_obj.person_data.email}\n"
    )

    recipients = list(getattr(settings, "CATALOG_IT_NOTIFY_EMAILS", []) or [])
    logger.info(f"[EMAIL] _notify_it called. Recipients found in settings: {recipients}")
    if not recipients:
        logger.warning("[EMAIL] No hay CATALOG_IT_NOTIFY_EMAILS configurado.")
        return

    use_oauth = bool(getattr(settings, "USE_GMAIL_OAUTH", False))

    if settings.DEBUG and not use_oauth:
        _send_email_console(subject, body, recipients)
        logger.info("[EMAIL] Notificación enviada por consola (DEV).")
        return

    _send_email_gmail_oauth(subject, body, recipients)
    logger.info("[EMAIL] Notificación enviada por Gmail API OAuth (PROD).")


class WizardStep6ReviewView(WizardBaseView):
    step = 6
    progress_percent = 100
    template_name = "catalog/wizard/step_6_review_document.html"

    def _get_request(self, request) -> AccessRequest:
        wizard = self.get_wizard(request)
        req_id = wizard.get("request_id")
        if not req_id:
            raise AccessRequest.DoesNotExist

        return (
            AccessRequest.objects.select_related("person_data")
            .prefetch_related(
                "items__selection_set__company",
                "items__selection_set__branch",
                "items__selection_set__modules",
            )
            .get(pk=req_id)
        )

    # -----------------------------
    # Tree: Módulo -> Nivel -> Subnivel
    # -----------------------------
    def _build_levels_tree(self, ss) -> list[dict]:
        """
        Devuelve una estructura:
        [
          {"module": <ErpModule>, "levels": [
              {"level": <ErpModuleLevel>, "sublevels":[<ErpModuleSubLevel>, ...]},
              ...
          ]},
          ...
        ]
        """
        selected_levels = (
            SelectionSetLevel.objects.filter(selection_set=ss)
            .select_related("level__module")
            .order_by("level__module__name", "level__name")
        )
        selected_sublevels = (
            SelectionSetSubLevel.objects.filter(selection_set=ss)
            .select_related("sublevel__level__module", "sublevel__level")
            .order_by("sublevel__level__module__name", "sublevel__level__name", "sublevel__name")
        )

        # module_id -> {"module": module, "levels": OrderedDict(level_id -> {...})}
        mod_map: dict[int, dict] = {}

        for r in selected_levels:
            m = r.level.module
            mod_bucket = mod_map.setdefault(
                m.id, {"module": m, "levels": OrderedDict()})
            mod_bucket["levels"].setdefault(
                r.level.id, {"level": r.level, "sublevels": []}
            )

        for r in selected_sublevels:
            sub = r.sublevel
            lvl = sub.level
            mod = lvl.module

            mod_bucket = mod_map.setdefault(
                mod.id, {"module": mod, "levels": OrderedDict()})
            lvl_bucket = mod_bucket["levels"].setdefault(
                lvl.id, {"level": lvl, "sublevels": []}
            )
            lvl_bucket["sublevels"].append(sub)

        out: list[dict] = []
        for m_id, bucket in sorted(mod_map.items(), key=lambda kv: kv[1]["module"].name):
            levels_list = list(bucket["levels"].values())
            out.append({"module": bucket["module"], "levels": levels_list})

        return out

    # -----------------------------
    # Payloads
    # -----------------------------
    def _build_global_payload(self, ss) -> dict:
        modules = list(ss.modules.filter(is_active=True).order_by("name"))
        levels_tree = self._build_levels_tree(ss)

        control_panels = list(
            SelectionSetControlPanel.objects.filter(selection_set=ss)
            .select_related("control_panel")
            .order_by("control_panel__name")
        )
        sellers = list(
            SelectionSetSeller.objects.filter(selection_set=ss)
            .select_related("seller")
            .order_by("seller__name")
        )

        actions = list(
            SelectionSetActionValue.objects.filter(
                selection_set=ss, is_active=True)
            .select_related("action_permission")
            .order_by("action_permission__group", "action_permission__action")
        )
        actions_by_group = defaultdict(list)
        for r in actions:
            ap = r.action_permission
            if ap.value_type == "BOOL":
                val = "Sí" if bool(r.value_bool) else "No"
                if val != "Sí":
                    continue
            elif ap.value_type == "INT":
                val = "" if r.value_int is None else str(r.value_int)
                if not val:
                    continue
            elif ap.value_type in ("DECIMAL", "PERCENT"):
                val = "" if r.value_decimal is None else str(r.value_decimal)
                if not val:
                    continue
            else:
                val = (r.value_text or "").strip()
                if not val:
                    continue

            actions_by_group[ap.group].append((ap.action, val))

        matrix = list(
            SelectionSetMatrixPermission.objects.filter(selection_set=ss)
            .select_related("permission")
            .order_by("permission__name")
        )
        matrix = [
            r
            for r in matrix
            if any(
                [
                    r.can_create,
                    r.can_update,
                    r.can_authorize,
                    r.can_close,
                    r.can_cancel,
                    r.can_update_validity,
                ]
            )
        ]

        payment_methods = list(
            SelectionSetPaymentMethod.objects.filter(
                selection_set=ss, enabled=True, is_active=True)
            .select_related("payment_method")
            .order_by("payment_method__name")
        )

        return {
            "modules": modules,
            "levels_tree": levels_tree,
            "control_panels": [x.control_panel for x in control_panels],
            "sellers": [x.seller for x in sellers],
            "actions_by_group": dict(actions_by_group),
            "matrix": matrix,
            "payment_methods": [x.payment_method for x in payment_methods],
        }

    def _build_scoped_payload(self, ss) -> dict:
        warehouses = list(
            SelectionSetWarehouse.objects.filter(selection_set=ss)
            .select_related("warehouse")
            .order_by("warehouse__name")
        )
        cash_registers = list(
            SelectionSetCashRegister.objects.filter(selection_set=ss)
            .select_related("cash_register")
            .order_by("cash_register__name")
        )

        return {
            "warehouses": [x.warehouse for x in warehouses],
            "cash_registers": [x.cash_register for x in cash_registers],
        }

    def _global_signature(self, ss) -> tuple:
        """
        Firma para detectar diferencias inesperadas entre sucursales de una misma empresa.
        (No es “seguridad”, es control de consistencia para UX.)
        """
        modules = tuple(ss.modules.filter(is_active=True).order_by(
            "id").values_list("id", flat=True))

        levels = tuple(
            SelectionSetLevel.objects.filter(selection_set=ss)
            .order_by("level_id")
            .values_list("level_id", flat=True)
        )
        sublevels = tuple(
            SelectionSetSubLevel.objects.filter(selection_set=ss)
            .order_by("sublevel_id")
            .values_list("sublevel_id", flat=True)
        )

        control_panels = tuple(
            SelectionSetControlPanel.objects.filter(selection_set=ss)
            .order_by("control_panel_id")
            .values_list("control_panel_id", flat=True)
        )
        sellers = tuple(
            SelectionSetSeller.objects.filter(selection_set=ss)
            .order_by("seller_id")
            .values_list("seller_id", flat=True)
        )

        action_rows = tuple(
            SelectionSetActionValue.objects.filter(
                selection_set=ss, is_active=True)
            .select_related("action_permission")
            .order_by("action_permission_id")
            .values_list(
                "action_permission_id",
                "value_bool",
                "value_int",
                "value_decimal",
                "value_text",
            )
        )

        matrix_rows = tuple(
            SelectionSetMatrixPermission.objects.filter(selection_set=ss)
            .order_by("permission_id")
            .values_list(
                "permission_id",
                "can_create",
                "can_update",
                "can_authorize",
                "can_close",
                "can_cancel",
                "can_update_validity",
            )
        )

        pay_rows = tuple(
            SelectionSetPaymentMethod.objects.filter(
                selection_set=ss, is_active=True)
            .order_by("payment_method_id")
            .values_list("payment_method_id", "enabled")
        )

        return (
            modules,
            levels,
            sublevels,
            control_panels,
            sellers,
            action_rows,
            matrix_rows,
            pay_rows,
        )

    # -----------------------------
    # GET
    # -----------------------------
    def get(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        items = list(req.items.all().order_by("order", "id"))
        if not items:
            messages.warning(request, "Primero definí empresas y sucursales.")
            return self.redirect_to("catalog:wizard_step_2_companies")

        # Agrupar por empresa, respetando el orden de aparición en items
        companies_map: "OrderedDict[int, dict]" = OrderedDict()

        for it in items:
            ss = it.selection_set
            company = ss.company
            bucket = companies_map.get(company.id)
            if bucket is None:
                bucket = {
                    "company": company,
                    "items": [],
                }
                companies_map[company.id] = bucket
            bucket["items"].append(it)

        companies: list[dict] = []

        for company_id, bucket in companies_map.items():
            its = bucket["items"]

            # Base SS: el primero (define globales para la empresa)
            base_ss = its[0].selection_set
            base_sig = self._global_signature(base_ss)

            # Scopes por sucursal: solo depósitos/cajas
            branches = []
            inconsistent = False

            for it in its:
                ss = it.selection_set

                if self._global_signature(ss) != base_sig:
                    inconsistent = True

                branches.append(
                    {
                        "item": it,
                        "branch": ss.branch,  # puede ser None
                        "scoped": self._build_scoped_payload(ss),
                    }
                )

            if inconsistent:
                messages.warning(
                    request,
                    f"Atención: Se detectaron diferencias en permisos globales entre sucursales de {bucket['company'].name}. "
                    "El documento muestra los globales tomando la primera sucursal como referencia.",
                )

            companies.append(
                {
                    "company": bucket["company"],
                    "globals": self._build_global_payload(base_ss),
                    "branches": branches,
                }
            )

        return render(
            request,
            self.template_name,
            self.wizard_context(
                request_obj=req,
                companies=companies,
                items=items,
            ),
        )

    # -----------------------------
    # POST (igual que tenías)
    # -----------------------------
    @transaction.atomic
    def post(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        if req.status != RequestStatus.DRAFT:
            messages.info(request, "La solicitud ya fue enviada o procesada.")
            return redirect("catalog:wizard_submitted", pk=req.id)

        req.status = RequestStatus.SUBMITTED
        req.save(update_fields=["status", "updated_at"])

        def _on_commit_send():
            logger.info(f"[EMAIL] Transaction committed. Starting _on_commit_send for req {req.id}")
            try:
                req2 = AccessRequest.objects.select_related(
                    "person_data").get(pk=req.id)
                _notify_it(req2)
            except Exception as e:
                logger.exception(
                    "[EMAIL] Falló notificación IT para request_id=%s: %s", req.id, e
                )

        transaction.on_commit(_on_commit_send)

        messages.success(request, "Solicitud enviada correctamente.")
        return redirect("catalog:wizard_submitted", pk=req.id)
