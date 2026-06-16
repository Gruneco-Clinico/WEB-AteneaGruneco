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
from ..forms import (
    ProyectoForm, RegistroDemograficoForm,
    EpworthForm, SuenoFisicoForm, SuenoAnamnesisForm,
    AtenasForm, BerlinForm, ISIForm, MEWForm, PittsburghForm, StopBangForm,
)
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
def guardar_examen_fisico_sueno(request):
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

            form = SuenoFisicoForm(request.POST)
            if form.is_valid():
                SuenoFisicoResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Examen físico de sueño guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"❌ Error al guardar el examen: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_sueno_anamnesis(request):
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

            # ── Parent model via ModelForm ──
            form = SuenoAnamnesisForm(request.POST)
            if form.is_valid():
                anamnesis, created = SuenoAnamnesisResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

            # ── Child models (getlist patterns, unchanged) ──

            # Quejas de sueño
            anamnesis.tipos_queja_detalle.all().delete()
            nombres_quejas = request.POST.getlist("tipo_queja[]")
            for nombre in nombres_quejas:
                quejaId = nombre.lower().replace(" ", "_")
                TipoQuejaSueno.objects.create(
                    anamnesis=anamnesis,
                    nombre=nombre,
                    inicio=request.POST.get(f"{quejaId}_inicio", ""),
                    evolucion=request.POST.get(f"{quejaId}_evolucion", ""),
                    frecuencia=request.POST.get(f"{quejaId}_frecuencia", ""),
                    gravedad=request.POST.get(f"{quejaId}_gravedad", ""),
                )

            # Sustancias
            anamnesis.sustancias.all().delete()
            sustancias_tipos = request.POST.getlist("sustancias_tipo[]")
            sustancias_cantidades = request.POST.getlist("sustancias_cantidad[]")
            sustancias_frecuencias = request.POST.getlist("sustancias_frecuencia[]")
            sustancias_tiempos = request.POST.getlist("sustancias_tiempo[]")
            sustancias_observaciones = request.POST.getlist(
                "sustancias_observaciones[]"
            )

            for i, tipo in enumerate(sustancias_tipos):
                SustanciaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    cantidad=sustancias_cantidades[i]
                    if i < len(sustancias_cantidades)
                    else "",
                    frecuencia=sustancias_frecuencias[i]
                    if i < len(sustancias_frecuencias)
                    else "",
                    tiempo=sustancias_tiempos[i] if i < len(sustancias_tiempos) else "",
                    observaciones=sustancias_observaciones[i]
                    if i < len(sustancias_observaciones)
                    else "",
                )

            # Medicamentos
            anamnesis.medicamentos.all().delete()
            nombres = request.POST.getlist("nombre_medicamento[]")
            dosis = request.POST.getlist("dosis_medicamento[]")
            observaciones = request.POST.getlist("observaciones_medicamento[]")
            presentacion = request.POST.getlist("presentacion[]")
            veces_dia = request.POST.getlist("veces_dia[]")
            frecuencias = request.POST.getlist("frecuencia_medicamentos[]")
            tiempos = request.POST.getlist("tiempo_antes_dormir[]")

            for i, nombre in enumerate(nombres):
                MedicamentoSueno.objects.create(
                    anamnesis=anamnesis,
                    nombre=nombre,
                    dosis=dosis[i] if i < len(dosis) else "",
                    observaciones=observaciones[i] if i < len(observaciones) else "",
                    presentacion=presentacion[i] if i < len(presentacion) else "",
                    veces_dia=veces_dia[i] if i < len(veces_dia) else "",
                    frecuencia=frecuencias[i] if i < len(frecuencias) else "",
                    tiempo=tiempos[i] if i < len(tiempos) else "",
                )

            # Pantallas
            anamnesis.pantallas.all().delete()
            pantallas_tipos = request.POST.getlist("tipo_pantalla[]")
            pantallas_frecuencias = request.POST.getlist("pantalla_frecuencia[]")
            pantallas_tiempos = request.POST.getlist("pantalla_tiempo_dormir[]")

            for i, tipo in enumerate(pantallas_tipos):
                PantallaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    frecuencia=pantallas_frecuencias[i]
                    if i < len(pantallas_frecuencias)
                    else "",
                    tiempo_antes_dormir=pantallas_tiempos[i]
                    if i < len(pantallas_tiempos)
                    else "",
                )

            # Actividades en cama
            anamnesis.actividades_en_cama.all().delete()
            actividades_cama = request.POST.getlist("tipo_actividad[]")
            actividades_frec = request.POST.getlist("frecuencia_actividad[]")
            actividades_obs = request.POST.getlist("observaciones_actividades[]")

            for i, tipo in enumerate(actividades_cama):
                ActividadEnCamaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    frecuencia=actividades_frec[i] if i < len(actividades_frec) else "",
                    observaciones=actividades_obs[i]
                    if i < len(actividades_obs)
                    else "",
                )

            # Actividades físicas
            anamnesis.actividades_fisicas.all().delete()
            actfis_tipo = request.POST.getlist("tipo_actividad_fisica[]")
            actfis_otro = request.POST.getlist("tipo_actividad_otro_texto[]")
            actfis_intensidad = request.POST.getlist("intensidad_fisica[]")
            actfis_frec = request.POST.getlist("frecuencia_fisica[]")
            actfis_obs = request.POST.getlist("observaciones_actividad_fisica[]")

            for i, tipo in enumerate(actfis_tipo):
                ActividadFisicaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    otro_texto=actfis_otro[i] if i < len(actfis_otro) else "",
                    intensidad=actfis_intensidad[i]
                    if i < len(actfis_intensidad)
                    else "",
                    frecuencia=actfis_frec[i] if i < len(actfis_frec) else "",
                    observaciones=actfis_obs[i] if i < len(actfis_obs) else "",
                )

            # Síntomas de sueño
            anamnesis.sintomas_suenos.all().delete()
            sintomas_tipo = request.POST.getlist("tipo_sintoma[]")
            sintomas_inicio = request.POST.getlist("cuando_inicio[]")
            sintomas_evo = request.POST.getlist("evolucion[]")
            sintomas_frec = request.POST.getlist("frecuencia[]")
            sintomas_grav = request.POST.getlist("gravedad[]")
            sintomas_obs = request.POST.getlist("observaciones_sintoma[]")

            for i, tipo in enumerate(sintomas_tipo):
                SintomaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    cuando_inicio=sintomas_inicio[i]
                    if i < len(sintomas_inicio)
                    else "",
                    evolucion=sintomas_evo[i] if i < len(sintomas_evo) else "",
                    frecuencia=sintomas_frec[i] if i < len(sintomas_frec) else "",
                    gravedad=sintomas_grav[i] if i < len(sintomas_grav) else "",
                    observaciones=sintomas_obs[i] if i < len(sintomas_obs) else "",
                )

            # Síntomas diurnos
            anamnesis.sintomas_diurno.all().delete()
            sintomasd_tipo = request.POST.getlist("tipo_sintoma_diurno[]")
            sintomasd_inicio = request.POST.getlist("cuando_inicio_diurno[]")
            sintomasd_evo = request.POST.getlist("evolucion_diurno[]")
            sintomasd_frec = request.POST.getlist("frecuencia_diurno[]")
            sintomasd_grav = request.POST.getlist("gravedad_diurno[]")
            sintomasd_obs = request.POST.getlist("observaciones_sintoma_diurno[]")

            for i, tipo in enumerate(sintomasd_tipo):
                SintomaDiurnoSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    cuando_inicio=sintomasd_inicio[i]
                    if i < len(sintomasd_inicio)
                    else "",
                    evolucion=sintomasd_evo[i] if i < len(sintomasd_evo) else "",
                    frecuencia=sintomasd_frec[i] if i < len(sintomasd_frec) else "",
                    gravedad=sintomasd_grav[i] if i < len(sintomasd_grav) else "",
                    observaciones=sintomasd_obs[i] if i < len(sintomasd_obs) else "",
                )

            # ==============================
            # Marcar examen como completado
            # ==============================
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "Anamnesis de sueño guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"Error al guardar la anamnesis: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    messages.error(request, "Método no permitido.")
    return redirect("index")


