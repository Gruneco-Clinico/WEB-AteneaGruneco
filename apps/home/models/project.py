from django.db import models


class Proyecto(models.Model):
    nombre = models.CharField(
        max_length=255, unique=True, verbose_name="Nombre del Proyecto"
    )
    descripcion = models.TextField(
        blank=True, null=True, verbose_name="Descripción del Proyecto"
    )
    investigador_principal = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Investigador Principal"
    )
    codigo_siu = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Código SIU"
    )
    fecha_inicio = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Inicio"
    )
    fecha_financiacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Financiación"
    )
    pacientes = models.ManyToManyField(
        "DatosDemograficos",
        related_name="proyectos",
        verbose_name="Pacientes",
    )

    # --- Configuración de registro público automático ---
    crear_visita_automatica = models.BooleanField(
        default=True,
        verbose_name="Crear visita automática al registrar paciente",
        help_text="Si está activo, al registrarse un paciente desde el formulario público "
                  "se creará una visita automática con el tipo de visita configurado.",
    )
    tipo_visita_automatica = models.ForeignKey(
        "TipoVisita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proyectos_auto",
        verbose_name="Tipo de visita automática",
        help_text="Tipo de visita que se creará automáticamente al registrar paciente.",
    )
    nombre_visita_automatica = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Nombre de la visita automática",
        help_text="Nombre que se asignará a la visita creada automáticamente. "
                  "Si está vacío, se usará el nombre del tipo de visita.",
    )
    
    # --- Consentimiento informado ---
    consentimiento_pdf = models.FileField(
        upload_to="consentimientos/",
        blank=True,
        null=True,
        verbose_name="Consentimiento Informado (PDF)",
        help_text="PDF del consentimiento informado que se enviará por correo al agendar citas de este proyecto.",
    )

    def __str__(self):
        return self.nombre


class ProyectoPacienteExtra(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    paciente = models.ForeignKey('DatosDemograficos', on_delete=models.CASCADE)

    codigo_proyecto = models.CharField(max_length=20)

    class Meta:
        unique_together = ("proyecto", "paciente")


class Examen(models.Model):
    """Catálogo de exámenes clínicos disponibles."""

    nombre = models.CharField(max_length=255, verbose_name="Nombre del Examen")
    descripcion = models.TextField(
        verbose_name="Descripción del Examen", blank=True, null=True
    )
    campos = models.JSONField(
        verbose_name="Campos del Examen", default=list
    )  # Estructura del formulario

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Exámenes"


class TipoVisita(models.Model):
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Visita")
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="visitas",
        verbose_name="Proyecto",
    )
    observaciones = models.TextField(
        verbose_name="Observaciones", blank=True, null=True
    )
    examenes = models.JSONField(
        default=dict, verbose_name="Exámenes", null=True, blank=True
    )

    def __str__(self):
        return f"{self.nombre} - {self.proyecto.nombre}"
