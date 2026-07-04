from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ACCOUNTS = "ACCOUNTS", "Accounts"
    BRANCH_MANAGER = "BRANCH_MANAGER", "Branch Manager"
    BRANCH_STAFF = "BRANCH_STAFF", "Branch Staff"
    AUDITOR = "AUDITOR", "Auditor"


CENTRAL_ROLES = {Role.SUPER_ADMIN, Role.ACCOUNTS, Role.AUDITOR}


class Branch(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BRANCH_STAFF)
    branches = models.ManyToManyField(Branch, blank=True, related_name="users")

    def is_central(self):
        return self.role in CENTRAL_ROLES

    def can_access_branch(self, branch_id):
        if self.is_central():
            return True
        return self.branches.filter(pk=branch_id).exists()

    def branch_ids(self):
        return list(self.branches.values_list("pk", flat=True))

    @property
    def is_central_user(self):
        return self.is_central()

    inv_grn = models.BooleanField(default=False)
    inv_outward = models.BooleanField(default=False)
    inv_receive = models.BooleanField(default=False)
    inv_branch_outward = models.BooleanField(default=False)
    inv_stock = models.BooleanField(default=True)

    def has_any_inventory_access(self):
        if self.role == Role.SUPER_ADMIN:
            return True
        return self.inv_grn or self.inv_outward or self.inv_receive or self.inv_branch_outward or self.inv_stock

    def can(self, module, action="view"):
        from core.module_permissions import user_can

        return user_can(self, module, action)

    @property
    def nav_access(self):
        from core.module_permissions import (
            has_inventory_access,
            has_reports_access,
            has_settings_access,
            user_can,
        )

        return {
            "dsr": user_can(self, "dsr", "view"),
            "petty_cash": user_can(self, "petty_cash", "view"),
            "inventory": has_inventory_access(self),
            "reports": has_reports_access(self),
            "settings": has_settings_access(self),
        }


class UserModulePermission(models.Model):
    """Per-user module access: view / create / edit / delete."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="module_permissions"
    )
    module = models.CharField(max_length=40)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = [("user", "module")]
        ordering = ["module"]

    def __str__(self):
        return f"{self.user.username}: {self.module}"


class DocumentSequence(models.Model):
    prefix = models.CharField(max_length=50, unique=True)
    last = models.PositiveIntegerField(default=0)

    @classmethod
    def next_number(cls, prefix: str) -> str:
        from django.utils import timezone

        year = timezone.now().year
        key = f"{prefix}-{year}"
        seq, _ = cls.objects.get_or_create(prefix=key, defaults={"last": 0})
        seq.last += 1
        seq.save(update_fields=["last"])
        return f"{prefix}/{year}/{seq.last:04d}"
