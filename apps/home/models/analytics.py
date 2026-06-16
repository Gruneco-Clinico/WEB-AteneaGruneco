from django.db import models


#### INTEGRACIÓN RECUÉRDAME


class InteractionMetric(models.Model):
    event = models.CharField(max_length=255)
    distinct_id = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    properties = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} - {self.timestamp}"


class EstadisticasUsuarioResult(models.Model):
    email = models.EmailField()
    ingresos = models.IntegerField(default=0)  # user_values
    sesiones_ingresadas = models.IntegerField(default=0)
    sesiones_convertidas = models.IntegerField(default=0)
    sesiones_abandonadas = models.IntegerField(default=0)
    conversion_rate = models.FloatField(default=0.0)
    tiempo_promedio = models.CharField(max_length=50, blank=True, null=True)
    tiempo_mediano = models.CharField(max_length=50, blank=True, null=True)
    total_clicks = models.IntegerField(default=0)

    def __str__(self):
        return f"Estadísticas Usuario - {self.email}"
