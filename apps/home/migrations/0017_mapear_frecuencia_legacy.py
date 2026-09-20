# -*- encoding: utf-8 -*-
from django.db import migrations


def mapear_frecuencia_legacy(apps, schema_editor):
    """dias→diario, semanas→semanal, meses→semanal."""
    mapping = {
        "dias": "diario",
        "semanas": "semanal",
        "meses": "semanal",
    }
    SerieVisitas = apps.get_model("home", "SerieVisitas")
    for old, new in mapping.items():
        SerieVisitas.objects.filter(frecuencia_unidad=old).update(frecuencia_unidad=new)
    try:
        Historical = apps.get_model("home", "HistoricalSerieVisitas")
    except LookupError:
        return
    for old, new in mapping.items():
        Historical.objects.filter(frecuencia_unidad=old).update(frecuencia_unidad=new)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0016_frecuencia_presets_dias_semana"),
    ]

    operations = [
        migrations.RunPython(mapear_frecuencia_legacy, noop_reverse),
    ]
