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

from ..tokens import generar_token_paciente, validar_token_paciente
from ..services.visita_sueno import resolver_visita_examen_publico

logger = logging.getLogger(__name__)


def _visita_id_from_request(request):
    params = request.GET if request.method == "GET" else request.POST
    raw = params.get("visita_id")
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _cargar_formulario_examen_publico(
    request,
    paciente,
    examen_id,
    examen_tipo_label,
    template_name,
    extra_context=None,
    result_model=None,
):
    """GET compartido: resuelve visita/examen y renderiza formulario o completado."""
    visita_id = _visita_id_from_request(request)
    try:
        visita, visita_examen = resolver_visita_examen_publico(
            paciente, examen_id, visita_id=visita_id
        )
    except Visita.DoesNotExist:
        messages.error(request, "❌ No se encontró la visita asociada.")
        return redirect("formulario_demografico_externo")

    if visita_examen.visita.paciente_id != paciente.id:
        messages.error(request, "❌ La visita no corresponde a este paciente.")
        return redirect("formulario_demografico_externo")

    if visita_examen.estado == "completado":
        messages.info(
            request, "ℹ️ Este examen ya ha sido completado anteriormente."
        )
        return render(
            request,
            "registro_publico/examen_completado.html",
            {"examen_tipo": examen_tipo_label, "paciente": paciente},
        )

    if visita_examen.estado == "pendiente":
        visita_examen.estado = "en_progreso"
        visita_examen.fecha_inicio = timezone.now()
        visita_examen.save()

    context = {
        "paciente": paciente,
        "visita": visita,
        "visita_examen": visita_examen,
        "token": generar_token_paciente(paciente.id),
        "visita_id": visita.id,
    }
    if result_model:
        context["datos_examen"] = _datos_examen_existente(result_model, visita_examen)
    if extra_context:
        context.update(extra_context)
    return render(request, template_name, context)


def _datos_examen_existente(result_model, visita_examen):
    try:
        resultado = result_model.objects.get(visita_examen=visita_examen)
        datos = model_to_dict(resultado)
        datos.pop("id", None)
        datos.pop("visita_examen", None)
        return datos
    except result_model.DoesNotExist:
        return None


def _visita_examen_desde_post(request, paciente, examen_id):
    """Resuelve VisitaExamen en POST validando paciente y visita_id."""
    visita_id = _visita_id_from_request(request)
    if visita_id is None:
        raise ValueError("Falta visita_id en el formulario.")

    visita, visita_examen = resolver_visita_examen_publico(
        paciente, examen_id, visita_id=visita_id
    )
    if visita_examen.visita.paciente_id != paciente.id:
        raise PermissionError("La visita no corresponde a este paciente.")
    if visita_examen.estado == "completado":
        raise ValueError("Este examen ya fue completado.")
    return visita_examen


def _validar_acceso_publico(request):
    """Shared access validation for public exam endpoints.

    Accepts ``token`` (signed, preferred) **or** ``paciente_id`` (legacy).
    Returns ``(paciente, error_message)``.
    """
    if request.method == "GET":
        params = request.GET
    else:
        params = request.POST

    # --- Prefer signed token ---
    token = params.get("token")
    if token:
        paciente_id = validar_token_paciente(token)
        if paciente_id is None:
            return None, "❌ Enlace inválido o expirado. Solicite uno nuevo."
        try:
            paciente = DatosDemograficos.objects.get(id=paciente_id)
            return paciente, None
        except DatosDemograficos.DoesNotExist:
            return None, "❌ Paciente no encontrado."

    # --- Legacy fallback: raw paciente_id (deprecated) ---
    paciente_id_raw = params.get("paciente_id")
    if paciente_id_raw:
        logger.warning(
            "Acceso público con paciente_id sin firmar (deprecated) id=%s uri=%s",
            paciente_id_raw,
            request.path,
        )
        try:
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id_raw)
            return paciente, None
        except Exception as e:
            return None, f"❌ Error al validar acceso: {str(e)}"

    return None, "❌ Datos de acceso incompletos."

