# -*- encoding: utf-8 -*-
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse, HttpResponseServerError
from django.template import loader
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.core.mail import send_mail, EmailMessage
from django.db.models import Max
from datetime import datetime, timedelta
from ..models import *
from ..forms import ProyectoForm, RegistroDemograficoForm, CognitivoAnamnesisForm
from .exam_builder import builder_result_response, realizar_examen_builder
from ..exam_legacy import examen_has_builder_schema, is_legacy_examen
from ..exam_registry import get_exam_config, get_exam_model
import json
import requests
import logging
import os
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from io import BytesIO

logger = logging.getLogger(__name__)

@login_required
def realizar_examen(request, visita_id, examen_id, paciente_id):
    # Legacy (IDs definidos en exam_legacy): siempre plantilla/registry fijos,
    # nunca builder aunque ``Examen.campos`` esté poblado por error en BD.
    examen = get_object_or_404(Examen, pk=examen_id)
    if is_legacy_examen(examen_id):
        config = get_exam_config(int(examen_id))
        if not config:
            messages.error(
                request,
                "Este examen legacy no tiene configuración de plantilla registrada.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)
    else:
        if examen_has_builder_schema(examen.campos):
            return realizar_examen_builder(request, visita_id, examen_id, paciente_id)
        config = get_exam_config(int(examen_id))
        if not config:
            return realizar_examen_builder(request, visita_id, examen_id, paciente_id)

    exam_model = get_exam_model(int(examen_id))

    # Obtener datos existentes
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    visita = get_object_or_404(Visita, id=visita_id, paciente=paciente)
    
    # BLOQUEAR EDICIÓN SI LA VISITA ESTÁ FIRMADA
    if visita.firmado:
        messages.error(request, "No se puede editar un examen de una visita firmada.")
        return redirect("detalle_paciente", paciente_id=paciente_id)
    
    try:
        visita_examen_obj = VisitaExamen.objects.get(
            visita_id=visita_id, examen_id=examen_id
        )
    except VisitaExamen.DoesNotExist:
        messages.error(request, "Visita-examen no encontrada")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    from ..services.exam_edit_context import (
        build_datos_examen_edicion,
        serialize_datos_examen,
    )

    datos_examen, modo_edicion, extra_ctx = build_datos_examen_edicion(
        visita_examen_obj, paciente, examen_id, exam_model
    )
    datos_examen_json = serialize_datos_examen(datos_examen)

    context = {
        "visita_examen": visita_id,
        "paciente_id": paciente_id,
        "examen_id": examen_id,
        "datos_examen": datos_examen,
        "datos_examen_json": datos_examen_json,
        "modo_edicion": modo_edicion,
        "visita_examen_obj": visita_examen_obj,
        "paciente": paciente,
        "visita": visita,
    }
    if int(examen_id) in (3, 9) and exam_model:
        from apps.home.models.field_toggle_semantics import TOGGLE_LABELS

        context["field_toggle_semantics_json"] = json.dumps(
            getattr(exam_model, "FIELD_TOGGLE_SEMANTICS", {})
        )
        context["toggle_labels_json"] = json.dumps(TOGGLE_LABELS)
    if extra_ctx:
        context.update(extra_ctx)

    return render(request, config["template"], context)


@login_required
def ver_resultado_examen(request, visita_examen_id):
    visita_examen = get_object_or_404(VisitaExamen, id=visita_examen_id)

    if not visita_examen.esta_realizado:
        messages.error(request, "Este examen aún no ha sido completado.")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )

    br = builder_result_response(request, visita_examen)
    if br is not None:
        return br

    from ..services.exam_view_context import get_context_ver_examen

    try:
        template_name, context = get_context_ver_examen(visita_examen)
        return render(request, template_name, context)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )
    except Exception as e:
        messages.error(request, f"Error al cargar el examen: {str(e)}")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )



@login_required
def guardar_examen_cognitivo_anamnesis(request):
    """Vista para guardar el examen cognitivo anamnesis usando CognitivoAnamnesisForm."""
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = CognitivoAnamnesisForm(request.POST)
            if form.is_valid():
                cognitivo_anamnesis, created = (
                    CognitivoAnamnesisResult.objects.update_or_create(
                        visita_examen=visita_examen,
                        defaults=form.cleaned_data,
                    )
                )

                # ==============================
                # Procesar relaciones hijas
                # ==============================
                cognitivo_anamnesis.actitudes.all().delete()
                cognitivo_anamnesis.atenciones.all().delete()
                cognitivo_anamnesis.errores_lenguaje.all().delete()
                cognitivo_anamnesis.actividades_vida_diaria.all().delete()
                cognitivo_anamnesis.actividades_complejas.all().delete()

                # Nombres POST alineados con cognitivo_Anamnesis.html
                for actitud in request.POST.getlist("actitud_seleccion"):
                    if actitud:
                        ActitudCognitiva.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=actitud
                        )

                atencion_prefix = {
                    "Quejas atencionales": "quejas",
                    "Alteración atención sostenida": "sostenida",
                    "Alteración atención dividida": "dividida",
                    "Incapacidad para quedarse quieto": "quieto",
                    "Dificultad para finalizar una tarea": "tarea",
                    "Dificultad para seguir instrucciones": "instrucciones",
                    "Distracción con estímulos irrelevantes": "distraccion",
                }
                for tipo in request.POST.getlist("atencion_seleccion[]"):
                    if not tipo:
                        continue
                    prefix = atencion_prefix.get(tipo)
                    edad = (
                        request.POST.get(f"{prefix}_edad_inicio", "")
                        if prefix
                        else ""
                    )
                    caract = (
                        request.POST.get(f"{prefix}_caracteristicas", "")
                        if prefix
                        else ""
                    )
                    AtencionCognitiva.objects.create(
                        anamnesis=cognitivo_anamnesis,
                        tipo=tipo,
                        edad_inicio=edad or "",
                        caracteristicas=caract or "",
                    )

                for error in request.POST.getlist("lenguaje_errores[]"):
                    if error:
                        ErrorLenguajeCognitivo.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=error
                        )

                for actividad in request.POST.getlist("actividades_vida_diaria[]"):
                    if actividad:
                        ActividadVidaDiaria.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=actividad
                        )

                for actividad in request.POST.getlist("actividades_complejas[]"):
                    if actividad:
                        ActividadCompleja.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=actividad
                        )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(
                    request,
                    "✅ Examen Cognitivo Anamnesis guardado exitosamente.",
                )
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in list(form.errors.items())[:5]
                )
                messages.error(
                    request,
                    f"❌ Error de validación en cognitivo anamnesis: {error_msgs}",
                )
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass

            messages.error(
                request, f"❌ Error al guardar el examen cognitivo: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


# Función auxiliar para enteros opcionales
def safe_int_optional(value):
    """Convierte a int o retorna None si no hay valor"""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


