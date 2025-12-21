# src/apps/catalog/models/rules.py
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .modules import ErpModule, ErpModuleLevel, ErpModuleSubLevel


class BlockKind(models.TextChoices):
    SCOPED = "SCOPED", "Scoped"
    GLOBAL = "GLOBAL", "Global"


class ScopedEntity(models.TextChoices):
    # Nota: Company y Branch los vas a pedir SIEMPRE, pero igual los dejo
    # disponibles por si más adelante querés gobernarlos por reglas.
    COMPANY = "COMPANY", "Empresa"
    BRANCH = "BRANCH", "Sucursal"
    WAREHOUSE = "WAREHOUSE", "Depósito"
    CASH_REGISTER = "CASH_REGISTER", "Caja"
    CONTROL_PANEL = "CONTROL_PANEL", "Panel de control"
    SELLER = "SELLER", "Vendedor"


class GlobalEntity(models.TextChoices):
    ACTION = "ACTION", "Acciones"
    MATRIX = "MATRIX", "Matriz"
    PAYMENT_METHOD = "PAYMENT_METHOD", "Medios de pago"


class PermissionBlock(models.Model):
    """
    Bloque de UI que puede mostrarse/ocultarse por reglas.

    - No guarda valores elegidos (eso será Assignments).
    - Puede representar catálogos scoped (dependen de Company/Branch)
      o catálogos globales (no dependen de Company/Branch).
    - Para GLOBAL/ACTION soporta filtro por ActionPermission.group (exact match).
    """

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)

    kind = models.CharField(max_length=12, choices=BlockKind.choices)

    scoped_entity = models.CharField(
        max_length=24, choices=ScopedEntity.choices, null=True, blank=True
    )
    global_entity = models.CharField(
        max_length=24, choices=GlobalEntity.choices, null=True, blank=True
    )

    # Filtros opcionales (por ahora solo para GLOBAL/ACTION)
    action_group = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        help_text="Solo aplica para GLOBAL/ACTION. Exact match sobre ActionPermission.group.",
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bloque de permisos"
        verbose_name_plural = "Bloques de permisos"
        ordering = ("order", "name")

    def clean(self):
        super().clean()

        if self.kind == BlockKind.SCOPED:
            if not self.scoped_entity or self.global_entity:
                raise ValidationError(
                    "SCOPED requiere scoped_entity y no permite global_entity.")
            if self.action_group:
                raise ValidationError(
                    "action_group no aplica a bloques SCOPED.")

        if self.kind == BlockKind.GLOBAL:
            if not self.global_entity or self.scoped_entity:
                raise ValidationError(
                    "GLOBAL requiere global_entity y no permite scoped_entity.")
            if self.global_entity != GlobalEntity.ACTION and self.action_group:
                raise ValidationError(
                    "action_group solo aplica para GLOBAL/ACTION.")

        if self.kind not in (BlockKind.SCOPED, BlockKind.GLOBAL):
            raise ValidationError("kind inválido.")

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class RuleMatchMode(models.TextChoices):
    ANY = "ANY", "Cualquiera (ANY)"
    # ALL lo agregamos solo si aparece un caso real; por ahora mantenemos simple.
    # ALL = "ALL", "Todos (ALL)"


class PermissionVisibilityRule(models.Model):
    """
    Regla simple: si matchea por selección de módulo/nivel/subnivel -> muestra bloques.

    Nota: si una regla NO tiene triggers, se interpreta como "siempre matchea".
    Útil para una regla base (modo incremental) mientras todavía no segregás por módulos.
    """

    name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)

    # Recomendación: mayor = más prioridad
    priority = models.IntegerField(default=0)

    match_mode = models.CharField(
        max_length=8, choices=RuleMatchMode.choices, default=RuleMatchMode.ANY
    )

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Regla de visibilidad"
        verbose_name_plural = "Reglas de visibilidad"
        ordering = ("-priority", "name")

    def __str__(self) -> str:
        return f"{self.name} (prio {self.priority})"


class PermissionVisibilityTrigger(models.Model):
    """
    Trigger unitario: referencia SOLO uno de (module, level, sublevel).
    Matchea si el usuario seleccionó ese elemento.
    """

    rule = models.ForeignKey(
        PermissionVisibilityRule, on_delete=models.CASCADE, related_name="triggers"
    )

    module = models.ForeignKey(
        ErpModule, on_delete=models.CASCADE, null=True, blank=True)
    level = models.ForeignKey(
        ErpModuleLevel, on_delete=models.CASCADE, null=True, blank=True)
    sublevel = models.ForeignKey(
        ErpModuleSubLevel, on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        verbose_name = "Trigger de visibilidad"
        verbose_name_plural = "Triggers de visibilidad"
        constraints = [
            models.CheckConstraint(
                name="trigger_exactly_one_fk",
                condition=(
                    (Q(module__isnull=False) & Q(level__isnull=True)
                     & Q(sublevel__isnull=True))
                    | (Q(module__isnull=True) & Q(level__isnull=False) & Q(sublevel__isnull=True))
                    | (Q(module__isnull=True) & Q(level__isnull=True) & Q(sublevel__isnull=False))
                ),
            ),
        ]

    def clean(self):
        super().clean()
        filled = sum(
            [
                1 if self.module_id else 0,
                1 if self.level_id else 0,
                1 if self.sublevel_id else 0,
            ]
        )
        if filled != 1:
            raise ValidationError(
                "Un trigger debe tener exactamente uno de: module, level o sublevel.")

    def __str__(self) -> str:
        if self.module_id:
            return f"module: {self.module}"
        if self.level_id:
            return f"level: {self.level}"
        return f"sublevel: {self.sublevel}"


class RuleBlockMode(models.TextChoices):
    SHOW = "SHOW", "Mostrar"
    # HIDE lo dejamos fuera por simplicidad. Si aparece un caso real, se agrega sin romper.
    # HIDE = "HIDE", "Ocultar"


class PermissionVisibilityRuleBlock(models.Model):
    """
    Mapeo regla -> bloque(s) a mostrar.
    """

    rule = models.ForeignKey(
        PermissionVisibilityRule, on_delete=models.CASCADE, related_name="rule_blocks"
    )
    block = models.ForeignKey(
        PermissionBlock, on_delete=models.CASCADE, related_name="used_in_rules")

    mode = models.CharField(
        max_length=8, choices=RuleBlockMode.choices, default=RuleBlockMode.SHOW)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Bloque por regla"
        verbose_name_plural = "Bloques por regla"
        ordering = ("order", "block__order", "block__name")
        constraints = [
            models.UniqueConstraint(
                fields=["rule", "block"], name="uniq_rule_block"),
        ]

    def clean(self):
        super().clean()
        if self.mode != RuleBlockMode.SHOW:
            raise ValidationError(
                "Por ahora solo se permite SHOW (simplificación inicial).")

    def __str__(self) -> str:
        return f"{self.rule} -> {self.block} ({self.mode})"
