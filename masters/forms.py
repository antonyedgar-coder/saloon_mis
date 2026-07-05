from django import forms

from core.models import Branch, User

from .models import (
    ExpenseParticular,
    IncentiveSettings,
    InventoryCategory,
    Product,
    Staff,
    Supplier,
)


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["name", "address", "active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "address": forms.TextInput(attrs={"class": "input"}),
            "active": forms.CheckboxInput(),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "inventory_category", "unit"]


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ["name", "active"]


class ExpenseParticularForm(forms.ModelForm):
    class Meta:
        model = ExpenseParticular
        fields = ["name", "active"]


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ["name", "phone", "designation", "salary", "active"]


class IncentiveSettingsForm(forms.ModelForm):
    effective_from = forms.DateField(
        required=True,
        label="Effective from",
        help_text="Changes apply from this date. Earlier periods keep the previous rules.",
    )

    class Meta:
        model = IncentiveSettings
        fields = [
            "incentive_percent",
            "salary_times",
            "makeup_percent",
            "google_review_with_photo_incentive",
            "google_review_without_photo_incentive",
            "ear_piercing_incentive",
            "watts_incentive",
            "membership_card_incentive",
            "ot_incentive",
        ]
        labels = {
            "incentive_percent": "Incentive %",
            "salary_times": "No. of times of salary as target",
            "makeup_percent": "Make-up incentive (%)",
            "google_review_with_photo_incentive": "Google review with photo (₹ per review)",
            "google_review_without_photo_incentive": "Google review without photo (₹ per review)",
            "ear_piercing_incentive": "Ear piercing (₹ per unit)",
            "watts_incentive": "Watts (₹ per unit)",
            "membership_card_incentive": "Membership card (₹ per unit)",
            "ot_incentive": "OT (₹ per unit)",
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "gstin", "phone", "email", "address", "active"]


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to keep current password when editing.",
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "role", "branches", "is_active"]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        elif not user.pk:
            user.set_password("changeme123")
        if commit:
            user.save()
            self.save_m2m()
        return user
