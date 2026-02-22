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
from ..forms import ProyectoForm, RegistroDemograficoForm
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

def guardar_examen_publico_epworth(request):
    """Cargar y guardar examen Epworth desde enlace público"""

    # Función auxiliar para validar acceso
    def validar_acceso():
        if request.method == "GET":
            paciente_id = request.GET.get("paciente_id")
        else:
            paciente_id = request.POST.get("paciente_id")

        if not paciente_id:
            return None, "❌ Datos de acceso incompletos."

        try:
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
            return paciente, None
        except Exception as e:
            return None, f"❌ Error al validar acceso: {str(e)}"

    # Validar acceso
    paciente, error = validar_acceso()
    if error:
        messages.error(request, error)
        return redirect("formulario_demografico_externo")

    if request.method == "GET":
        # MOSTRAR FORMULARIO
        try:
            # Buscar visita automática
            visita = Visita.objects.filter(
                paciente=paciente, nombre="VISITA EPWORTH/MEW", Tipo_visita_id=7
            ).first()

            if not visita:
                messages.error(request, "❌ No se encontró la visita asociada.")
                return redirect("formulario_demografico_externo")

            # Buscar o crear VisitaExamen para Epworth
            visita_examen = VisitaExamen.objects.filter(
                visita=visita,
                examen_id=14,  # ID del examen Epworth
            ).first()

            if not visita_examen:
                # Crear el VisitaExamen si no existe
                examen_epworth = Examen.objects.get(id=14)
                visita_examen = VisitaExamen.objects.create(
                    visita=visita, examen=examen_epworth, estado="pendiente"
                )

            # Verificar si ya fue completado
            if visita_examen.estado == "completado":
                messages.info(
                    request, "ℹ️ Este examen ya ha sido completado anteriormente."
                )
                return render(
                    request,
                    "registro_publico/examen_completado.html",
                    {"examen_tipo": "Escala de Epworth", "paciente": paciente},
                )

            # Marcar como iniciado
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            context = {
                "paciente": paciente,
                "visita": visita,
                "visita_examen": visita_examen,
            }

            return render(request, "registro_publico/epworth_publico.html", context)

        except Exception as e:
            messages.error(request, f"❌ Error al cargar el examen: {str(e)}")
            return redirect("formulario_demografico_externo")

    elif request.method == "POST":
        # GUARDAR RESULTADOS
        try:
            visita_id = request.POST.get("visita_id")
            examen_id = 14  # ID fijo para Epworth

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Obtener las respuestas
            sentado_leyendo = int(request.POST.get("epworth_leyendo", "0"))
            viendo_tv = int(request.POST.get("epworth_tv", "0"))
            sentado_teatro = int(request.POST.get("epworth_teatro", "0"))
            pasajero_coche = int(request.POST.get("epworth_pasajero", "0"))
            tumbado_tarde = int(request.POST.get("epworth_tumbado", "0"))
            charlando = int(request.POST.get("epworth_charlando", "0"))
            despues_comer = int(request.POST.get("epworth_comida", "0"))
            trafico = int(request.POST.get("epworth_trafico", "0"))

            # Calcular puntuación total
            puntaje_total = (
                sentado_leyendo
                + viendo_tv
                + sentado_teatro
                + pasajero_coche
                + tumbado_tarde
                + charlando
                + despues_comer
                + trafico
            )

            # Crear o actualizar el resultado
            epworth, created = EpworthResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "sentado_leyendo": sentado_leyendo,
                    "viendo_tv": viendo_tv,
                    "sentado_teatro": sentado_teatro,
                    "pasajero_coche": pasajero_coche,
                    "tumbado_tarde": tumbado_tarde,
                    "charlando": charlando,
                    "despues_comer": despues_comer,
                    "trafico": trafico,
                    "puntaje_total": puntaje_total,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Mensaje de éxito y redirección a página pública
            messages.success(
                request,
                f"✅ Examen Epworth completado exitosamente. Puntaje: {puntaje_total}",
            )

            return render(
                request,
                "registro_publico/examen_completado_exitoso.html",
                {
                    "examen_tipo": "Escala de Somnolencia de Epworth",
                    "paciente": paciente,
                    "puntaje": puntaje_total,
                    "interpretacion": get_interpretacion_epworth(puntaje_total),
                },
            )

        except Exception as e:
            messages.error(request, f"❌ Error al guardar el examen: {str(e)}")
            return redirect("formulario_demografico_externo")

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("formulario_demografico_externo")


