from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Set

from apps.catalog.models.rules import (
    BlockKind,
    GlobalEntity,
    PermissionBlock,
)

from apps.catalog.models.selections import PermissionSelectionSet


@dataclass(frozen=True)
class VisibleBlocks:
    """
    Resultado mínimo para que la UI (y luego los forms) decidan qué mostrar.

    En esta fase:
    - devolvemos "todo visible" (modo incremental)
    - dejamos la estructura lista para integrar reglas reales
    """
    block_codes: Set[str]

    def has(self, code: str) -> bool:
        return code in self.block_codes

    def allow_global_entity(self, entity: str) -> bool:
        """
        Helper para UI: ej entity = GlobalEntity.ACTION, MATRIX, PAYMENT_METHOD.
        """
        # Esta implementación es deliberadamente simple: si existe algún bloque
        # para esa entity dentro de los visibles -> permitido.
        return True


def resolve_visible_blocks(
    *,
    selection_set: PermissionSelectionSet,
) -> VisibleBlocks:
    """
    Resolver bloques visibles según selection_set.

    Fase actual (modo incremental):
    - Devuelve TODOS los bloques activos.

    Fase futura:
    - evaluar PermissionVisibilityRule + triggers (module/level/sublevel)
    - mapear a PermissionVisibilityRuleBlock (SHOW)
    - contemplar prioridad y match_mode
    """
    codes = set(
        PermissionBlock.objects.filter(is_active=True)
        .values_list("code", flat=True)
    )
    return VisibleBlocks(block_codes=codes)


def filter_action_groups_for_visible_blocks(*, blocks: VisibleBlocks) -> Optional[Set[str]]:
    """
    Para GLOBAL/ACTION: si en el futuro activamos reglas por action_group,
    este helper devolverá el conjunto permitido.

    En fase actual:
    - None significa "no filtrar"
    """
    return None
