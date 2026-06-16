from django.conf import settings
from django.db import models


class ConsentimientoFirmaEnvio(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("completado", "Completado"),
    ]

    TIPO_DOCUMENTO_CHOICES = [
        ("CC", "Cedula de ciudadania"),
        ("TI", "Tarjeta de Identidad"),
        ("NUIP", "Numero Unico de Identificacion Personal - NUIP"),
        ("CE", "Cedula de Extranjeria"),
        ("PS", "Pasaporte"),
    ]

    paciente = models.ForeignKey(
        "DatosDemograficos",
        on_delete=models.CASCADE,
        related_name="consentimientos_firma",
    )
    proyecto = models.ForeignKey(
        "Proyecto",
        on_delete=models.CASCADE,
        related_name="consentimientos_firma",
    )
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consentimientos_enviados",
    )

    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default="pendiente")
    fecha_envio_link = models.DateTimeField(auto_now_add=True)

    acepta_participacion = models.BooleanField(null=True, blank=True)
    acepta_uso_futuras_investigaciones = models.BooleanField(null=True, blank=True)
    acepta_contacto_nuevas_investigaciones = models.BooleanField(null=True, blank=True)

    nombres_apellidos = models.CharField(max_length=255, blank=True)
    tipo_documento = models.CharField(max_length=10, choices=TIPO_DOCUMENTO_CHOICES, blank=True)
    numero_documento = models.CharField(max_length=30, blank=True)
    fecha_firma = models.DateField(null=True, blank=True)
    hora_firma = models.TimeField(null=True, blank=True)
    correo_electronico = models.EmailField(blank=True)
    celular = models.CharField(max_length=30, blank=True)
    firma_participante = models.TextField(blank=True, null=True)

    fecha_guardado_formulario = models.DateTimeField(null=True, blank=True)
    ip_guardado_formulario = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_envio_link"]

    def __str__(self):
        return f"Consentimiento firma #{self.id} - Paciente {self.paciente_id} - Proyecto {self.proyecto_id}"
