from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from core.mixins import ModulePermissionMixin
from core.module_permissions import (
    MODULES,
    permissions_matrix_for_user,
    role_defaults_json,
    save_user_permissions,
)
from core.models import Branch, User

from .forms import (
    BranchForm,
    ExpenseParticularForm,
    InventoryCategoryForm,
    ProductForm,
    StaffForm,
    SupplierForm,
    UserForm,
)
from .models import (
    ExpenseParticular,
    IncentiveSettingsVersion,
    InventoryCategory,
    Product,
    Staff,
    Supplier,
)


def _handle_delete(request, obj, redirect_name):
    try:
        obj.delete()
        messages.success(request, "Deleted successfully.")
    except ProtectedError:
        messages.error(request, "Cannot delete — this record is used elsewhere.")
    return redirect(redirect_name)


class BranchListView(ModulePermissionMixin, View):
    module = "master_branches"
    template_name = "masters/branch_list.html"

    def get(self, request):
        edit_id = request.GET.get("edit")
        instance = Branch.objects.filter(pk=edit_id).first() if edit_id else None
        return render(
            request,
            self.template_name,
            {
                "branches": Branch.objects.all(),
                "form": BranchForm(instance=instance),
                "edit_obj": instance,
            },
        )

    def post(self, request):
        if request.POST.get("action") == "delete":
            obj = get_object_or_404(Branch, pk=request.POST.get("id"))
            return _handle_delete(request, obj, "masters:branches")

        edit_id = request.POST.get("edit_id")
        instance = Branch.objects.filter(pk=edit_id).first() if edit_id else None
        form = BranchForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated." if instance else "Added.")
            return redirect("masters:branches")
        return render(
            request,
            self.template_name,
            {"branches": Branch.objects.all(), "form": form, "edit_obj": instance},
        )


class ProductListView(ModulePermissionMixin, View):
    module = "master_products"
    template_name = "masters/product_list.html"

    def get(self, request):
        edit_id = request.GET.get("edit")
        instance = (
            Product.objects.select_related("inventory_category")
            .filter(pk=edit_id)
            .first()
            if edit_id
            else None
        )
        return render(
            request,
            self.template_name,
            {
                "products": Product.objects.select_related("inventory_category"),
                "categories": InventoryCategory.objects.filter(active=True),
                "form": ProductForm(instance=instance),
                "edit_obj": instance,
            },
        )

    def post(self, request):
        if request.POST.get("action") == "delete":
            obj = get_object_or_404(Product, pk=request.POST.get("id"))
            return _handle_delete(request, obj, "masters:products")

        edit_id = request.POST.get("edit_id")
        instance = Product.objects.filter(pk=edit_id).first() if edit_id else None
        form = ProductForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated." if instance else "Added.")
            return redirect("masters:products")
        return render(
            request,
            self.template_name,
            {
                "products": Product.objects.select_related("inventory_category"),
                "categories": InventoryCategory.objects.filter(active=True),
                "form": form,
                "edit_obj": instance,
            },
        )


class InventoryCategoryListView(ModulePermissionMixin, View):
    module = "master_categories"
    template_name = "masters/inventory_category_list.html"

    def get(self, request):
        edit_id = request.GET.get("edit")
        instance = InventoryCategory.objects.filter(pk=edit_id).first() if edit_id else None
        return render(
            request,
            self.template_name,
            {
                "categories": InventoryCategory.objects.all(),
                "form": InventoryCategoryForm(instance=instance),
                "edit_obj": instance,
            },
        )

    def post(self, request):
        if request.POST.get("action") == "delete":
            obj = get_object_or_404(InventoryCategory, pk=request.POST.get("id"))
            return _handle_delete(request, obj, "masters:inventory_categories")

        edit_id = request.POST.get("edit_id")
        instance = InventoryCategory.objects.filter(pk=edit_id).first() if edit_id else None
        form = InventoryCategoryForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated." if instance else "Added.")
            return redirect("masters:inventory_categories")
        return render(
            request,
            self.template_name,
            {
                "categories": InventoryCategory.objects.all(),
                "form": form,
                "edit_obj": instance,
            },
        )


