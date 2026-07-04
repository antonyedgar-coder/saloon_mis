from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import Role, User
from masters.models import ExpenseParticular, InventoryCategory, Product, Supplier


DEMO_USERNAMES = ("admin", "accounts", "manager")


class Command(BaseCommand):
    help = (
        "Remove demo users and seed particulars/masters, "
        "and promote Django superusers to Super Admin role."
    )

    def handle(self, *args, **options):
        # Promote real superusers so Settings and full access work
        promoted = User.objects.filter(is_superuser=True).exclude(role=Role.SUPER_ADMIN)
        count_promoted = promoted.count()
        promoted.update(
            role=Role.SUPER_ADMIN,
            is_staff=True,
            inv_grn=True,
            inv_outward=True,
            inv_receive=True,
            inv_branch_outward=True,
            inv_stock=True,
        )
        for user in User.objects.filter(is_superuser=True):
            user.module_permissions.all().delete()

        # Remove demo accounts
        demo_users = User.objects.filter(
            Q(username__in=DEMO_USERNAMES)
            | Q(email__iendswith="@salonmis.local")
            | Q(email__iendswith="@saloonmis.local")
        )
        deleted_users = list(demo_users.values_list("username", flat=True))
        demo_users.delete()

        # Remove seed expense particulars and other demo masters
        particulars_deleted, _ = ExpenseParticular.objects.all().delete()

        products_deleted = 0
        categories_deleted = 0
        suppliers_deleted = 0
        for label, model in (
            ("products", Product),
            ("categories", InventoryCategory),
            ("suppliers", Supplier),
        ):
            try:
                deleted, _ = model.objects.all().delete()
                if label == "products":
                    products_deleted = deleted
                elif label == "categories":
                    categories_deleted = deleted
                else:
                    suppliers_deleted = deleted
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(f"Could not remove all {label}: {exc}")
                )

        self.stdout.write(self.style.SUCCESS("Demo data cleared."))
        if deleted_users:
            self.stdout.write(f"Removed users: {', '.join(deleted_users)}")
        else:
            self.stdout.write("No demo users found.")
        self.stdout.write(f"Removed expense particulars: {particulars_deleted}")
        self.stdout.write(f"Removed products: {products_deleted}")
        self.stdout.write(f"Removed categories: {categories_deleted}")
        self.stdout.write(f"Removed suppliers: {suppliers_deleted}")
        self.stdout.write(f"Promoted superusers to Super Admin: {count_promoted}")

