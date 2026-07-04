from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Sum
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from core.mixins import LoginRequiredMixin, ModulePermissionMixin
from core.module_permissions import has_settings_access, user_can
from inventory.models import BranchOutward, Grn, OutwardInvoice, StockLedger

class SaloonLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True


class SaloonLogoutView(LogoutView):
    next_page = reverse_lazy("login")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        branch_filter = {}
        if not user.is_central():
            branch_filter["branch_id__in"] = user.branch_ids()

        ctx["pending_transfers"] = OutwardInvoice.objects.filter(
            status=OutwardInvoice.Status.DISPATCHED, **branch_filter
        ).count()
        ctx["posted_grns"] = Grn.objects.filter(status=Grn.Status.POSTED).count()

        from django.utils import timezone

        today = timezone.localdate()
        ctx["today_retail"] = (
            BranchOutward.objects.filter(
                type=BranchOutward.Type.RETAIL_SALE,
                date__date=today,
                **branch_filter,
            ).aggregate(total=Sum("lines__amount"))["total"]
            or 0
        )
        ctx["low_stock"] = []
        if user.is_central() or user.branch_ids():
            from masters.models import Product

            for product in Product.objects.filter(active=True):
                if user.is_central():
                    qty = StockLedger.balance(None, product.pk)
                else:
                    qty = sum(
                        StockLedger.balance(bid, product.pk) for bid in user.branch_ids()
                    )
                if product.reorder_level and qty <= product.reorder_level:
                    ctx["low_stock"].append({"product": product, "qty": qty})
        return ctx


class SettingsHubView(ModulePermissionMixin, View):
    module = "master_users"
    template_name = "core/settings.html"

    def test_func(self):
        return has_settings_access(self.request.user)

    def get(self, request):
        def item(title, desc, url, icon, module):
            if not user_can(request.user, module, "view"):
                return None
            return {"title": title, "desc": desc, "url": url, "icon": icon}

        inventory_masters = [
            x
            for x in [
                item(
                    "User Role",
                    "Users, roles, and module permissions",
                    "masters:users",
                    "users",
                    "master_users",
                ),
                item(
                    "Branch Master",
                    "Manage salon branch locations",
                    "masters:branches",
                    "branch",
                    "master_branches",
                ),
                item(
                    "Inventory Category",
                    "Categories for inventory items",
                    "masters:inventory_categories",
                    "category",
                    "master_categories",
                ),
                item(
                    "Inventory Name",
                    "Inventory items with category and unit",
                    "masters:products",
                    "inventory",
                    "master_products",
                ),
                item(
                    "Supplier Master",
                    "Suppliers for stock inward (GRN)",
                    "masters:suppliers",
                    "supplier",
                    "master_suppliers",
                ),
            ]
            if x
        ]
        expense_masters = [
            x
            for x in [
                item(
                    "Expenses Head",
                    "Expense heads for petty cash payments",
                    "masters:expenses",
                    "expense",
                    "master_expenses",
                ),
            ]
            if x
        ]
        dsr_masters = [
            x
            for x in [
                item(
                    "Staff Master",
                    "Salon staff — tracked across all branches for sales",
                    "masters:staff",
                    "staff",
                    "master_staff",
                ),
                item(
                    "Incentive Master",
                    "Incentive % and salary-times target for incentive reports",
                    "masters:incentive",
                    "incentive",
                    "master_incentive",
                ),
            ]
            if x
        ]
        return render(
            request,
            self.template_name,
            {
                "inventory_masters": inventory_masters,
                "expense_masters": expense_masters,
                "dsr_masters": dsr_masters,
            },
        )