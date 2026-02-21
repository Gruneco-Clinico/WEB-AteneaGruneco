from django.db import models
from django.contrib.auth.models import User


class Sala(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    capacidad = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sala"
        verbose_name_plural = "Salas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class DisponibilidadUsuario(models.Model):
    DIAS_SEMANA = [
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="disponibilidades"
    )
    sala = models.ForeignKey(
        Sala, on_delete=models.CASCADE, related_name="disponibilidades"
    )
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def esta_disponible_para_fecha(self, fecha):
        """Verificar si está disponible en una fecha específica"""
        # Verificar que sea el día correcto de la semana
        if fecha.weekday() != self.dia_semana:
            return False

        # Verificar que esté en el rango de fechas válidas
        if fecha < self.fecha_inicio:
            return False

        if self.fecha_fin and fecha > self.fecha_fin:
            return False

        # Verificar que no hay cita agendada para esa fecha
        return not CitaMedica.objects.filter(
            disponibilidad=self, fecha_cita=fecha, estado__in=["agendada", "confirmada"]
        ).exists()

    class Meta:
        verbose_name = "Disponibilidad de Usuario"
        verbose_name_plural = "Disponibilidades de Usuarios"
        unique_together = ["usuario", "sala", "dia_semana", "hora_inicio"]
        ordering = ["dia_semana", "hora_inicio"]

    def clean(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError("La hora de inicio debe ser menor que la hora de fin")

        if self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError(
                "La fecha de inicio debe ser menor que la fecha de fin"
            )

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - {self.sala.nombre} - {self.get_dia_semana_display()} ({self.hora_inicio}-{self.hora_fin})"


class CitaMedica(models.Model):
    ESTADO_CHOICES = [
        ("agendada", "Agendada"),
        ("confirmada", "Confirmada"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
        ("no_asistio", "No asistió"),
    ]

    # Relación con la disponibilidad (plantilla)
    disponibilidad = models.ForeignKey(
        DisponibilidadUsuario, on_delete=models.CASCADE, related_name="citas"
    )

    # Fecha y hora específicas
    fecha_cita = models.DateField()
    # La hora se toma de disponibilidad.hora_inicio y disponibilidad.hora_fin

    # Datos del paciente
    email_paciente = models.EmailField()
    nombre_paciente = models.CharField(max_length=200)
    telefono_paciente = models.CharField(max_length=20, blank=True)
    motivo_consulta = models.TextField(blank=True)

    # Control
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="agendada")
    fecha_agendamiento = models.DateTimeField(auto_now_add=True)

    # Propiedades de conveniencia
    @property
    def hora_inicio(self):
        return self.disponibilidad.hora_inicio

    @property
    def hora_fin(self):
        return self.disponibilidad.hora_fin

    @property
    def profesional(self):
        return self.disponibilidad.usuario

    @property
    def sala(self):
        return self.disponibilidad.sala

    class Meta:
        unique_together = ["disponibilidad", "fecha_cita"]

    def __str__(self):
        return f"{self.nombre_paciente} - {self.fecha_cita} {self.hora_inicio}"


class BloqueoDisponibilidad(models.Model):
    disponibilidad = models.ForeignKey(
        DisponibilidadUsuario, on_delete=models.CASCADE, related_name="bloqueos"
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    motivo = models.CharField(max_length=200, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bloqueo de Disponibilidad"
        verbose_name_plural = "Bloqueos de Disponibilidad"

    def __str__(self):
        return f"Bloqueo: {self.disponibilidad} - {self.fecha}"
