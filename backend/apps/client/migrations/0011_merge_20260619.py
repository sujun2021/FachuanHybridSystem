"""Merge two 0010 leaf nodes: timestamps + fddbrsjhm_phone."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("client", "0010_add_timestamps_to_client"),
        ("client", "0010_client_fddbrsjhm_phone_and_more"),
    ]

    operations = []
