from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

from core.module_permissions import user_can
from .models import Role


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles: tuple[str, ...] = ()

    def test_func(self):
        return self.request.user.role in self.allowed_roles


class SuperAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Role.SUPER_ADMIN,)


class AccountsRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Role.SUPER_ADMIN, Role.ACCOUNTS)


class BranchManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Role.SUPER_ADMIN, Role.BRANCH_MANAGER)


class ReportsRequiredMixin(RoleRequiredMixin):
    allowed_roles = (
        Role.SUPER_ADMIN,
        Role.ACCOUNTS,
        Role.BRANCH_MANAGER,
        Role.AUDITOR,
    )


class ModulePermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require module permission. GET uses view; POST uses create or edit."""

    module = None
    # Optional override: "view", "create", "edit", "delete"
    required_action = None

    def get_required_action(self):
        if self.required_action:
            return self.required_action
        if self.request.method in ("POST", "PUT", "PATCH"):
            return "write"
        if self.request.method == "DELETE":
            return "delete"
        return "view"

    def test_func(self):
        user = self.request.user
        if not self.module:
            return False
        if (
            self.request.method == "POST"
            and self.request.POST.get("action") == "delete"
        ):
            return user_can(user, self.module, "delete")
        action = self.get_required_action()
        if action == "write":
            return user_can(user, self.module, "create") or user_can(
                user, self.module, "edit"
            )
        return user_can(user, self.module, action)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission for this action.")
            return redirect("dashboard")
        return super().handle_no_permission()