def guardar_examen_publico_mew(request):
    """Cargar y guardar examen MEW desde enlace público"""

    def validar_acceso():
        if request.method == "GET":
            paciente_id = request.GET.get("paciente_id")
        else:
            paciente_id = request.POST.get("paciente_id")

        if not paciente_id:
            return None, "❌ Datos de acceso incompletos."

        try:
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
            return paciente, None
        except Exception as e:
            return None, f"❌ Error al validar acceso: {str(e)}"

    # Validar acceso
    paciente, error = validar_acceso()
    if error:
        messages.error(request, error)
        return redirect("formulario_demografico_externo")

    if request.method == "GET":
        # MOSTRAR FORMULARIO
        try:
            # Buscar visita automática
            visita = Visita.objects.filter(
                paciente=paciente, nombre="VISITA EPWORTH/MEW", Tipo_visita_id=7
            ).first()

            if not visita:
                messages.error(request, "❌ No se encontró la visita asociada.")
                return redirect("formulario_demografico_externo")

            # Buscar o crear VisitaExamen para MEW
            visita_examen = VisitaExamen.objects.filter(
                visita=visita,
                examen_id=16,  # ID del examen MEW
            ).first()

            if not visita_examen:
                # Crear el VisitaExamen si no existe
                examen_mew = Examen.objects.get(id=16)
                visita_examen = VisitaExamen.objects.create(
                    visita=visita, examen=examen_mew, estado="pendiente"
                )

            # Verificar si ya fue completado
            if visita_examen.estado == "completado":
                messages.info(
                    request, "ℹ️ Este examen ya ha sido completado anteriormente."
                )
                return render(
                    request,
                    "registro_publico/examen_completado.html",
                    {"examen_tipo": "Cuestionario MEW", "paciente": paciente},
                )

            # Marcar como iniciado
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Buscar datos existentes si los hay
            datos_examen = None
            try:
                resultado_existente = MEWResult.objects.get(visita_examen=visita_examen)
                datos_examen = model_to_dict(resultado_existente)
                datos_examen.pop("id", None)
                datos_examen.pop("visita_examen", None)
            except MEWResult.DoesNotExist:
                datos_examen = None

            context = {
                "paciente": paciente,
                "visita": visita,
                "visita_examen": visita_examen,
                "datos_examen": datos_examen,
            }

            return render(request, "registro_publico/mew_publico.html", context)

        except Exception as e:
            messages.error(request, f"❌ Error al cargar el examen: {str(e)}")
            return redirect("formulario_demografico_externo")

    elif request.method == "POST":
        try:
            # Recuperar paciente otra vez
            paciente_id = request.POST.get("paciente_id")
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)

            visita_id = request.POST.get("visita_id")
            examen_id = 16  # ID fijo para MEW

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Obtener la puntuación calculada en el frontend
            puntuacion_frontend = request.POST.get("puntuacion", "0")
            try:
                puntuacion_calculada = int(puntuacion_frontend)
            except (ValueError, TypeError):
                puntuacion_calculada = 0

            # Validar que la puntuación esté en rango válido
            if puntuacion_calculada < 16 or puntuacion_calculada > 86:
                messages.error(
                    request, "❌ Error: Puntuación MEQ fuera del rango válido (16-86)."
                )
                return redirect(
                    f"/guardar-examen-publico-mew/?paciente_id={paciente.id}"
                )

            # Obtener campos del formulario MEW (usando nombres del formulario HTML)
            # Mapear nombres del formulario a nombres del modelo
            hora_levantarse = request.POST.get("hora_levantarse_meq", "")
            hora_acostarse = request.POST.get("hora_acostarse_meq", "")
            uso_despertador = request.POST.get("uso_despertador_meq", "")
            facilidad_levantarse = request.POST.get("facilidad_levantarse_meq", "")
            alerta_manana = request.POST.get("alerta_manana_meq", "")
            apetito_manana = request.POST.get("apetito_manana_meq", "")
            descanso_manana = request.POST.get("descanso_manana_meq", "")
            hora_acostarse_libre = request.POST.get("hora_acostarse_libre_meq", "")
            ejercicio_manana = request.POST.get("ejercicio_manana_meq", "")
            hora_cansancio_noche = request.POST.get("hora_cansancio_noche_meq", "")
            prueba_mental = request.POST.get("prueba_mental_meq", "")
            cansancio_11pm = request.POST.get("cansancio_11pm_meq", "")
            despertar_tarde = request.POST.get("despertar_tarde_meq", "")
            guardia_nocturna = request.POST.get("guardia_nocturna_meq", "")
            trabajo_fisico = request.POST.get("trabajo_fisico_meq", "")
            ejercicio_nocturno = request.POST.get("ejercicio_nocturno_meq", "")
            horario_trabajo = request.POST.get("horario_trabajo_meq", "")
            maximo_bienestar = request.POST.get("maximo_bienestar_meq", "")
            tipo_persona = request.POST.get("tipo_persona_meq", "")

            # Los campos que se mantienen del modelo anterior
            ejercicio_fisico = request.POST.get("ejercicio_fisico_meq", "")
            nivel_cansancia_11 = request.POST.get("nivel_cansancia_11", "")
            hora_despertarse_si_tarde = request.POST.get(
                "hora_despertarse_si_tarde", ""
            )
            horario_trabajo_fisico = request.POST.get("horario_trabajo_fisico", "")

            # Determinar cronotipo basado en la puntuación
            if puntuacion_calculada >= 70:
                tipo_persona_calculado = "Matutino Definido"
            elif puntuacion_calculada >= 59:
                tipo_persona_calculado = "Moderadamente Matutino"
            elif puntuacion_calculada >= 42:
                tipo_persona_calculado = "Intermedio"
            elif puntuacion_calculada >= 31:
                tipo_persona_calculado = "Moderadamente Vespertino"
            else:
                tipo_persona_calculado = "Vespertino Definido"

            # Crear o actualizar el resultado usando los nombres EXACTOS del modelo
            mew_result, created = MEWResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Nombres exactos del modelo (sin sufijo _meq)
                    "hora_levantarse": hora_levantarse,
                    "hora_acostarse": hora_acostarse,
                    "uso_despertador": uso_despertador,
                    "facilidad_levantarse": facilidad_levantarse,
                    "alerta_manana": alerta_manana,
                    "apetito_manana": apetito_manana,
                    "descanso_manana": descanso_manana,
                    "hora_acostarse_libre": hora_acostarse_libre,
                    "ejercicio_manana": ejercicio_manana,
                    "ejercicio_fisico": ejercicio_fisico,
                    "hora_cansancio_noche": hora_cansancio_noche,
                    "nivel_cansancia_11": nivel_cansancia_11,
                    "prueba_mental": prueba_mental,
                    "cansancio_11pm": cansancio_11pm,
                    "despertar_tarde": despertar_tarde,
                    "hora_despertarse_si_tarde": hora_despertarse_si_tarde,
                    "guardia_nocturna": guardia_nocturna,
                    "horario_trabajo_fisico": horario_trabajo_fisico,
                    "trabajo_fisico": trabajo_fisico,
                    "ejercicio_nocturno": ejercicio_nocturno,
                    "horario_trabajo": horario_trabajo,
                    "maximo_bienestar": maximo_bienestar,
                    "tipo_persona": tipo_persona or tipo_persona_calculado,
                    "puntuacion": puntuacion_calculada,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Mensaje de éxito y redirección a página pública
            messages.success(
                request,
                f"✅ Examen MEQ completado exitosamente. Puntuación: {puntuacion_calculada}/86 - {tipo_persona_calculado}",
            )

            return render(
                request,
                "registro_publico/examen_completado_exitoso.html",
                {
                    "examen_tipo": "Cuestionario de Matutinidad-Vespertinidad (MEQ)",
                    "paciente": paciente,
                    "puntaje": puntuacion_calculada,
                    "interpretacion": tipo_persona_calculado,
                    "rango_puntuacion": "16-86 puntos",
                    "descripcion_resultado": obtener_descripcion_cronotipo(
                        puntuacion_calculada
                    ),
                },
            )

        except Exception as e:
            messages.error(request, f"❌ Error al guardar el examen: {str(e)}")
            return redirect("formulario_demografico_externo")

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("formulario_demografico_externo")


