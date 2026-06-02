from __future__ import annotations

from django.db import migrations


LEGACY_COLUMNS = (
    "original_filename",
    "relative_file_path",
    "storage_root_type",
    "subdir_path",
)


def _get_existing_columns(schema_editor) -> set[str]:
    connection = schema_editor.connection
    table_name = "cases_caselogattachment"

    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA table_info({table_name})")
            return {row[1] for row in cursor.fetchall()}

        description = connection.introspection.get_table_description(cursor, table_name)
        return {column.name for column in description}


def cleanup_legacy_caselogattachment_columns(apps, schema_editor) -> None:
    connection = schema_editor.connection
    existing_columns = _get_existing_columns(schema_editor)
    columns_to_drop = [column for column in LEGACY_COLUMNS if column in existing_columns]

    if not columns_to_drop:
        return

    if connection.vendor == "sqlite":
        schema_editor.execute("DROP INDEX IF EXISTS cases_caselogattachment_relative_file_path_36122a21")
        for column in columns_to_drop:
            schema_editor.execute(f"ALTER TABLE cases_caselogattachment DROP COLUMN {column}")
        return

    if connection.vendor == "postgresql":
        drop_clause = ", ".join(f"DROP COLUMN IF EXISTS {column}" for column in columns_to_drop)
        schema_editor.execute(f"ALTER TABLE cases_caselogattachment {drop_clause}")
        return

    raise RuntimeError(
        f"Unsupported database vendor for legacy CaseLogAttachment cleanup: {connection.vendor}"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0017_alter_caselogattachment_file_and_more"),
    ]

    operations = [
        migrations.RunPython(
            cleanup_legacy_caselogattachment_columns,
            migrations.RunPython.noop,
        ),
    ]
