import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_user_inventory_access"),
        ("masters", "0003_inventorycategory"),
    ]

    operations = [
        migrations.CreateModel(
            name="Staff",
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
                ("name", models.CharField(max_length=200)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("designation", models.CharField(blank=True, max_length=100)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="staff",
                        to="core.branch",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "staff",
                "ordering": ["name"],
            },
        ),
    ]
