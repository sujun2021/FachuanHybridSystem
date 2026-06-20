"""启用 pg_trgm 扩展并在 CaseNumber.number 上添加 GIN 索引，加速模糊搜索。"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0031_alter_historicalcase_created_at_and_more"),
    ]

    operations = [
        # 启用 PostgreSQL pg_trgm 扩展（用于加速 LIKE 模糊搜索）
        TrigramExtension(),
        # 在案号字段上添加 GIN 索引
        migrations.AddIndex(
            model_name="casenumber",
            index=GinIndex(
                name="cases_casenumber_number_gin_trgm",
                fields=["number"],
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]
