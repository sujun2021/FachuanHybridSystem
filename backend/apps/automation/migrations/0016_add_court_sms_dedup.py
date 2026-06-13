# Generated migration — add content_hash + duplicate_of to CourtSMS
from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0015_add_captcha_manual_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="courtsms",
            name="content_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                verbose_name="内容哈希（MD5，用于去重）",
            ),
        ),
        migrations.AddField(
            model_name="courtsms",
            name="duplicate_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="duplicates",
                to="automation.courtsms",
                verbose_name="重复自",
            ),
        ),
        migrations.AddIndex(
            model_name="courtsms",
            index=models.Index(
                fields=["content_hash", "-received_at"],
                name="automation__content_72497c_idx",
            ),
        ),
    ]
