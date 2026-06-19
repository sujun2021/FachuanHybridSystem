"""Add created_at and updated_at to Case.

Uses default=timezone.now to backfill existing rows,
then alters to auto_now_add / auto_now.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0027_remove_caselog_cases_caselog_created_idx"),
    ]

    operations = [
        # Step 1: add columns with a default so existing rows are backfilled
        migrations.AddField(
            model_name="case",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="创建时间",
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="updated_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="更新时间",
            ),
        ),
        # Step 2: switch to auto_now_add / auto_now (Django handles the DB-level alter)
        migrations.AlterField(
            model_name="case",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                verbose_name="创建时间",
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                verbose_name="更新时间",
            ),
        ),
    ]
