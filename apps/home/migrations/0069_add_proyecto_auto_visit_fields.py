# Generated manually

import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0068_add_proyecto_to_citamedica"),
    ]

    operations = [
        migrations.AddField(
            model_name="proyecto",
            name="crear_visita_automatica",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Si está activo, al registrarse un paciente desde el formulario "
                    "público se creará una visita automática con el tipo de visita configurado."
                ),
                verbose_name="Crear visita automática al registrar paciente",
            ),
        ),
        migrations.AddField(
            model_name="proyecto",
            name="tipo_visita_automatica",
            field=models.ForeignKey(
                blank=True,
                help_text="Tipo de visita que se creará automáticamente al registrar paciente.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="proyectos_auto",
                to="home.tipovisita",
                verbose_name="Tipo de visita automática",
            ),
        ),
        migrations.AddField(
            model_name="proyecto",
            name="nombre_visita_automatica",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Nombre que se asignará a la visita creada automáticamente. "
                    "Si está vacío, se usará el nombre del tipo de visita."
                ),
                max_length=255,
                verbose_name="Nombre de la visita automática",
            ),
        ),
    ]
