from django.db import migrations, models


def set_inventory_access_from_role(apps, schema_editor):
    User = apps.get_model("core", "User")
    defaults = {
        "SUPER_ADMIN": dict(inv_grn=True, inv_outward=True, inv_receive=True, inv_branch_outward=True, inv_stock=True),
        "ACCOUNTS": dict(inv_grn=True, inv_outward=True, inv_receive=False, inv_branch_outward=False, inv_stock=True),
        "BRANCH_MANAGER": dict(inv_grn=False, inv_outward=False, inv_receive=True, inv_branch_outward=True, inv_stock=True),
        "BRANCH_STAFF": dict(inv_grn=False, inv_outward=False, inv_receive=True, inv_branch_outward=True, inv_stock=True),
        "AUDITOR": dict(inv_grn=True, inv_outward=True, inv_receive=True, inv_branch_outward=True, inv_stock=True),
    }
    for user in User.objects.all():
        role_defaults = defaults.get(user.role, defaults["BRANCH_STAFF"])
        for field, value in role_defaults.items():
            setattr(user, field, value)
        user.save(update_fields=list(role_defaults.keys()))


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_remove_branch_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="inv_branch_outward",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="inv_grn",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="inv_outward",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="inv_receive",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="inv_stock",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(set_inventory_access_from_role, migrations.RunPython.noop),
    ]
