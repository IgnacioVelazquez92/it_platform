# src/apps/catalog/models/templates.py
from __future__ import annotations

from django.db import models

from .selections import PermissionSelectionSet
from django.conf import settings


class AccessTemplate(models.Model):
    """
    “Usuario modelo” / Template reutilizable.

    Objetivo:
    - Guardar preselecciones para no recargar todo cada vez.
    - Puede representar un perfil típico (rol + departamento + preferencias).

    Importante:
    - Se usa para CLONAR selecciones hacia una nueva AccessRequest.
    - No guarda persona (nombre/dni/email).
    """

    name = models.CharField(max_length=160)
    department = models.CharField(max_length=160, blank=True, default="")
    role_name = models.CharField(max_length=160, blank=True, default="")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_templates",
    )
    # Legacy: mantener por transición (NO usar como fuente de verdad a futuro)
    selection_set = models.ForeignKey(
        PermissionSelectionSet,
        on_delete=models.PROTECT,
        related_name="templates_legacy",
        null=True,
        blank=True,
        help_text="LEGACY: se migrará a items. Evitar usarlo en lógica nueva.",
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Template de acceso"
        verbose_name_plural = "Templates de acceso"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["name"], name="uniq_access_template_name"),
        ]

    def __str__(self) -> str:
        base = self.name
        if self.department or self.role_name:
            return f"{base} — {self.department} — {self.role_name}".strip(" —")
        return base


class AccessTemplateItem(models.Model):
    """
    Línea del template: equivale a un AccessRequestItem, pero para plantillas.

    Permite:
    - múltiples empresas/sucursales dentro de un template
    - orden y notas por línea
    """

    template = models.ForeignKey(
        AccessTemplate, on_delete=models.CASCADE, related_name="items"
    )
    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.PROTECT, related_name="template_items"
    )

    order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ítem de template"
        verbose_name_plural = "Ítems de template"
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["template", "selection_set"], name="uniq_template_selection_set"
            ),
        ]

    def __str__(self) -> str:
        ss = self.selection_set
        return f"Template #{self.template_id} — {ss.company} / {ss.branch}"
