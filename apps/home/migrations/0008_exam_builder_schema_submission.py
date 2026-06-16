# Generated manually for Form Builder

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0006_merge_20260322_1606"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExamenSchemaVersion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("version", models.PositiveIntegerField(default=1, verbose_name="Versión")),
                ("schema", models.JSONField(default=list, verbose_name="Esquema (campos)")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="examen_schema_versions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "examen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="schema_versions",
                        to="home.examen",
                        verbose_name="Examen",
                    ),
                ),
            ],
            options={
                "verbose_name": "Versión de esquema de examen",
                "verbose_name_plural": "Versiones de esquema de examen",
                "ordering": ["-version", "-created_at"],
                "unique_together": {("examen", "version")},
            },
        ),
        migrations.CreateModel(
            name="ExamenSubmission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("answers", models.JSONField(default=dict, verbose_name="Respuestas")),
                ("computed", models.JSONField(default=dict, verbose_name="Valores calculados")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "schema_version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="submissions",
                        to="home.examenschemaversion",
                        verbose_name="Versión de esquema",
                    ),
                ),
                (
                    "visita_examen",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="builder_submission",
                        to="home.visitaexamen",
                        verbose_name="Visita examen",
                    ),
                ),
            ],
            options={
                "verbose_name": "Envío de examen (builder)",
                "verbose_name_plural": "Envíos de examen (builder)",
            },
        ),
    ]
