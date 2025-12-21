# src/apps/catalog/models/requests.py
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from .person import RequestPersonData
from .selections import PermissionSelectionSet


class RequestKind(models.TextChoices):
    ALTA = "ALTA", "Alta"
    MODIFICACION = "MOD", "Modificación"
    BAJA = "BAJA", "Baja"


class RequestStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    SUBMITTED = "SUBMITTED", "Enviada"
    APPROVED = "APPROVED", "Aprobada"
    REJECTED = "REJECTED", "Rechazada"


class AccessRequest(models.Model):
    """
    Solicitud principal (imprimible y trazable).

    Guarda:
    - Snapshot de persona (RequestPersonData)
    - Un set (o sets) de selecciones (PermissionSelectionSet) a través de AccessRequestItem
    - Estado básico del flujo (borrador/enviada/aprobada/rechazada)

    No guarda:
    - Catálogos (modules.py / permissions/*)
    - Reglas (rules.py)
    """

    kind = models.CharField(
        max_length=8, choices=RequestKind.choices, default=RequestKind.ALTA
    )
    status = models.CharField(
        max_length=16, choices=RequestStatus.choices, default=RequestStatus.DRAFT
    )

    person_data = models.ForeignKey(
        RequestPersonData, on_delete=models.PROTECT, related_name="requests"
    )

    # Compatibilidad: el modelo original tenía un único selection_set.
    # Ahora la solicitud soporta múltiples empresas/sucursales vía AccessRequestItem.
    # Dejar nullable evita romper registros existentes y permite migración incremental.
    selection_set = models.ForeignKey(
        PermissionSelectionSet,
        on_delete=models.PROTECT,
        related_name="requests",
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["kind", "created_at"]),
        ]

    def clean(self):
        super().clean()
        # Regla de transición: si existen items, no debería usarse selection_set directo.
        if self.pk and self.selection_set_id and self.items.exists():
            raise ValidationError(
                {"selection_set":
                    "Esta solicitud usa múltiples selecciones (items); no debe tener selection_set directo."}
            )

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.person_data} — {self.get_status_display()}"


class AccessRequestItem(models.Model):
    """
    Línea de solicitud: una empresa/sucursal (y sus scoped/globales) dentro de una AccessRequest.

    Permite:
    - múltiples empresas dentro de una misma solicitud
    - clonar globales y luego ajustar scope por empresa
    """

    request = models.ForeignKey(
        AccessRequest, on_delete=models.CASCADE, related_name="items"
    )
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.PROTECT, related_name="request_items"
    )

    order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ítem de solicitud"
        verbose_name_plural = "Ítems de solicitud"
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["request", "selection_set"], name="uniq_request_selection_set"
            ),
        ]

    def __str__(self) -> str:
        return f"Request #{self.request_id} — {self.selection_set.company} / {self.selection_set.branch}"
