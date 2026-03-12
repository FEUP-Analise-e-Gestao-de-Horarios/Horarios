from django.contrib.auth.hashers import make_password
from django.db import migrations


def add_custom_user(apps, schema_editor):
    CustomUser = apps.get_model("users", "User")
    superuser = CustomUser(
        username="admin",
        email="feupscheduler@gmail.com",
        is_staff=True,
        is_superuser=True,
        is_active=True,
        sent_email=True,
        password=make_password("passhorarios"),
    )
    superuser.save()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_custom_user),
    ]
