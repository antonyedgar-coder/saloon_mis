from datetime import date

from django.db import migrations


def seed_history(apps, schema_editor):
    Staff = apps.get_model("masters", "Staff")
    StaffSalaryVersion = apps.get_model("masters", "StaffSalaryVersion")
    IncentiveSettings = apps.get_model("masters", "IncentiveSettings")
    IncentiveSettingsVersion = apps.get_model("masters", "IncentiveSettingsVersion")

    earliest = date(2000, 1, 1)

    for staff in Staff.objects.all():
        if not StaffSalaryVersion.objects.filter(staff=staff).exists():
            StaffSalaryVersion.objects.create(
                staff=staff,
                salary=staff.salary,
                effective_from=earliest,
            )

    settings = IncentiveSettings.objects.first()
    if settings and not IncentiveSettingsVersion.objects.exists():
        IncentiveSettingsVersion.objects.create(
            incentive_percent=settings.incentive_percent,
            salary_times=settings.salary_times,
            effective_from=earliest,
        )


def unseed_history(apps, schema_editor):
    StaffSalaryVersion = apps.get_model("masters", "StaffSalaryVersion")
    IncentiveSettingsVersion = apps.get_model("masters", "IncentiveSettingsVersion")
    StaffSalaryVersion.objects.filter(effective_from=date(2000, 1, 1)).delete()
    IncentiveSettingsVersion.objects.filter(effective_from=date(2000, 1, 1)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("masters", "0008_incentive_history"),
    ]

    operations = [
        migrations.RunPython(seed_history, unseed_history),
    ]
