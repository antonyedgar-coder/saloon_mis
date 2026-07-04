import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0005_remove_staff_branch"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="branchoutwardline",
            name="staff",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="retail_sales",
                to="masters.staff",
            ),
        ),
    ]
