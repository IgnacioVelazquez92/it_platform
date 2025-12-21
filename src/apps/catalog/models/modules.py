# src/apps/catalog/models/modules.py
from __future__ import annotations

from django.db import models


class ErpModule(models.Model):
    """
    Nodo raíz del árbol del ERP (columna 'Modulo' del Excel).
    Ej: 'Gestión Comercial'
    """
    name = models.CharField(max_length=160, unique=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Módulo ERP"
        verbose_name_plural = "Módulos ERP"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class ErpModuleLevel(models.Model):
    """
    Segundo nivel del árbol (columna 'Nivel' del Excel).
    Ej: 'Ventas', 'Clientes', etc.
    """
    module = models.ForeignKey(
        ErpModule, on_delete=models.CASCADE, related_name="levels")
    name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nivel ERP"
        verbose_name_plural = "Niveles ERP"
        ordering = ("module__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["module", "name"], name="uniq_level_per_module_name"),
        ]

    def __str__(self) -> str:
        return f"{self.module.name} / {self.name}"


class ErpModuleSubLevel(models.Model):
    """
    Tercer nivel del árbol (columna 'Subnivel' del Excel).
    Ej: 'Oportunidades', 'Presupuestos', etc.
    """
    level = models.ForeignKey(
        ErpModuleLevel, on_delete=models.CASCADE, related_name="sublevels")
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subnivel ERP"
        verbose_name_plural = "Subniveles ERP"
        ordering = ("level__module__name", "level__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["level", "name"], name="uniq_sublevel_per_level_name"),
        ]

    def __str__(self) -> str:
        return f"{self.level.module.name} / {self.level.name} / {self.name}"
