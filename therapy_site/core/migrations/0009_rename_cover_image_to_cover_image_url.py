from django.db import migrations


def rename_cover_column_if_needed(apps, schema_editor):
    connection = schema_editor.connection
    table_name = apps.get_model("core", "Blog")._meta.db_table
    columns = {
        column.name
        for column in connection.introspection.get_table_description(
            connection.cursor(), table_name
        )
    }

    if "cover_image" in columns and "cover_image_url" not in columns:
        schema_editor.execute(
            "ALTER TABLE {table} RENAME COLUMN {old} TO {new}".format(
                table=schema_editor.quote_name(table_name),
                old=schema_editor.quote_name("cover_image"),
                new=schema_editor.quote_name("cover_image_url"),
            )
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_blog_covers_admin"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    rename_cover_column_if_needed,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.RenameField(
                    model_name="blog",
                    old_name="cover_image",
                    new_name="cover_image_url",
                ),
            ],
        ),
    ]