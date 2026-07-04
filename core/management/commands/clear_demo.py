from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import Role, User
from masters.models import ExpenseParticular, InventoryCategory, Product, Supplier


DEMO_USERNAMES = ("admin", "accounts", "manager")
OWNER_IDENTIFIERS = (
    "antonyedgar@antonyandco.com",
)


class Command(BaseCommand):
    help = (
        "Remove demo users and seed particulars/masters, "
        "and promote the owner account to Super Admin."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner",
            default="antonyedgar@antonyandco.com",
            help="Username or email to promote to Super Admin",
        )

    def handle(self, *args, **options):
        owner_id = options["owner"].strip()

        # Remove demo accounts first
        demo_users = User.objects.filter(
            Q(username__in=DEMO_USERNAMES)
            | Q(email__iendswith="@salonmis.local")
            | Q(email__iendswith="@saloonmis.local")
        )
        deleted_users = list(demo_users.values_list("username", flat=True))
        demo_users.delete()

        # Promote owner (by username or email) to full Super Admin
        owner = (
            User.objects.filter(Q(username__iexact=owner_id) | Q(email__iexact=owner_id))
            .order_by("pk")
            .first()
        )
        if owner:
            owner.role = Role.SUPER_ADMIN
            owner.is_superuser = True
            owner.is_staff = True
            owner.is_active = True
            owner.inv_grn = True
            owner.inv_outward = True
            owner.inv_receive = True
            owner.inv_branch_outward = True
            owner.inv_stock = True
            owner.save()
            owner.module_permissions.all().delete()
            owner.branches.clear()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Promoted {owner.username} ({owner.email}) to Super Admin."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Owner account '{owner_id}' not found. "
                    "Create it with: python manage.py createsuperuser"
                )
            )

        # Also promote any other Django superusers
        for user in User.objects.filter(is_superuser=True).exclude(
            Q(username__iexact=owner_id) | Q(email__iexact=owner_id)
        ):
            user.role = Role.SUPER_ADMIN
            user.is_staff = True
            user.inv_grn = True
            user.inv_outward = True
            user.inv_receive = True
            user.inv_branch_outward = True
            user.inv_stock = True
            user.save()
            user.module_permissions.all().delete()

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
