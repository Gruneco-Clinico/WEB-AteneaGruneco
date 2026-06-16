from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from .patient import DatosDemograficos


class Visita(models.Model):
    paciente = models.ForeignKey(
        DatosDemograficos,
        on_delete=models.CASCADE,
        related_name="visitas",
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Visita")
    Tipo_visita = models.ForeignKey(
        'TipoVisita',
        on_delete=models.CASCADE,
        related_name="visitas",
        null=True,
        blank=True,
    )
    fecha = models.DateField(blank=True, null=True)
    evaluador = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas_evaluador"
    )

    # Notas aclaratorias — editable even after visit signature
    notas_aclaratorias = models.TextField(
        blank=True, null=True,
        verbose_name="Notas aclaratorias",
        help_text="Notas de clarificación editables después de la firma.",
    )

    estado_visita = models.CharField(
        max_length=20,
        choices=[
            ("abierta", "Abierta"),
            ("cerrada", "Cerrada"),
        ],
        default="abierta",
        db_index=True,
    )

    # Indica si la visita fue firmada (no se podrán editar exámenes relacionados si es True)
    firmado = models.BooleanField(default=False, verbose_name="Firmado", db_index=True)
    firmado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas_firmadas"
    )

    acompanante_nombre = models.CharField(max_length=255, blank=True, null=True)
    acompanante_relacion = models.CharField(max_length=100, blank=True, null=True)
    acompanante_correo = models.EmailField(blank=True, null=True)
    acompanante_telefono = models.CharField(max_length=20, blank=True, null=True)

    # Audit trail — tracks all changes with user and timestamp
    history = HistoricalRecords()

    class Meta:
        indexes = [
            models.Index(fields=["paciente", "estado_visita"], name="visita_pac_estado_idx"),
            models.Index(fields=["paciente", "fecha"], name="visita_pac_fecha_idx"),
        ]

    def __str__(self):
        if self.Tipo_visita and self.Tipo_visita.proyecto:
            return f"{self.nombre} - {self.Tipo_visita.proyecto.nombre}"
        return self.nombre

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.Tipo_visita:
            return

        if not self.Tipo_visita.proyecto:
            return

        if (
            self.Tipo_visita.proyecto.nombre == "Anosognosia"
            and self.Tipo_visita.nombre == "PosIntervención"
        ):
            paciente = self.paciente

            if not paciente:
                return

            if paciente.codigo:
                return

            ultimo = (
                DatosDemograficos.objects.exclude(codigo__isnull=True)
                .exclude(codigo__exact="")
                .order_by("-codigo")
                .first()
            )

            if ultimo and ultimo.codigo:
                try:
                    numero = int(ultimo.codigo.split("-")[1])
                except Exception:
                    numero = 0
            else:
                numero = 0

            nuevo_codigo = f"ANG-{numero + 1:03d}"
            paciente.codigo = nuevo_codigo
            paciente.save()


