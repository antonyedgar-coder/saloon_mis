import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0005_remove_staff_branch"),
        ("reports", "0002_pettycashtransaction_delete_pettycashentry"),
    ]

    operations = [
        migrations.RemoveField(model_name="dailysalesreport", name="card_sales"),
        migrations.RemoveField(model_name="dailysalesreport", name="cash_sales"),
        migrations.RemoveField(model_name="dailysalesreport", name="female_customers"),
        migrations.RemoveField(model_name="dailysalesreport", name="male_customers"),
        migrations.RemoveField(model_name="dailysalesreport", name="remarks"),
        migrations.RemoveField(model_name="dailysalesreport", name="retail_sales"),
        migrations.RemoveField(model_name="dailysalesreport", name="service_sales"),
        migrations.RemoveField(model_name="dailysalesreport", name="total_customers"),
        migrations.RemoveField(model_name="dailysalesreport", name="upi_sales"),
        migrations.AddField(
            model_name="dailysalesreport",
            name="bridal_advance",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="broadcast",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="calls_done",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="ear_piercing",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="female_income",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="female_walkins",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="google_appointment",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="google_reviews_request",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="gst",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="just_dial",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="kids_income",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="kids_walkins",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="male_income",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="male_walkins",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="membership_card",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="net_service_income",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="new_clients",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="other_income",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="product_sale_18",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="product_sale_5",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="status_story",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="zooty_appointment",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="DsrStaffLine",
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
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_lines",
                        to="reports.dailysalesreport",
                    ),
                ),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dsr_lines",
                        to="masters.staff",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
