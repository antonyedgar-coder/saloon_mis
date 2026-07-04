from core.models import Role

INVENTORY_FIELDS = (
    "inv_grn",
    "inv_outward",
    "inv_receive",
    "inv_branch_outward",
    "inv_stock",
)

ROLE_INVENTORY_DEFAULTS = {
    Role.SUPER_ADMIN: {
        "inv_grn": True,
        "inv_outward": True,
        "inv_receive": True,
        "inv_branch_outward": True,
        "inv_stock": True,
    },
    Role.ACCOUNTS: {
        "inv_grn": True,
        "inv_outward": True,
        "inv_receive": False,
        "inv_branch_outward": False,
        "inv_stock": True,
    },
    Role.BRANCH_MANAGER: {
        "inv_grn": False,
        "inv_outward": False,
        "inv_receive": True,
        "inv_branch_outward": True,
        "inv_stock": True,
    },
    Role.BRANCH_STAFF: {
        "inv_grn": False,
        "inv_outward": False,
        "inv_receive": True,
        "inv_branch_outward": True,
        "inv_stock": True,
    },
    Role.AUDITOR: {
        "inv_grn": True,
        "inv_outward": True,
        "inv_receive": True,
        "inv_branch_outward": True,
        "inv_stock": True,
    },
}


def inventory_defaults_for_role(role):
    key = role if isinstance(role, str) else role
    for r, perms in ROLE_INVENTORY_DEFAULTS.items():
        if r == key or r.value == key:
            return dict(perms)
    return dict(ROLE_INVENTORY_DEFAULTS[Role.BRANCH_STAFF])


def apply_inventory_defaults(user):
    defaults = inventory_defaults_for_role(user.role)
    for field, value in defaults.items():
        setattr(user, field, value)
