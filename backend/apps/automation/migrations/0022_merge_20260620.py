"""Merge automation leaf nodes 0020 and 0021."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("automation", "0020_rename_automation__content_72497c_idx_automation__content_eceb32_idx"),
        ("automation", "0021_delete_imagerotation"),
    ]

    operations = []
