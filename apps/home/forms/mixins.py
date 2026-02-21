# -*- encoding: utf-8 -*-
"""
Mixin and utilities for exam form handling.

ExamSaveMixin:
    Provides a standardized save flow for exam views, handling:
    - VisitaExamen state transitions (pendiente → en_progreso → completado)
    - ModelForm-based get_or_create / update pattern
    - Error handling and rollback
"""
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from ..models import VisitaExamen


class ExamSaveMixin:
    """
    Utility class that encapsulates the common exam save workflow.

    Usage in a view::

        from ..forms import EpworthForm, ExamSaveMixin

        @login_required
        def guardar_examen_Epworth(request):
            if request.method != "POST":
                messages.error(request, "Método no permitido.")
                return redirect("index")

            helper = ExamSaveMixin(request)
            visita_examen = helper.get_visita_examen()
            if visita_examen is None:
                return helper.redirect_error("Visita-examen no encontrada.")

            helper.mark_in_progress(visita_examen)

            form = EpworthForm(request.POST)
            if not form.is_valid():
                return helper.redirect_with_form_errors(form)

            helper.save_form(form, visita_examen)
            helper.mark_completed(visita_examen)

            messages.success(request, "Escala de Epworth guardada exitosamente.")
            return helper.redirect_success()
    """

    def __init__(self, request):
        self.request = request
        self.visita_id = request.POST.get("visita_id")
        self.paciente_id = request.POST.get("paciente_id")
        self.examen_id = request.POST.get("examen_id")

    def get_visita_examen(self):
        """Retrieve the VisitaExamen or return None."""
        try:
            return get_object_or_404(
                VisitaExamen,
                visita_id=self.visita_id,
                examen_id=self.examen_id,
            )
        except Exception:
            return None

    def mark_in_progress(self, visita_examen):
        """Move VisitaExamen from 'pendiente' to 'en_progreso'."""
        if visita_examen.estado == "pendiente":
            visita_examen.estado = "en_progreso"
            visita_examen.fecha_inicio = timezone.now()
            visita_examen.save()

    def mark_completed(self, visita_examen):
        """Mark VisitaExamen as completed."""
        visita_examen.estado = "completado"
        visita_examen.fecha_completado = timezone.now()
        visita_examen.save()

    def save_form(self, form, visita_examen):
        """
        Save a ModelForm, using update_or_create with visita_examen as the key.
        Returns the saved instance.
        """
        Model = form.Meta.model
        defaults = form.cleaned_data
        instance, _ = Model.objects.update_or_create(
            visita_examen=visita_examen,
            defaults=defaults,
        )
        return instance

    def redirect_success(self):
        """Redirect to the patient detail after success."""
        return redirect("detalle_paciente", paciente_id=self.paciente_id)

    def redirect_error(self, msg="Error al guardar el examen."):
        """Redirect with an error message."""
        messages.error(self.request, f"❌ {msg}")
        return redirect("detalle_paciente", paciente_id=self.paciente_id or 1)

    def redirect_with_form_errors(self, form):
        """Redirect showing form validation errors."""
        error_list = "; ".join(
            f"{field}: {', '.join(errs)}" for field, errs in form.errors.items()
        )
        return self.redirect_error(f"Errores de validación: {error_list}")