def guardar_examen_publico_epworth(request):
    """Cargar y guardar examen Epworth desde enlace público"""

    # Validar acceso (token firmado o paciente_id legacy)
    paciente, error = _validar_acceso_publico(request)
    if error:
        messages.error(request, error)
        return redirect("formulario_demografico_externo")

    if request.method == "GET":
        return _cargar_formulario_examen_publico(
            request,
            paciente,
            examen_id=14,
            examen_tipo_label="Escala de Epworth",
            template_name="registro_publico/epworth_publico.html",
        )

    elif request.method == "POST":
        # GUARDAR RESULTADOS
        try:
            visita_examen = _visita_examen_desde_post(request, paciente, examen_id=14)

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

        except PermissionError as e:
            messages.error(request, f"❌ {e}")
            return redirect("formulario_demografico_externo")
        except ValueError as e:
            messages.error(request, f"❌ {e}")
            return redirect("formulario_demografico_externo")
        except Exception as e:
            messages.error(request, f"❌ Error al guardar el examen: {str(e)}")
            return redirect("formulario_demografico_externo")

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("formulario_demografico_externo")


def guardar_examen_publico_mew(request):
    """Cargar y guardar examen MEW desde enlace público"""

    # Validar acceso (token firmado o paciente_id legacy)
    paciente, error = _validar_acceso_publico(request)
    if error:
        messages.error(request, error)
        return redirect("formulario_demografico_externo")

    if request.method == "GET":
        return _cargar_formulario_examen_publico(
            request,
            paciente,
            examen_id=16,
            examen_tipo_label="Cuestionario MEW",
            template_name="registro_publico/mew_publico.html",
            result_model=MEWResult,
        )

    elif request.method == "POST":
        try:
            visita_examen = _visita_examen_desde_post(request, paciente, examen_id=16)

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
                    f"/guardar-examen-publico-mew/?token={generar_token_paciente(paciente.id)}&visita_id={visita_examen.visita_id}"
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

        except PermissionError as e:
            messages.error(request, f"❌ {e}")
            return redirect("formulario_demografico_externo")
        except ValueError as e:
            messages.error(request, f"❌ {e}")
            return redirect("formulario_demografico_externo")
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

    # Validar acceso (token firmado o paciente_id legacy)
    paciente, error = _validar_acceso_publico(request)
    if error:
        messages.error(request, error)
        return redirect("formulario_demografico_externo")

    if request.method == "GET":
        return _cargar_formulario_examen_publico(
            request,
            paciente,
            examen_id=13,
            examen_tipo_label="Cuestionario de Pittsburgh",
            template_name="registro_publico/Pitsburg_publico.html",
            result_model=PittsburghResult,
            extra_context={
                "paciente_id": paciente.id,
                "examen_id": 13,
            },
        )

    elif request.method == "POST":
        print("POST DATA:", request.POST)
        # GUARDAR RESULTADOS
        try:
            visita_examen = _visita_examen_desde_post(request, paciente, examen_id=13)

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
    print ("Datos de sesión en confirmación:", datos_sesion)

    mostrar_examenes_sueno = False

    if proyecto_id:
        proyecto = Proyecto.objects.filter(id=proyecto_id).first()
        if proyecto and proyecto.id == 11 :
            mostrar_examenes_sueno = True

    context = {
        "datos": datos_sesion,
        "mostrar_examenes_sueno": mostrar_examenes_sueno,
    }

    return render(request, "registro_publico/successfullyRegistered.html", context)

# ===== FUNCIONES AUXILIARES =====


def get_interpretacion_epworth(puntaje):
    """Devuelve la interpretación del puntaje Epworth (escala D-16)."""
    from apps.home.services.exam_scoring import interpretar_epworth

    return interpretar_epworth(puntaje)


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
