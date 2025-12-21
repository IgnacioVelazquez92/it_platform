# src/apps/catalog/models/permissions/global_ops.py
from __future__ import annotations

from django.db import models


def _norm_name(value: str) -> str:
    return " ".join(str(value or "").strip().split())


class ActionValueType(models.TextChoices):
    BOOL = "BOOL", "Bool"
    INT = "INT", "Entero"
    DECIMAL = "DECIMAL", "Decimal"
    PERCENT = "PERCENT", "Porcentaje"
    TEXT = "TEXT", "Texto"


class ActionPermission(models.Model):
    group = models.CharField(max_length=120)  # Tipo
    action = models.CharField(max_length=220)  # Acciones
    value_type = models.CharField(
        max_length=12, choices=ActionValueType.choices)  # Permiso (tipo)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "action"], name="uniq_actionperm_group_action"),
        ]
        ordering = ("group", "action")

    def save(self, *args, **kwargs):
        self.group = _norm_name(self.group)
        self.action = _norm_name(self.action)
        super().save(*args, **kwargs)


class MatrixPermission(models.Model):
    """
    Permiso funcional con columnas fijas de acciones.
    Representa una fila completa de la matriz.
    """

    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)

    can_create = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_authorize = models.BooleanField(default=False)
    can_close = models.BooleanField(default=False)
    can_cancel = models.BooleanField(default=False)
    can_update_validity = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Permiso (matriz)"
        verbose_name_plural = "Permisos (matriz)"
        ordering = ("name",)

    def __str__(self):
        return self.name


class PaymentMethodPermission(models.Model):
    """
    Catálogo simple de 'Medios de Pago' (si existen y se pueden habilitar).
    """

    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Medio de pago"
        verbose_name_plural = "Medios de pago"
        ordering = ("name",)

    def save(self, *args, **kwargs):
        self.name = _norm_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