@login_required
def guardar_atenas(request):
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

            form = AtenasForm(request.POST)
            if form.is_valid():
                AtenasResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala de Atenas guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Atenas: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la escala de Atenas: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_berlin(request):
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

            form = BerlinForm(request.POST)
            if form.is_valid():
                BerlinResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Cuestionario de Berlín guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Berlín: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario de Berlín: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Epworth(request):
    """
    Refactored Epworth view using EpworthForm (ModelForm).

    Before (manual):
      - 8 × request.POST.get() calls with HTML→model name mapping
      - String concatenation for puntaje_total (bug: "0"+"0" = "00")
      - Manual update_or_create with 9-field defaults dict

    After (form-based):
      - EpworthForm handles HTML→model field mapping in __init__
      - Scoring is computed correctly (int sum) in clean()
      - form.is_valid() provides built-in validation
      - update_or_create uses form.cleaned_data
    """
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Validate via ModelForm (handles HTML field name mapping + scoring)
            form = EpworthForm(request.POST)
            if form.is_valid():
                EpworthResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                # Marcar como completado
                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala de Epworth guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                # Form validation failed — show errors
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(
                    request,
                    f"❌ Error de validación en Epworth: {error_msgs}",
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
                request, f"❌ Error al guardar la escala de Epworth: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_ISI(request):
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

            form = ISIForm(request.POST)
            if form.is_valid():
                ISIResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Índice de Severidad del Insomnio (ISI) guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en ISI: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el ISI: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_MEW(request):
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

            form = MEWForm(request.POST)
            if form.is_valid():
                MEWResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                puntuacion = form.cleaned_data.get("puntuacion", 0)
                tipo = form.cleaned_data.get("tipo_persona", "")
                messages.success(
                    request,
                    f"✅ Cuestionario MEW guardado exitosamente. "
                    f"Puntuación: {puntuacion}/86 - {tipo}",
                )
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en MEW: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario MEW: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Pitsburg(request):
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

            form = PittsburghForm(request.POST)
            if form.is_valid():
                PittsburghResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Cuestionario de Pittsburgh guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Pittsburgh: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario de Pittsburgh: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_StopBang(request):
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

            form = StopBangForm(request.POST)
            if form.is_valid():
                StopBangResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Cuestionario STOP-BANG guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en STOP-BANG: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario STOP-BANG: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


### Anosognosia


