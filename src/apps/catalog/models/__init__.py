from .modules import (
    ErpModule,
    ErpModuleLevel,
    ErpModuleSubLevel,
)

from .person import RequestPersonData

from .permissions.scoped import (
    Company,
    Branch,
    Warehouse,
    CashRegister,
    ControlPanel,
    Seller,
)

from .permissions.global_ops import (
    ActionPermission,
    MatrixPermission,
    PaymentMethodPermission,
)

from .rules import (
    PermissionBlock,
    PermissionVisibilityRule,
    PermissionVisibilityTrigger,
    PermissionVisibilityRuleBlock,
)

from .selections import (
    PermissionSelectionSet,
    SelectionSetModule,
    SelectionSetWarehouse,
    SelectionSetCashRegister,
    SelectionSetControlPanel,
    SelectionSetSeller,
    SelectionSetActionValue,
    SelectionSetPaymentMethod,
)

from .requests import AccessRequest, AccessRequestItem

from .templates import AccessTemplate


__all__ = [
    # modules
    "ErpModule",
    "ErpModuleLevel",
    "ErpModuleSubLevel",

    # person
    "RequestPersonData",

    # scoped catalogs
    "Company",
    "Branch",
    "Warehouse",
    "CashRegister",
    "ControlPanel",
    "Seller",

    # global catalogs
    "ActionPermission",
    "MatrixPermission",
    "PaymentMethodPermission",

    # rules engine
    "PermissionBlock",
    "PermissionVisibilityRule",
    "PermissionVisibilityTrigger",
    "PermissionVisibilityRuleBlock",

    # selections (payload reusable)
    "PermissionSelectionSet",
    "SelectionSetModule",
    "SelectionSetWarehouse",
    "SelectionSetCashRegister",
    "SelectionSetControlPanel",
    "SelectionSetSeller",
    "SelectionSetActionValue",
    "SelectionSetPaymentMethod",

    # business objects
    "AccessRequest",
    "AccessRequestItem",
    "AccessTemplate",
]
