from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

from core.module_permissions import user_can
from core.models import Role


class _InvModuleMixin(LoginRequiredMixin, UserPassesTestMixin):
    module = None

    def test_func(self):
        user = self.request.user
        if user.is_superuser or user.role == Role.SUPER_ADMIN:
            return True
        action = "view"
        if self.request.method in ("POST", "PUT", "PATCH"):
            return user_can(user, self.module, "create") or user_can(
                user, self.module, "edit"
            )
        if self.request.method == "DELETE":
            action = "delete"
        return user_can(user, self.module, action)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission for this action.")
            return redirect("dashboard")
        return super().handle_no_permission()


class InvGrnRequiredMixin(_InvModuleMixin):
    module = "inv_grn"


class InvOutwardRequiredMixin(_InvModuleMixin):
    module = "inv_outward"


class InvReceiveRequiredMixin(_InvModuleMixin):
    module = "inv_receive"


class InvBranchOutwardRequiredMixin(_InvModuleMixin):
    module = "inv_branch_outward"


class InvStockRequiredMixin(_InvModuleMixin):
    module = "inv_stock"
