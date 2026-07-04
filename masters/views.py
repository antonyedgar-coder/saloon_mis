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
    IncentiveSettingsForm,
    InventoryCategoryForm,
    ProductForm,
    StaffForm,
    SupplierForm,
    UserForm,
)
from .models import (
    ExpenseParticular,
    IncentiveSettings,
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

    def get(self, request):
        from django.utils import timezone

        settings_obj = IncentiveSettings.get_solo()
        form = IncentiveSettingsForm(
            instance=settings_obj,
            initial={"effective_from": timezone.localdate()},
        )
        versions = IncentiveSettingsVersion.objects.order_by("-effective_from", "-pk")[:20]
        return render(
            request,
            self.template_name,
            {"form": form, "versions": versions},
        )

    def post(self, request):
        from masters.incentive_history import record_incentive_settings_version

        settings_obj = IncentiveSettings.get_solo()
        form = IncentiveSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            settings_obj = form.save()
            record_incentive_settings_version(
                settings_obj.incentive_percent,
                settings_obj.salary_times,
                form.cleaned_data["effective_from"],
            )
            messages.success(
                request,
                f"Incentive settings saved from {form.cleaned_data['effective_from']}.",
            )
            return redirect("masters:incentive")
        versions = IncentiveSettingsVersion.objects.order_by("-effective_from", "-pk")[:20]
        return render(
            request,
            self.template_name,
            {"form": form, "versions": versions},
        )


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
