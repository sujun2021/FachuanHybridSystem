from __future__ import annotations

from django.db import migrations, models


TABLE_NAME = "contracts_finalizedmaterial"


def _get_existing_columns(schema_editor) -> set[str]:
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
            return {row[1] for row in cursor.fetchall()}

        description = connection.introspection.get_table_description(cursor, TABLE_NAME)
        return {column.name for column in description}


def add_file_metadata_columns(apps, schema_editor) -> None:
    connection = schema_editor.connection
    existing_columns = _get_existing_columns(schema_editor)

    if "relative_file_path" not in existing_columns:
        schema_editor.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN relative_file_path varchar(1000) NOT NULL DEFAULT ''"
        )

    schema_editor.execute(
        f"UPDATE {TABLE_NAME} SET relative_file_path = COALESCE(file_path, '') "
        f"WHERE relative_file_path IS NULL OR relative_file_path = ''"
    )
    if connection.vendor == "postgresql":
        schema_editor.execute(f"ALTER TABLE {TABLE_NAME} ALTER COLUMN relative_file_path SET NOT NULL")

    if connection.vendor == "postgresql":
        schema_editor.execute(f"ALTER TABLE {TABLE_NAME} ALTER COLUMN relative_file_path SET DEFAULT ''")

    for column_name, max_length in (("storage_root_type", 100), ("subdir_path", 1000)):
        if column_name not in existing_columns:
            schema_editor.execute(
                f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} varchar({max_length}) NOT NULL DEFAULT ''"
            )
        else:
            schema_editor.execute(
                f"UPDATE {TABLE_NAME} SET {column_name} = '' WHERE {column_name} IS NULL"
            )
            if connection.vendor == "postgresql":
                schema_editor.execute(f"ALTER TABLE {TABLE_NAME} ALTER COLUMN {column_name} SET NOT NULL")

        if connection.vendor == "postgresql":
            schema_editor.execute(f"ALTER TABLE {TABLE_NAME} ALTER COLUMN {column_name} SET DEFAULT ''")


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0028_p3_protect_payment_fk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_file_metadata_columns, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="finalizedmaterial",
                    name="relative_file_path",
                    field=models.CharField(blank=True, default="", max_length=1000, verbose_name="相对文件路径"),
                ),
                migrations.AddField(
                    model_name="finalizedmaterial",
                    name="storage_root_type",
                    field=models.CharField(blank=True, default="", max_length=100, verbose_name="存储根类型"),
                ),
                migrations.AddField(
                    model_name="finalizedmaterial",
                    name="subdir_path",
                    field=models.CharField(blank=True, default="", max_length=1000, verbose_name="子目录路径"),
                ),
            ],
        ),
    ]
