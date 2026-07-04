from django.core.management.base import BaseCommand

from core.models import Branch, Role, User
from masters.models import ExpenseParticular, InventoryCategory, Product, ProductType, Supplier


class Command(BaseCommand):
    help = "Seed demo data for Salon MIS"

    def handle(self, *args, **options):
        Branch.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Product.objects.all().delete()
        InventoryCategory.objects.all().delete()
        Supplier.objects.all().delete()
        ExpenseParticular.objects.all().delete()

        branch1 = Branch.objects.create(name="Main Branch", address="City Centre")
        branch2 = Branch.objects.create(name="North Branch", address="North Zone")

        Supplier.objects.create(
            name="Beauty Supplies Co.",
            gstin="29AAAAA0000A1Z5",
            phone="9876543210",
        )

        hair = InventoryCategory.objects.create(name="Hair Care")
        skin = InventoryCategory.objects.create(name="Skin Care")
        consumables = InventoryCategory.objects.create(name="Consumables")

        for p in [
            Product(
                name="Professional Shampoo 500ml",
                inventory_category=hair,
                unit="pcs",
                product_type=ProductType.BOTH,
                purchase_rate=250,
                selling_price=450,
                reorder_level=10,
            ),
            Product(
                name="Face Cream 100g",
                inventory_category=skin,
                unit="pcs",
                product_type=ProductType.RETAIL,
                purchase_rate=180,
                selling_price=350,
                reorder_level=15,
            ),
            Product(
                name="Salon Towel",
                inventory_category=consumables,
                unit="pcs",
                product_type=ProductType.CONSUMPTION,
                purchase_rate=80,
                selling_price=0,
                reorder_level=20,
            ),
        ]:
            p.save()

        ExpenseParticular.objects.bulk_create([
            ExpenseParticular(name="Tea & Snacks"),
            ExpenseParticular(name="Auto / Taxi Fare"),
            ExpenseParticular(name="Cleaning Materials"),
            ExpenseParticular(name="Minor Repairs"),
            ExpenseParticular(name="Stationery"),
        ])

        User.objects.create_user(
            username="admin",
            email="admin@salonmis.local",
            password="admin123",
            role=Role.SUPER_ADMIN,
            is_staff=True,
        )
        User.objects.create_user(
            username="accounts",
            email="accounts@salonmis.local",
            password="accounts123",
            role=Role.ACCOUNTS,
        )
        manager = User.objects.create_user(
            username="manager",
            email="manager@salonmis.local",
            password="manager123",
            role=Role.BRANCH_MANAGER,
        )
        manager.branches.add(branch1)

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("admin / admin123 (Super Admin)")
        self.stdout.write("accounts / accounts123 (Accounts)")
        self.stdout.write("manager / manager123 (Branch Manager — Main Branch)")
