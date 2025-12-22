from __future__ import annotations

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.catalog.models import (
    AccessRequest,
    AccessTemplate,
    AccessTemplateItem,
)
from apps.catalog.models.requests import RequestStatus
# tu clonador de selection_set
from apps.catalog.services.templates import clone_selection_set


@transaction.atomic
def create_template_from_request(
    *,
    access_request: AccessRequest,
    name: str,
    department: str = "",
    role_name: str = "",
    notes: str = "",
    owner=None,
) -> AccessTemplate:
    """
    Crea un AccessTemplate a partir de una solicitud existente.
    Copia multiempresa: clona todos los selection_sets (items o legacy).
    """

    name = (name or "").strip()
    if not name:
        raise ValidationError("El nombre del template es obligatorio.")

    # Recomendado: solo permitir desde Enviada o Aprobada (evita templates incompletos)
    if access_request.status not in (RequestStatus.SUBMITTED, RequestStatus.APPROVED):
        raise ValidationError(
            "Solo se puede crear un template desde una solicitud Enviada o Aprobada.")

    # Obtener selection_sets desde items o legacy
    items_qs = access_request.items.select_related(
        "selection_set").order_by("order", "id")

    selection_sets = []
    if items_qs.exists():
        selection_sets = [(it.order, it.notes or "", it.selection_set)
                          for it in items_qs]
    elif getattr(access_request, "selection_set_id", None):
        selection_sets = [(0, "", access_request.selection_set)]
    else:
        raise ValidationError(
            "La solicitud no tiene selection_sets para convertir en template.")

    template = AccessTemplate.objects.create(
        name=name,
        department=(department or "").strip(),
        role_name=(role_name or "").strip(),
        notes=(notes or "").strip(),
        is_active=True,
        owner=owner or access_request.owner,
    )

    for idx, (order, item_notes, ss) in enumerate(selection_sets):
        cloned_ss = clone_selection_set(
            ss,
            notes=f"Template '{name}' — clon desde Request #{access_request.pk}",
        ).cloned

        AccessTemplateItem.objects.create(
            template=template,
            selection_set=cloned_ss,
            order=order if order is not None else idx,
            notes=item_notes,
        )

    return template
