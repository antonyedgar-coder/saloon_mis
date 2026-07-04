from core.models import Role

# module_key -> label
MODULES = (
    ("dsr", "Daily Sales Report"),
    ("petty_cash", "Petty Cash"),
    ("inv_grn", "GRN (Stock Inward)"),
    ("inv_outward", "Outward Register"),
    ("inv_receive", "Receive Stock"),
    ("inv_branch_outward", "Branch Outward"),
    ("inv_stock", "Stock Balance"),
    ("report_sales", "Sales Report"),
    ("report_staff_performance", "Staff Performance Report"),
    ("report_incentive", "Incentive Report"),
    ("report_inventory", "Inventory Reports"),
    ("master_users", "User Role"),
    ("master_branches", "Branch Master"),
    ("master_categories", "Inventory Category"),
    ("master_products", "Inventory Name"),
    ("master_suppliers", "Supplier Master"),
    ("master_expenses", "Expenses Head"),
    ("master_staff", "Staff Master"),
    ("master_incentive", "Incentive Master"),
)

ACTIONS = ("view", "create", "edit", "delete")


def _all(v=True):
    return {"view": v, "create": v, "edit": v, "delete": v}


def _view_only():
    return {"view": True, "create": False, "edit": False, "delete": False}


def _none():
    return _all(False)


# Role defaults applied when creating a user (can be overridden per user)
ROLE_MODULE_DEFAULTS = {
    Role.SUPER_ADMIN: {key: _all(True) for key, _ in MODULES},
    Role.ACCOUNTS: {
        "dsr": _view_only(),
        "petty_cash": _all(True),
        "inv_grn": _all(True),
        "inv_outward": _all(True),
        "inv_receive": _view_only(),
        "inv_branch_outward": _view_only(),
        "inv_stock": _view_only(),
        "report_sales": _view_only(),
        "report_staff_performance": _view_only(),
        "report_incentive": _view_only(),
        "report_inventory": _view_only(),
        "master_users": _none(),
        "master_branches": _view_only(),
        "master_categories": _all(True),
        "master_products": _all(True),
        "master_suppliers": _all(True),
        "master_expenses": _all(True),
        "master_staff": _view_only(),
        "master_incentive": _view_only(),
    },
    Role.BRANCH_MANAGER: {
        "dsr": _all(True),
        "petty_cash": _all(True),
        "inv_grn": _none(),
        "inv_outward": _none(),
        "inv_receive": _all(True),
        "inv_branch_outward": _all(True),
        "inv_stock": _view_only(),
        "report_sales": _view_only(),
        "report_staff_performance": _view_only(),
        "report_incentive": _view_only(),
        "report_inventory": _view_only(),
        "master_users": _none(),
        "master_branches": _none(),
        "master_categories": _none(),
        "master_products": _none(),
        "master_suppliers": _none(),
        "master_expenses": _none(),
        "master_staff": _none(),
        "master_incentive": _none(),
    },
    Role.BRANCH_STAFF: {
        "dsr": {"view": True, "create": True, "edit": True, "delete": False},
        "petty_cash": {"view": True, "create": True, "edit": False, "delete": False},
        "inv_grn": _none(),
        "inv_outward": _none(),
        "inv_receive": {"view": True, "create": True, "edit": False, "delete": False},
        "inv_branch_outward": {"view": True, "create": True, "edit": False, "delete": False},
        "inv_stock": _view_only(),
        "report_sales": _none(),
        "report_staff_performance": _none(),
        "report_incentive": _none(),
        "report_inventory": _none(),
        "master_users": _none(),
        "master_branches": _none(),
        "master_categories": _none(),
        "master_products": _none(),
        "master_suppliers": _none(),
        "master_expenses": _none(),
        "master_staff": _none(),
        "master_incentive": _none(),
    },
    Role.AUDITOR: {
        **{key: _view_only() for key, _ in MODULES},
        "master_users": _none(),
    },
}


def defaults_for_role(role):
    base = {key: _none() for key, _ in MODULES}
    base.update(ROLE_MODULE_DEFAULTS.get(role, {}))
    return base


