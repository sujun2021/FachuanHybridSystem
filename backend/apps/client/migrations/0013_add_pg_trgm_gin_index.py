"""在 Client.name 上添加 GIN 索引，加速当事人名称模糊搜索。"""

from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("client", "0012_alter_historicalclient_created_at_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="client",
            index=GinIndex(
                name="client_client_name_gin_trgm",
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]