class SupplierListView(ModulePermissionMixin, View):
    module = "master_suppliers"
    template_name = "masters/supplier_list.html"

    def get(self, request):
        edit_id = request.GET.get("edit")
        instance = Supplier.objects.filter(pk=edit_id).first() if edit_id else None
        return render(
            request,
            self.template_name,
            {
                "suppliers": Supplier.objects.all(),
                "form": SupplierForm(instance=instance),
                "edit_obj": instance,
            },
        )

    def post(self, request):
        if request.POST.get("action") == "delete":
            obj = get_object_or_404(Supplier, pk=request.POST.get("id"))
            return _handle_delete(request, obj, "masters:suppliers")

        edit_id = request.POST.get("edit_id")
        instance = Supplier.objects.filter(pk=edit_id).first() if edit_id else None
        form = SupplierForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated." if instance else "Added.")
            return redirect("masters:suppliers")
        return render(
            request,
            self.template_name,
            {"suppliers": Supplier.objects.all(), "form": form, "edit_obj": instance},
        )


class StaffListView(ModulePermissionMixin, View):
    module = "master_staff"
    template_name = "masters/staff_list.html"

    def get(self, request):
        edit_id = request.GET.get("edit")
        instance = Staff.objects.filter(pk=edit_id).first() if edit_id else None
        return render(
            request,
            self.template_name,
            {
                "staff_list": Staff.objects.all(),
                "form": StaffForm(instance=instance),
                "edit_obj": instance,
            },
        )

    def post(self, request):
        from masters.incentive_history import record_staff_salary_version

        if request.POST.get("action") == "delete":
            obj = get_object_or_404(Staff, pk=request.POST.get("id"))
            return _handle_delete(request, obj, "masters:staff")

        edit_id = request.POST.get("edit_id")
        instance = Staff.objects.filter(pk=edit_id).first() if edit_id else None
        form = StaffForm(request.POST, instance=instance)
        if form.is_valid():
            staff = form.save()
            record_staff_salary_version(staff, staff.salary)
            messages.success(request, "Updated." if instance else "Added.")
            return redirect("masters:staff")
        return render(
            request,
            self.template_name,
            {
                "staff_list": Staff.objects.all(),
                "form": form,
                "edit_obj": instance,
            },
        )


