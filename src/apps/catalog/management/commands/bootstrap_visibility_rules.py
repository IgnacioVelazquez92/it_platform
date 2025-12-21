# src/apps/catalog/management/commands/bootstrap_visibility_rules.py
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models.rules import (
    PermissionBlock,
    BlockKind,
    ScopedEntity,
    GlobalEntity,
    PermissionVisibilityRule,
    PermissionVisibilityRuleBlock,
    RuleBlockMode,
)


class Command(BaseCommand):
    """
    Bootstrap inicial del motor de reglas.

    Objetivo (modo incremental):
    - Crear bloques base (scoped + global) para armar la UI.
    - Crear UNA regla base SIN triggers ("siempre matchea") que muestre TODO.
    - Luego, el usuario puede desactivar bloques o crear reglas específicas por módulo.
    """

    help = "Crea bloques y una regla base para mostrar todo (modo incremental)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra la regla base y recrea sus relaciones a bloques (no borra los bloques).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset: bool = options["reset"]

        # -------------------------------------------------
        # 1) Definición de bloques estándar (idempotente)
        # -------------------------------------------------
        # Nota: Company/Branch normalmente se eligen siempre, pero los dejamos como bloque
        # por si más adelante querés gobernarlos también por reglas.
        block_specs = [
            # Scoped
            dict(code="scoped_company", name="Empresa", kind=BlockKind.SCOPED,
                 scoped_entity=ScopedEntity.COMPANY, order=10),
            dict(code="scoped_branch", name="Sucursal", kind=BlockKind.SCOPED,
                 scoped_entity=ScopedEntity.BRANCH, order=20),
            dict(code="scoped_warehouse", name="Depósitos", kind=BlockKind.SCOPED,
                 scoped_entity=ScopedEntity.WAREHOUSE, order=30),
            dict(code="scoped_cash_register", name="Cajas", kind=BlockKind.SCOPED,
                 scoped_entity=ScopedEntity.CASH_REGISTER, order=40),
            dict(code="scoped_control_panel", name="Paneles de control",
                 kind=BlockKind.SCOPED, scoped_entity=ScopedEntity.CONTROL_PANEL, order=50),
            dict(code="scoped_seller", name="Vendedores", kind=BlockKind.SCOPED,
                 scoped_entity=ScopedEntity.SELLER, order=60),

            # Global
            dict(code="global_actions_all", name="Acciones (todas)", kind=BlockKind.GLOBAL,
                 global_entity=GlobalEntity.ACTION, action_group=None, order=110),
            dict(code="global_matrix", name="Matriz", kind=BlockKind.GLOBAL,
                 global_entity=GlobalEntity.MATRIX, order=120),
            dict(code="global_payment_methods", name="Medios de pago",
                 kind=BlockKind.GLOBAL, global_entity=GlobalEntity.PAYMENT_METHOD, order=130),
        ]

        blocks_by_code: dict[str, PermissionBlock] = {}

        for spec in block_specs:
            code = spec.pop("code")
            defaults = {
                "name": spec.get("name"),
                "kind": spec.get("kind"),
                "scoped_entity": spec.get("scoped_entity"),
                "global_entity": spec.get("global_entity"),
                "action_group": spec.get("action_group"),
                "order": spec.get("order", 0),
                "is_active": True,
            }

            obj, created = PermissionBlock.objects.get_or_create(
                code=code, defaults=defaults)

            # Si existe, lo mantenemos sincronizado con el bootstrap (sin tocar is_active si el usuario lo apagó)
            updates = {}
            for k, v in defaults.items():
                if k == "is_active":
                    continue
                if getattr(obj, k) != v:
                    updates[k] = v
            if updates:
                for k, v in updates.items():
                    setattr(obj, k, v)
                obj.save(update_fields=list(updates.keys()))

            blocks_by_code[code] = obj

        # -------------------------------------------------
        # 2) Regla base (siempre matchea)
        # -------------------------------------------------
        rule_name = "Base — Mostrar todo"
        rule, _ = PermissionVisibilityRule.objects.get_or_create(
            name=rule_name,
            defaults={
                "is_active": True,
                "priority": 0,
                "notes": "Bootstrap inicial: muestra todos los bloques. Luego se segrega por módulo.",
            },
        )

        if reset:
            PermissionVisibilityRuleBlock.objects.filter(rule=rule).delete()

        # -------------------------------------------------
        # 3) Vincular regla -> todos los bloques (SHOW)
        # -------------------------------------------------
        created_links = 0
        for code, block in blocks_by_code.items():
            _, created = PermissionVisibilityRuleBlock.objects.get_or_create(
                rule=rule,
                block=block,
                defaults={"mode": RuleBlockMode.SHOW, "order": block.order},
            )
            created_links += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                "OK. "
                f"Bloques total: {len(blocks_by_code)} | "
                f"Regla: '{rule.name}' | "
                f"Vínculos creados: {created_links}"
            )
        )
