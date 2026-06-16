# Generated manually to classify existing exams by name patterns
from django.db import migrations


def backfill_examen_categoria(apps, schema_editor):
    Examen = apps.get_model('home', 'Examen')

    reglas = [
        (
            'SUENO',
            [
                'sueno',
                'pittsburgh',
                'epworth',
                'mew',
                'stop-bang',
                'stopbang',
                'berlin',
                'atenas',
                'isi',
            ],
        ),
        (
            'NEUROPSICO',
            [
                'moca',
                'euroqol',
                'eva',
                'yesavage',
                'bettyferrel',
            ],
        ),
        (
            'CLINICAS',
            [
                'npi',
                'cdr',
                'lawton',
                'zarit',
                'aqd',
                'redlat',
            ],
        ),
        (
            'MEDICAS',
            [
                'general_',
                'antecedentes',
                'examenneurologico',
                'cognitivo_anamnesis',
                'anamnesis_',
                'analisis',
                'medicamentos',
                'examenfisico',
                'revision',
                'consentimiento',
            ],
        ),
    ]

    for examen in Examen.objects.all():
        nombre = (examen.nombre or '').lower().replace('í', 'i').replace('á', 'a').replace('é', 'e').replace('ó', 'o').replace('ú', 'u')
        categoria = 'OTROS'
        for codigo, patrones in reglas:
            if any(p in nombre for p in patrones):
                categoria = codigo
                break
        if examen.categoria != categoria:
            examen.categoria = categoria
            examen.save(update_fields=['categoria'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_examen_categoria'),
    ]

    operations = [
        migrations.RunPython(backfill_examen_categoria, noop_reverse),
    ]
