# Generated manually for adding consentimiento_pdf field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyecto',
            name='consentimiento_pdf',
            field=models.FileField(blank=True, help_text='PDF del consentimiento informado que se enviará por correo al agendar citas de este proyecto.', null=True, upload_to='consentimientos/', verbose_name='Consentimiento Informado (PDF)'),
        ),
    ]