class VisitaExamen(models.Model):
    visita = models.ForeignKey(
        Visita, on_delete=models.CASCADE, related_name="visita_examenes"
    )
    examen = models.ForeignKey(
        'Examen', on_delete=models.CASCADE, related_name="examenes_realizados"
    )

    # Estado del examen
    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("en_progreso", "En Progreso"),
            ("completado", "Completado"),
            ("cancelado", "Cancelado"),
        ],
        default="pendiente",
        verbose_name="Estado del Examen",
        db_index=True,
    )

    # Fechas de seguimiento
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    # Metadatos adicionales
    notas_examinador = models.TextField(
        blank=True, null=True, verbose_name="Notas del Examinador"
    )

    # Campos opcionales para seguimiento
    evaluador = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Evaluador"
    )

    tiempo_duracion = models.DurationField(
        null=True, blank=True, verbose_name="Tiempo de Duración"
    )

    # Audit trail — tracks all changes with user and timestamp
    history = HistoricalRecords()

    class Meta:
        unique_together = ["visita", "examen"]
        indexes = [
            models.Index(fields=["visita", "estado"], name="visitaexam_visita_estado_idx"),
        ]
        verbose_name = "Examen de Visita"
        verbose_name_plural = "Exámenes de Visita"
        ordering = ["fecha_creacion"]

    def __str__(self):
        return (
            f"{self.visita.nombre} - {self.examen.nombre} ({self.get_estado_display()})"
        )

    def get_resultado_instance(self):
        """Retorna la instancia del resultado específico del examen si existe."""
        if not hasattr(self, "_resultado_cache"):
            self._resultado_cache = None

            from apps.home.exam_registry import get_exam_config

            config = get_exam_config(self.examen.id)
            if not config:
                return self._resultado_cache

            # MANEJO ESPECIAL para Antecedentes (uses AntecedentesVisitaLink bridge)
            if config.get("use_bridge"):
                try:
                    antecedentes_link = self.antecedentes_link
                    if antecedentes_link and antecedentes_link.antecedentes_result:
                        self._resultado_cache = antecedentes_link.antecedentes_result
                except AttributeError:
                    pass
                return self._resultado_cache

            related_name = config.get("related_name")
            if not related_name:
                return self._resultado_cache

            try:
                manager = getattr(self, related_name)

                # If it's a RelatedManager (ForeignKey), use .get()
                if hasattr(manager, "get"):
                    try:
                        resultado_instance = manager.get()
                        if resultado_instance:
                            self._resultado_cache = resultado_instance
                    except manager.model.DoesNotExist:
                        pass
                # If it's a direct instance (OneToOneField), use directly
                elif manager:
                    self._resultado_cache = manager
            except AttributeError:
                pass

        return self._resultado_cache

    @property
    def esta_realizado(self):
        """Verifica si el examen está completado y tiene un resultado concreto asociado."""

        estado_completado = self.estado == "completado"

        # Form Builder: resultado = ExamenSubmission (incluye IDs legacy si tienen ``campos``)
        from ..exam_legacy import examen_has_builder_schema, is_legacy_examen

        if examen_has_builder_schema(self.examen.campos) or not is_legacy_examen(
            self.examen_id
        ):
            from .exam_builder import ExamenSubmission

            tiene = ExamenSubmission.objects.filter(visita_examen=self).exists()
            return estado_completado and tiene

        resultado = self.get_resultado_instance()
        tiene_resultado = resultado is not None

        final_result = estado_completado and tiene_resultado

        return final_result

    @property
    def puede_editarse(self):
        """Verifica si el examen puede editarse."""
        # Solo puede editarse si la visita está abierta, NO está firmada Y el examen está realizado
        visita_abierta = self.visita.estado_visita == "abierta"
        visita_no_firmada = not self.visita.firmado
        examen_realizado = self.esta_realizado

        puede_editar = visita_abierta and visita_no_firmada and examen_realizado

        return puede_editar

    def get_nombre_examen_normalizado(self):
        """Retorna el nombre del examen normalizado para URLs"""
        return self.examen.nombre.lower().replace(" ", "").replace("-", "")

    def get_url_realizar(self):
        """Retorna la URL para realizar el examen específico"""
        return reverse(
            "realizar_examen",
            args=[self.visita.id, self.examen.id, self.visita.paciente.id],
        )

    def get_url_ver(self):
        """Retorna la URL para ver los resultados del examen"""
        if not self.esta_realizado:
            return "#"
        return reverse("ver_resultado_examen", args=[self.id])

    def get_url_editar(self):
        """Retorna la URL para editar el examen"""
        if not self.puede_editarse:
            return "#"
        return reverse(
            "realizar_examen",
            args=[self.visita.id, self.examen.id, self.visita.paciente.id],
        )

    def get_progreso_porcentaje(self):
        """Retorna el porcentaje de progreso del examen"""
        if self.estado == "completado":
            return 100
        elif self.estado == "en_progreso":
            return 50
        elif self.estado == "cancelado":
            return 0
        else:  # pendiente
            return 0

    def get_icono_estado(self):
        """Retorna el icono FontAwesome para el estado"""
        iconos = {
            "pendiente": "fas fa-hourglass-start",
            "en_progreso": "fas fa-clock",
            "completado": "fas fa-check-circle",
            "cancelado": "fas fa-times-circle",
        }
        return iconos.get(self.estado, "fas fa-question-circle")

    def get_color_badge(self):
        """Retorna la clase CSS para el badge del estado"""
        colores = {
            "pendiente": "badge-secondary",
            "en_progreso": "badge-warning",
            "completado": "badge-success",
            "cancelado": "badge-danger",
        }
        return colores.get(self.estado, "badge-light")


# Este modelo abstracto servirá como padre para todos los resultados de exámenes.
class ResultadoExamenBase(models.Model):
    # CORRECTO: Usar %(class)s para generar related_names únicos
    visita_examen = models.OneToOneField(
        VisitaExamen,
        on_delete=models.CASCADE,
        related_name="%(class)s_resultado",  # Esto genera nombres únicos
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"Resultado para {self.visita_examen}"
