# Generated manually for public consent signature links
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('home', '0002_proyecto_consentimiento_pdf'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsentimientoFirmaEnvio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('completado', 'Completado')], default='pendiente', max_length=15)),
                ('fecha_envio_link', models.DateTimeField(auto_now_add=True)),
                ('acepta_participacion', models.BooleanField(blank=True, null=True)),
                ('acepta_uso_futuras_investigaciones', models.BooleanField(blank=True, null=True)),
                ('acepta_contacto_nuevas_investigaciones', models.BooleanField(blank=True, null=True)),
                ('nombres_apellidos', models.CharField(blank=True, max_length=255)),
                ('tipo_documento', models.CharField(blank=True, choices=[('CC', 'Cedula de ciudadania'), ('TI', 'Tarjeta de Identidad'), ('NUIP', 'Numero Unico de Identificacion Personal - NUIP'), ('CE', 'Cedula de Extranjeria'), ('PS', 'Pasaporte')], max_length=10)),
                ('numero_documento', models.CharField(blank=True, max_length=30)),
                ('fecha_firma', models.DateField(blank=True, null=True)),
                ('hora_firma', models.TimeField(blank=True, null=True)),
                ('correo_electronico', models.EmailField(blank=True, max_length=254)),
                ('celular', models.CharField(blank=True, max_length=30)),
                ('firma_participante', models.TextField(blank=True, null=True)),
                ('fecha_guardado_formulario', models.DateTimeField(blank=True, null=True)),
                ('ip_guardado_formulario', models.GenericIPAddressField(blank=True, null=True)),
                ('enviado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consentimientos_enviados', to=settings.AUTH_USER_MODEL)),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consentimientos_firma', to='home.datosdemograficos')),
                ('proyecto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consentimientos_firma', to='home.proyecto')),
            ],
            options={
                'ordering': ['-fecha_envio_link'],
            },
        ),
    ]
