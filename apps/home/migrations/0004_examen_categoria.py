# Generated manually to classify exams by category
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_consentimientofirmaenvio'),
    ]

    operations = [
        migrations.AddField(
            model_name='examen',
            name='categoria',
            field=models.CharField(
                choices=[
                    ('MEDICAS', 'Evaluaciones Medicas'),
                    ('CLINICAS', 'Escalas clinicas'),
                    ('NEUROPSICO', 'Evaluaciones Neuropsicologicas'),
                    ('SUENO', 'Escalas de sueno'),
                    ('OTROS', 'Otros'),
                ],
                default='OTROS',
                max_length=20,
                verbose_name='Categoria',
            ),
        ),
    ]
