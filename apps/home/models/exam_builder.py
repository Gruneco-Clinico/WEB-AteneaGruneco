# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings


class ExamenSchemaVersion(models.Model):
    """
    Versión inmutable del esquema de un examen dinámico (snapshot al publicar).
    """

    examen = models.ForeignKey(
        "Examen",
        on_delete=models.CASCADE,
        related_name="schema_versions",
        verbose_name="Examen",
    )
    version = models.PositiveIntegerField(default=1, verbose_name="Versión")
    schema = models.JSONField(default=list, verbose_name="Esquema (campos)")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="examen_schema_versions",
    )

    class Meta:
        ordering = ["-version", "-created_at"]
        unique_together = [["examen", "version"]]
        verbose_name = "Versión de esquema de examen"
        verbose_name_plural = "Versiones de esquema de examen"

    def __str__(self):
        return f"{self.examen_id} v{self.version}"


class ExamenSubmission(models.Model):
    """
    Respuestas de un examen construido con el Form Builder (JSON por VisitaExamen).
    """

    visita_examen = models.OneToOneField(
        "VisitaExamen",
        on_delete=models.CASCADE,
        related_name="builder_submission",
        verbose_name="Visita examen",
    )
    schema_version = models.ForeignKey(
        ExamenSchemaVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
        verbose_name="Versión de esquema",
    )
    answers = models.JSONField(default=dict, verbose_name="Respuestas")
    computed = models.JSONField(default=dict, verbose_name="Valores calculados")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Envío de examen (builder)"
        verbose_name_plural = "Envíos de examen (builder)"

    def __str__(self):
        return f"Submission ve={self.visita_examen_id}"
