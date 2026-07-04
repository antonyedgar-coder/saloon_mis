from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0003_dsr_format"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailysalesreport",
            name="card_payment",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="cash_payment",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="dailysalesreport",
            name="upi_payment",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
