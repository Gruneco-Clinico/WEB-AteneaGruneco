# Generated manually to reconcile DB with model state.
#
# Background:
#   * The model ``home.Proyecto`` declares ``consentimiento_pdf``.
#   * ``0001_initial.py`` also declares the column.
#   * The former ``0002_proyecto_consentimiento_pdf`` used to add the column
#     via AddField, but was later converted to a no-op (the column was
#     squashed into 0001_initial).
#   * Some environments were migrated before that squash and therefore never
#     ran the AddField, so the physical column may be missing in MySQL even
#     though Django's migration state believes it should be there.
#
# This migration uses RunPython with introspection of ``information_schema``
# so the ORM state is NOT touched (it is already correct from 0001_initial)
# and only the physical column is ensured, idempotently.
#
# Safe to run on any environment: if the column already exists, the migration
# becomes a no-op.

from django.db import migrations


def ensure_consentimiento_pdf_column(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor

    with connection.cursor() as cursor:
        if vendor == "mysql":
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'home_proyecto'
                  AND COLUMN_NAME = 'consentimiento_pdf'
                """
            )
            exists = cursor.fetchone()[0]
            if not exists:
                cursor.execute(
                    "ALTER TABLE home_proyecto "
                    "ADD COLUMN consentimiento_pdf VARCHAR(100) NULL"
                )
        else:
            columns = {
                col.name
                for col in connection.introspection.get_table_description(
                    cursor, "home_proyecto"
                )
            }
            if "consentimiento_pdf" not in columns:
                if vendor == "postgresql":
                    cursor.execute(
                        'ALTER TABLE home_proyecto '
                        'ADD COLUMN consentimiento_pdf varchar(100) NULL'
                    )
                else:
                    cursor.execute(
                        'ALTER TABLE "home_proyecto" '
                        'ADD COLUMN "consentimiento_pdf" varchar(100) NULL'
                    )


def noop_reverse(apps, schema_editor):
    # Reversal is a no-op: we don't want to drop the column on reverse because
    # ``0001_initial`` declares it as part of initial state.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0008_exam_builder_schema_submission"),
    ]

    operations = [
        migrations.RunPython(
            ensure_consentimiento_pdf_column,
            noop_reverse,
        ),
    ]
