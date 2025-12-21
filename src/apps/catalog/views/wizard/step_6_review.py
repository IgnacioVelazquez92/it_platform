from __future__ import annotations

from collections import defaultdict
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
)

from .base import WizardBaseView

logger = logging.getLogger("apps.catalog")


# -------------------------------------------------
# EMAIL: DEV (consola) / PROD (Gmail API OAuth)
# -------------------------------------------------
def _send_email_console(subject: str, body: str, recipients: list[str]) -> None:
    """
    DEV: se imprime en consola usando el backend console de Django
    (igual deja rastros en logs/terminal, sin depender de SMTP).
    """
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
    """
    PROD: Gmail API con OAuth (refresh_token).
    Requiere:
      - GMAIL_OAUTH_CLIENT_ID
      - GMAIL_OAUTH_CLIENT_SECRET
      - GMAIL_OAUTH_REFRESH_TOKEN
      - GMAIL_OAUTH_SENDER (cuenta real que enviará)
    """
    if not recipients:
        return

    client_id = getattr(settings, "GMAIL_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GMAIL_OAUTH_CLIENT_SECRET", "")
    refresh_token = getattr(settings, "GMAIL_OAUTH_REFRESH_TOKEN", "")
    sender = getattr(settings, "GMAIL_OAUTH_SENDER", "")

    missing = [k for k, v in {
        "GMAIL_OAUTH_CLIENT_ID": client_id,
        "GMAIL_OAUTH_CLIENT_SECRET": client_secret,
        "GMAIL_OAUTH_REFRESH_TOKEN": refresh_token,
        "GMAIL_OAUTH_SENDER": sender,
    }.items() if not v]

    if missing:
        raise RuntimeError(
            f"Faltan settings OAuth Gmail: {', '.join(missing)}")

    # OAuth Credentials (refresh token)
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

    # MIME email
    msg = MIMEText(body, "plain", "utf-8")
    msg["to"] = ", ".join(recipients)
    msg["from"] = sender
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def _notify_it(request_obj: AccessRequest) -> None:
    """
    Decide DEV vs PROD.
    - DEV: consola.
    - PROD: OAuth Gmail API.
    """
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
    if not recipients:
        logger.warning("[EMAIL] No hay CATALOG_IT_NOTIFY_EMAILS configurado.")
        return

    # Regla: en PROD sí o sí OAuth
    use_oauth = bool(getattr(settings, "USE_GMAIL_OAUTH", False))

    if settings.DEBUG and not use_oauth:
        _send_email_console(subject, body, recipients)
        logger.info("[EMAIL] Notificación enviada por consola (DEV).")
        return

    # PROD: OAuth
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
            AccessRequest.objects
            .select_related("person_data")
            .prefetch_related(
                "items__selection_set__company",
                "items__selection_set__branch",
                "items__selection_set__modules",
            )
            .get(pk=req_id)
        )

    def _build_selection_payload(self, ss):
        modules = list(ss.modules.filter(is_active=True).order_by("name"))

        warehouses = list(
            SelectionSetWarehouse.objects
            .filter(selection_set=ss)
            .select_related("warehouse")
            .order_by("warehouse__name")
        )
        cash_registers = list(
            SelectionSetCashRegister.objects
            .filter(selection_set=ss)
            .select_related("cash_register")
            .order_by("cash_register__name")
        )
        control_panels = list(
            SelectionSetControlPanel.objects
            .filter(selection_set=ss)
            .select_related("control_panel")
            .order_by("control_panel__name")
        )
        sellers = list(
            SelectionSetSeller.objects
            .filter(selection_set=ss)
            .select_related("seller")
            .order_by("seller__name")
        )

        actions = list(
            SelectionSetActionValue.objects
            .filter(selection_set=ss, is_active=True)
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
            SelectionSetMatrixPermission.objects
            .filter(selection_set=ss)
            .select_related("permission")
            .order_by("permission__name")
        )
        matrix = [
            r for r in matrix
            if any([r.can_create, r.can_update, r.can_authorize, r.can_close, r.can_cancel, r.can_update_validity])
        ]

        payment_methods = list(
            SelectionSetPaymentMethod.objects
            .filter(selection_set=ss, enabled=True, is_active=True)
            .select_related("payment_method")
            .order_by("payment_method__name")
        )

        return {
            "modules": modules,
            "warehouses": [x.warehouse for x in warehouses],
            "cash_registers": [x.cash_register for x in cash_registers],
            "control_panels": [x.control_panel for x in control_panels],
            "sellers": [x.seller for x in sellers],
            "actions_by_group": dict(actions_by_group),
            "matrix": matrix,
            "payment_methods": [x.payment_method for x in payment_methods],
            "levels_tree": [],
        }

    def get(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        items = list(req.items.all().order_by("order", "id"))
        if not items:
            messages.warning(request, "Primero definí empresas y sucursales.")
            return self.redirect_to("catalog:wizard_step_2_companies")

        blocks = []
        for it in items:
            ss = it.selection_set
            blocks.append(
                {
                    "item": it,
                    "selection_set": ss,
                    "company": ss.company,
                    "branch": ss.branch,
                    "payload": self._build_selection_payload(ss),
                }
            )

        return render(
            request,
            self.template_name,
            self.wizard_context(
                request_obj=req,
                blocks=blocks,
                items=items,
            ),
        )

    @transaction.atomic
    def post(self, request):
        try:
            req = self._get_request(request)
        except AccessRequest.DoesNotExist:
            return self.redirect_to("catalog:wizard_step_1_person")

        if req.status != RequestStatus.DRAFT:
            messages.info(request, "La solicitud ya fue enviada o procesada.")
            return redirect("catalog:wizard_submitted", pk=req.id)

        # 1) Persistir estado
        req.status = RequestStatus.SUBMITTED
        req.save(update_fields=["status", "updated_at"])

        # 2) Enviar email SOLO si la transacción se confirma
        def _on_commit_send():
            try:
                # refrescar para tener person_data cargado si hace falta
                req2 = AccessRequest.objects.select_related(
                    "person_data").get(pk=req.id)
                _notify_it(req2)
            except Exception as e:
                logger.exception(
                    "[EMAIL] Falló notificación IT para request_id=%s: %s", req.id, e)

        transaction.on_commit(_on_commit_send)

        messages.success(request, "Solicitud enviada correctamente.")
        return redirect("catalog:wizard_submitted", pk=req.id)
