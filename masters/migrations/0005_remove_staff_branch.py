from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0004_staff"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="staff",
            name="branch",
        ),
    ]