def obtener_descripcion_cronotipo(puntuacion):
    """Devuelve una descripción detallada del cronotipo según la puntuación MEQ"""
    if puntuacion >= 70:
        return "Persona claramente matutina: Prefiere levantarse y acostarse temprano, con mayor energía en las mañanas."
    elif puntuacion >= 59:
        return "Persona moderadamente matutina: Tendencia a ser más activo en las mañanas que en las noches."
    elif puntuacion >= 42:
        return "Persona intermedia: No muestra una preferencia marcada por las mañanas o las noches."
    elif puntuacion >= 31:
        return "Persona moderadamente vespertina: Tendencia a ser más activo en las noches que en las mañanas."
    else:
        return "Persona claramente vespertina: Prefiere acostarse y levantarse tarde, con mayor energía en las noches."


def guardar_examen_publico_pitsburg(request):
    """Cargar y guardar examen Pittsburgh desde enlace público"""

    # Función auxiliar para validar acceso
    def validar_acceso():
        if request.method == "GET":
            paciente_id = request.GET.get("paciente_id")
        else:
            paciente_id = request.POST.get("paciente_id")

        if not paciente_id:
            return None, "❌ Datos de acceso incompletos."

        try:
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
            return paciente, None
        except Exception as e:
            return None, f"❌ Error al validar acceso: {str(e)}"

    # Validar acceso
    paciente, error = validar_acceso()
    if error:
        messages.error(request, error)
        return redirect("formulario_demografico_externo")

    if request.method == "GET":
        # MOSTRAR FORMULARIO
        try:
            # Buscar visita automática
            visita = Visita.objects.filter(
                paciente=paciente, nombre="VISITA EPWORTH/MEW", Tipo_visita_id=7
            ).first()

            if not visita:
                messages.error(request, "❌ No se encontró la visita asociada.")
                return redirect("formulario_demografico_externo")

            # Buscar o crear VisitaExamen para Pittsburgh
            visita_examen = VisitaExamen.objects.filter(
                visita=visita,
                examen_id=13,  # ID del examen Pittsburgh
            ).first()

            if not visita_examen:
                # Crear el VisitaExamen si no existe
                examen_pitsburg = Examen.objects.get(id=13)
                visita_examen = VisitaExamen.objects.create(
                    visita=visita, examen=examen_pitsburg, estado="pendiente"
                )

            # Verificar si ya fue completado
            if visita_examen.estado == "completado":
                messages.info(
                    request, "ℹ️ Este examen ya ha sido completado anteriormente."
                )
                return render(
                    request,
                    "registro_publico/examen_completado.html",
                    {"examen_tipo": "Cuestionario de Pittsburgh", "paciente": paciente},
                )

            # Marcar como iniciado
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Buscar datos existentes si los hay
            datos_examen = None
            try:
                resultado_existente = PittsburghResult.objects.get(
                    visita_examen=visita_examen
                )
                datos_examen = model_to_dict(resultado_existente)
                datos_examen.pop("id", None)
                datos_examen.pop("visita_examen", None)
            except PittsburghResult.DoesNotExist:
                datos_examen = None

            context = {
                "paciente": paciente,
                "visita": visita,
                "visita_examen": visita_examen,
                "datos_examen": datos_examen,
                "paciente_id": paciente.id,
                "examen_id": 13,
            }

            return render(request, "registro_publico/Pitsburg_publico.html", context)

        except Exception as e:
            messages.error(request, f"❌ Error al cargar el examen: {str(e)}")
            return redirect("formulario_demografico_externo")

    elif request.method == "POST":
        print("POST DATA:", request.POST)
        # GUARDAR RESULTADOS
        try:
            visita_id = request.POST.get("visita_id")
            examen_id = 13  # ID fijo para Pittsburgh

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Obtener los campos según los NOMBRES EXACTOS del modelo PittsburghResult
            hora_acostarse = request.POST.get("hora_acostarse", "")
            hora_levantarse = request.POST.get("hora_levantarse", "")
            latencia_sueno = request.POST.get("latencia_sueno", "")
            horas_dormidas = request.POST.get("horas_sueno_real", "0")

            # Problemas durante el sueño
            conciliar_sueno = request.POST.get("conciliar_sueno", "")
            despertarse_sueno = request.POST.get("despertarse_sueno", "")
            levantarse_servicio_sueno = request.POST.get(
                "levantarse_servicio_sueno", ""
            )
            respirar = request.POST.get("respirar", "")
            toser_roncar_sueno = request.POST.get("toser_roncar_sueno", "")
            sentir_frio_sueno = request.POST.get("sentir_frio_sueno", "")
            calor_sueno = request.POST.get("calor_sueno", "")
            pesadillas_sueno = request.POST.get("pesadillas_sueno", "")
            dolores_sueno = request.POST.get("dolores_sueno", "")
            otras_razones = request.POST.get("otras_razones", "")
            otras_sueno = request.POST.get("otras_sueno", "")

            # Evaluación general
            calidad_sueno = request.POST.get("calidad_sueno", "")
            medicinas_sueno = request.POST.get("medicinas_sueno", "")
            somnolencia_sueno = request.POST.get("somnolencia_sueno", "")
            problemas_animos_sueno = request.POST.get("problemas_animos_sueno", "")

            # Información de compañía
            duerme_acompanado = request.POST.get("duerme_acompanado", "")
            ronquidos_ruidosos = request.POST.get("ronquidos_ruidosos", "")
            pausas_respiracion = request.POST.get("pausas_respiracion", "")
            sacudidas_piernas = request.POST.get("sacudidas_piernas", "")
            desorientacion_confusion = request.POST.get("desorientacion_confusion", "")
            descripcion_inconvenientes = request.POST.get(
                "descripcion_inconvenientes", ""
            )
            otros_inconvenientes = request.POST.get("otros_inconvenientes", "")
            puntuacion_total = request.POST.get("puntuacion_total", "0")

            # Crear o actualizar el resultado Pittsburgh
            pitsburg_result, created = PittsburghResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos de tiempo
                    "hora_acostarse": hora_acostarse,
                    "hora_levantarse": hora_levantarse,
                    "latencia_sueno": latencia_sueno,
                    "horas_dormidas": horas_dormidas,
                    # Problemas durante el sueño
                    "conciliar_sueno": conciliar_sueno,
                    "despertarse_sueno": despertarse_sueno,
                    "levantarse_servicio_sueno": levantarse_servicio_sueno,
                    "respirar": respirar,
                    "toser_roncar_sueno": toser_roncar_sueno,
                    "sentir_frio_sueno": sentir_frio_sueno,
                    "calor_sueno": calor_sueno,
                    "pesadillas_sueno": pesadillas_sueno,
                    "dolores_sueno": dolores_sueno,
                    "otras_razones": otras_razones,
                    "otras_sueno": otras_sueno,
                    # Evaluación general
                    "calidad_sueno": calidad_sueno,
                    "medicinas_sueno": medicinas_sueno,
                    "somnolencia_sueno": somnolencia_sueno,
                    "problemas_animos_sueno": problemas_animos_sueno,
                    # Información de compañía
                    "duerme_acompanado": duerme_acompanado,
                    "ronquidos_ruidosos": ronquidos_ruidosos,
                    "pausas_respiracion": pausas_respiracion,
                    "sacudidas_piernas": sacudidas_piernas,
                    "desorientacion_confusion": desorientacion_confusion,
                    "descripcion_inconvenientes": descripcion_inconvenientes,
                    "otros_inconvenientes": otros_inconvenientes,
                    "puntuacion_total": puntuacion_total,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Mensaje de éxito y redirección a página pública
            messages.success(
                request,
                f"✅ Cuestionario de Pittsburgh completado exitosamente.",
            )

            return render(
                request,
                "registro_publico/examen_completado_exitoso.html",
                {
                    "examen_tipo": "Cuestionario de Calidad de Sueño de Pittsburgh",
                    "paciente": paciente,
                    "interpretacion": f"Calidad de sueño reportada: {calidad_sueno}",
                },
            )

        except Exception as e:
            messages.error(request, f"❌ Error al guardar el examen: {str(e)}")
            return redirect("formulario_demografico_externo")

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("formulario_demografico_externo")