class IncentiveSettingsView(ModulePermissionMixin, View):
    module = "master_incentive"
    template_name = "masters/incentive_settings.html"

    def _context(self, effective_from=None):
        from django.utils import timezone

        from masters.incentive_master import PERIOD_LABELS, PERIOD_TYPES, profiles_for_template

        profiles, slabs = profiles_for_template()
        period_configs = [
            {
                "period_type": period_type,
                "label": PERIOD_LABELS[period_type],
                "profile": profiles[period_type],
                "slabs": slabs[period_type],
            }
            for period_type in PERIOD_TYPES
        ]
        versions = IncentiveSettingsVersion.objects.order_by(
            "-effective_from", "-pk", "period_type"
        )[:30]
        return {
            "period_configs": period_configs,
            "effective_from": effective_from or timezone.localdate().isoformat(),
            "versions": versions,
        }

    def get(self, request):
        return render(request, self.template_name, self._context())

    def post(self, request):
        from datetime import datetime

        from masters.incentive_history import record_all_period_versions
        from masters.incentive_master import parse_all_period_configs, save_period_profiles

        effective_from_raw = request.POST.get("effective_from")
        try:
            effective_from = datetime.strptime(effective_from_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            messages.error(request, "Enter a valid effective from date.")
            return render(request, self.template_name, self._context(effective_from_raw))

        all_configs = parse_all_period_configs(request.POST)
        save_period_profiles(all_configs)
        record_all_period_versions(all_configs, effective_from)
        messages.success(
            request,
            f"Incentive settings saved for Daily, Weekly, and Monthly from {effective_from}.",
        )
        return redirect("masters:incentive")


class UserListView(ModulePermissionMixin, View):
    module = "master_users"
    template_name = "masters/user_list.html"

    def get(self, request):
        edit_id = request.GET.get("edit")
        instance = (
            User.objects.filter(pk=edit_id)
            .prefetch_related("branches", "module_permissions")
            .first()
            if edit_id
            else None
        )
        form = UserForm(instance=instance) if instance else UserForm()
        return render(
            request,
            self.template_name,
            {
                "users": User.objects.prefetch_related("branches"),
                "form": form,
                "edit_obj": instance,
                "branches": Branch.objects.filter(active=True),
                "modules": MODULES,
                "perm_matrix": permissions_matrix_for_user(instance),
                "role_perm_defaults_json": role_defaults_json(),
            },
        )

    def post(self, request):
        if request.POST.get("action") == "delete":
            obj = get_object_or_404(User, pk=request.POST.get("id"))
            if obj.pk == request.user.pk:
                messages.error(request, "You cannot delete your own account.")
                return redirect("masters:users")
            return _handle_delete(request, obj, "masters:users")

        edit_id = request.POST.get("edit_id")
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "")
        role = request.POST.get("role")
        password = request.POST.get("password", "")
        branch_id = request.POST.get("branches")
        is_active = request.POST.get("is_active") == "on"

        if edit_id:
            user = get_object_or_404(User, pk=edit_id)
            user.username = username
            user.email = email
            user.role = role
            user.is_active = is_active
            if password:
                user.set_password(password)
            user.save()
            user.branches.clear()
            if branch_id:
                user.branches.add(branch_id)
            save_user_permissions(user, request.POST)
            messages.success(request, "User updated.")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password or "changeme123",
                role=role,
                is_active=is_active,
            )
            if branch_id:
                user.branches.add(branch_id)
            save_user_permissions(user, request.POST)
            messages.success(request, "User added.")
        return redirect("masters:users")


class ExpenseParticularListView(ModulePermissionMixin, View):
    module = "master_expenses"
    template_name = "masters/expense_list.html"

    def get(self, request):
        edit_id = request.GET.get("edit")
        instance = ExpenseParticular.objects.filter(pk=edit_id).first() if edit_id else None
        return render(
            request,
            self.template_name,
            {
                "expenses": ExpenseParticular.objects.all(),
                "form": ExpenseParticularForm(instance=instance),
                "edit_obj": instance,
            },
        )

    def post(self, request):
        if request.POST.get("action") == "delete":
            obj = get_object_or_404(ExpenseParticular, pk=request.POST.get("id"))
            return _handle_delete(request, obj, "masters:expenses")

        edit_id = request.POST.get("edit_id")
        instance = ExpenseParticular.objects.filter(pk=edit_id).first() if edit_id else None
        form = ExpenseParticularForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated." if instance else "Added.")
            return redirect("masters:expenses")
        return render(
            request,
            self.template_name,
            {
                "expenses": ExpenseParticular.objects.all(),
                "form": form,
                "edit_obj": instance,
            },
        )


class ProductBulkUploadView(ModulePermissionMixin, View):
    module = "master_products"
    template_name = "masters/product_bulk_upload.html"

    def get(self, request):
        from core.bulk_upload_utils import csv_template_response
        from masters.product_bulk_upload import PRODUCT_HEADERS

        if request.GET.get("template") == "1":
            return csv_template_response(
                "inventory_master_template.csv",
                PRODUCT_HEADERS,
                [["Sample Shampoo 100ml", "Retail Products"]],
            )
        return render(request, self.template_name)

    def post(self, request):
        from masters.product_bulk_upload import apply_product_upload, parse_product_upload

        uploaded = request.FILES.get("upload_file")
        if not uploaded:
            messages.error(request, "Choose a CSV or Excel file to upload.")
            return render(request, self.template_name)

        try:
            parsed_rows = parse_product_upload(uploaded)
            result = apply_product_upload(parsed_rows)
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name)

        messages.success(
            request,
            f"Upload complete. Created {result['created']}, updated {result['updated']}, "
            f"skipped {result['skipped']} (already matched).",
        )
        return redirect("masters:products")
