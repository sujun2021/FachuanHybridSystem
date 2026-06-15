# Generated migration — add archived_to_case_folder flag to CourtSMS
from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0016_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="courtsms",
            name="archived_to_case_folder",
            field=models.BooleanField(default=False, verbose_name="已归档到案件目录"),
        ),
    ]
