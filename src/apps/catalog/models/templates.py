# src/apps/catalog/models/templates.py
from __future__ import annotations

from django.db import models

from .selections import PermissionSelectionSet


class AccessTemplate(models.Model):
    """
    “Usuario modelo” / Template reutilizable.

    Objetivo:
    - Guardar una preselección para no recargar todo cada vez.
    - Puede representar un perfil típico (rol + departamento + preferencias).

    Importante:
    - No reemplaza a la Request: se usa para CLONAR una selección hacia una nueva Request.
    - No guarda persona (nombre/dni/email). Eso corresponde al snapshot de RequestPersonData.
    """

    name = models.CharField(max_length=160)
    department = models.CharField(max_length=160, blank=True, default="")
    role_name = models.CharField(max_length=160, blank=True, default="")

    selection_set = models.ForeignKey(
        PermissionSelectionSet, on_delete=models.PROTECT, related_name="templates"
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
