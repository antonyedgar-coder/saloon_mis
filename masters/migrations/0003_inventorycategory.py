# Generated manually for InventoryCategory and Product.category → FK migration

from django.db import migrations, models
import django.db.models.deletion


def migrate_categories(apps, schema_editor):
    Product = apps.get_model("masters", "Product")
    InventoryCategory = apps.get_model("masters", "InventoryCategory")

    cache = {}
    for product in Product.objects.all():
        name = (product.category or "").strip() or "General"
        if name not in cache:
            cache[name], _ = InventoryCategory.objects.get_or_create(name=name)
        product.inventory_category = cache[name]
        product.save(update_fields=["inventory_category"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0002_expenseparticular"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name_plural": "inventory categories",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="inventory_category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="masters.inventorycategory",
            ),
        ),
        migrations.RunPython(migrate_categories, noop),
        migrations.AlterField(
            model_name="product",
            name="inventory_category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="masters.inventorycategory",
            ),
        ),
        migrations.RemoveField(
            model_name="product",
            name="category",
        ),
        migrations.AlterField(
            model_name="product",
            name="sku",
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
    ]
