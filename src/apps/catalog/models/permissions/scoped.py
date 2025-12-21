# src/apps/catalog/models/permissions/scoped.py
from __future__ import annotations

from django.db import models


def _norm_name(value: str) -> str:
    return " ".join(str(value or "").strip().split())


class Company(models.Model):
    """Empresa (scope principal)."""
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ("name",)

    def save(self, *args, **kwargs):
        self.name = _norm_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Branch(models.Model):
    """Sucursal (depende de Company)."""
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ("company__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="uniq_branch_per_company_name"),
        ]

    def save(self, *args, **kwargs):
        self.name = _norm_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"


class Warehouse(models.Model):
    """Depósito habilitado (depende de Branch)."""
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="warehouses")
    name = models.CharField(max_length=180)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Depósito"
        verbose_name_plural = "Depósitos"
        ordering = ("branch__company__name", "branch__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"], name="uniq_warehouse_per_branch_name"),
        ]

    def save(self, *args, **kwargs):
        self.name = _norm_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.branch.company.name} / {self.branch.name} / {self.name}"


class CashRegister(models.Model):
    """Caja (depende de Company + Branch). Hoja: 'Cajas'."""
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="cash_registers")
    name = models.CharField(max_length=180)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ("branch__company__name", "branch__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"], name="uniq_cashregister_per_branch_name"),
        ]

    def save(self, *args, **kwargs):
        self.name = _norm_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.branch.company.name} / {self.branch.name} / {self.name}"


class ControlPanel(models.Model):
    """Panel/Informe (depende de Company). Hoja: 'Paneles Control'."""
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="control_panels")
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Panel de control"
        verbose_name_plural = "Paneles de control"
        ordering = ("company__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="uniq_panel_per_company_name"),
        ]

    def save(self, *args, **kwargs):
        self.name = _norm_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"


class Seller(models.Model):
    """Vendedor (depende de Company). Hoja: 'Vendedores'."""
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="sellers")
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vendedor"
        verbose_name_plural = "Vendedores"
        ordering = ("company__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="uniq_seller_per_company_name"),
        ]

    def save(self, *args, **kwargs):
        self.name = _norm_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"
