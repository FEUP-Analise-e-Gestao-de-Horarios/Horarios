from typing import ClassVar

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar = [
        ("projects", "0001_initial"),
    ]

    operations: ClassVar = [
        migrations.AddField(
            model_name="project",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