def confirmacion_registro_externo(request):
    datos_sesion = request.session.get("registro_completado")
    if not datos_sesion:
        return redirect("formulario_demografico_externo")

    proyecto_id = datos_sesion.get("proyecto_id")

    mostrar_examenes_sueno = False

    if proyecto_id:
        proyecto = Proyecto.objects.filter(id=proyecto_id).first()
        if proyecto and proyecto.nombre_visita_automatica == 'Caracterización sueño':
            mostrar_examenes_sueno = True

    context = {
        "datos": datos_sesion,
        "mostrar_examenes_sueno": mostrar_examenes_sueno,
    }

    return render(request, "registro_publico/successfullyRegistered.html", context)

# ===== FUNCIONES AUXILIARES =====


def get_interpretacion_epworth(puntaje):
    """Devuelve la interpretación del puntaje Epworth"""
    if puntaje <= 6:
        return "Somnolencia normal"
    elif puntaje <= 10:
        return "Somnolencia leve"
    elif puntaje <= 15:
        return "Somnolencia moderada"
    else:
        return "Somnolencia severa"


def calcular_puntuacion_mew_publico(post_data):
    """Calcula la puntuación MEW desde datos del formulario público"""
    puntuacion = 0

    # Implementar lógica de cálculo MEW según las respuestas
    # (Esta es una versión simplificada, debes implementar la lógica completa)

    # Ejemplo de algunos cálculos
    hora_lev = post_data.get("hora_levantarse_meq", "")
    if "5:00-6:30" in hora_lev:
        puntuacion += 5
    elif "6:30-7:45" in hora_lev:
        puntuacion += 4
    elif "7:45-9:45" in hora_lev:
        puntuacion += 3
    elif "9:45-11:00" in hora_lev:
        puntuacion += 2
    elif "11:00" in hora_lev:
        puntuacion += 1

    # Continuar con el resto de preguntas...
    # (Implementar toda la lógica de cálculo MEW)

    return min(puntuacion, 86)  # Máximo 86 puntos


# visitas del paciente