def permissions_matrix_for_user(user):
    """Return {module: {view, create, edit, delete}} for form display."""
    if user is None:
        return defaults_for_role(Role.BRANCH_STAFF)
    if user.role == Role.SUPER_ADMIN:
        return {key: _all(True) for key, _ in MODULES}

    matrix = defaults_for_role(user.role)
    for perm in user.module_permissions.all():
        matrix[perm.module] = {
            "view": perm.can_view,
            "create": perm.can_create,
            "edit": perm.can_edit,
            "delete": perm.can_delete,
        }
    return matrix


def user_can(user, module, action="view"):
    """Check whether user may perform action on module."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "role", None) == Role.SUPER_ADMIN:
        return True
    if action not in ACTIONS:
        return False

    perm = user.module_permissions.filter(module=module).first()
    if perm is not None:
        return bool(getattr(perm, f"can_{action}", False))

    # Fall back to role defaults (and legacy inventory flags for inv_* modules)
    defaults = defaults_for_role(user.role).get(module, _none())
    allowed = bool(defaults.get(action, False))

    # Bridge existing inventory checkboxes until fully migrated
    inv_map = {
        "inv_grn": "inv_grn",
        "inv_outward": "inv_outward",
        "inv_receive": "inv_receive",
        "inv_branch_outward": "inv_branch_outward",
        "inv_stock": "inv_stock",
    }
    if module in inv_map and hasattr(user, inv_map[module]):
        if not getattr(user, inv_map[module]):
            return False
        if action == "view":
            return True
        # If they have inv access flag, allow create/edit unless role default says no
        return allowed or action in ("create", "edit")

    return allowed


def save_user_permissions(user, post_data):
    """Read perm_<module>_<action> checkboxes from POST and save."""
    from core.models import UserModulePermission

    if user.role == Role.SUPER_ADMIN:
        user.module_permissions.all().delete()
        return

    for module_key, _label in MODULES:
        defaults = {
            "can_view": post_data.get(f"perm_{module_key}_view") == "on",
            "can_create": post_data.get(f"perm_{module_key}_create") == "on",
            "can_edit": post_data.get(f"perm_{module_key}_edit") == "on",
            "can_delete": post_data.get(f"perm_{module_key}_delete") == "on",
        }
        # View is required if any write permission is set
        if defaults["can_create"] or defaults["can_edit"] or defaults["can_delete"]:
            defaults["can_view"] = True
        UserModulePermission.objects.update_or_create(
            user=user,
            module=module_key,
            defaults=defaults,
        )

    # Keep legacy inventory flags in sync for older checks
    user.inv_grn = user_can(user, "inv_grn", "view")
    user.inv_outward = user_can(user, "inv_outward", "view")
    user.inv_receive = user_can(user, "inv_receive", "view")
    user.inv_branch_outward = user_can(user, "inv_branch_outward", "view")
    user.inv_stock = user_can(user, "inv_stock", "view")
    user.save(
        update_fields=[
            "inv_grn",
            "inv_outward",
            "inv_receive",
            "inv_branch_outward",
            "inv_stock",
        ]
    )


def role_defaults_json():
    import json

    return json.dumps(
        {role.value: defaults_for_role(role) for role in Role}
    )


MASTER_MODULES = [key for key, _ in MODULES if key.startswith("master_")]
REPORT_MODULES = [key for key, _ in MODULES if key.startswith("report_")]
INVENTORY_MODULES = [key for key, _ in MODULES if key.startswith("inv_")]


def has_any_module_view(user, module_keys):
    return any(user_can(user, key, "view") for key in module_keys)


def has_settings_access(user):
    return user_can(user, "master_users", "view") or has_any_module_view(
        user, MASTER_MODULES
    )


def has_reports_access(user):
    return has_any_module_view(user, REPORT_MODULES)


def has_inventory_access(user):
    if getattr(user, "role", None) == Role.SUPER_ADMIN:
        return True
    return has_any_module_view(user, INVENTORY_MODULES) or user.has_any_inventory_access()
