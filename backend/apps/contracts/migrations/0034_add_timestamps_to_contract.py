"""Add created_at and updated_at to Contract.

Uses default=timezone.now to backfill existing rows,
then alters to auto_now_add / auto_now.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0033_add_storage_to_folder_root_preset"),
    ]

    operations = [
        # Step 1: add columns with a default so existing rows are backfilled
        migrations.AddField(
            model_name="contract",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="创建时间",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="updated_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="更新时间",
            ),
        ),
        # Step 2: switch to auto_now_add / auto_now (Django handles the DB-level alter)
        migrations.AlterField(
            model_name="contract",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                verbose_name="创建时间",
            ),
        ),
        migrations.AlterField(
            model_name="contract",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                verbose_name="更新时间",
            ),
        ),
        # HistoricalContract: add fields with default (no auto_now for history records)
        migrations.AddField(
            model_name="historicalcontract",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="historicalcontract",
            name="updated_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
