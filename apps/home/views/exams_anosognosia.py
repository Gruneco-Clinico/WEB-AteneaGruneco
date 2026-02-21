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

@login_required
def guardar_examen_Participante_EuroQoL(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener las respuestas del formulario
            movilidad = request.POST.get("movilidad")
            cuidado_personal = request.POST.get("cuidado_personal")
            actividades = request.POST.get("actividades")
            dolor = request.POST.get("dolor")
            ansiedad = request.POST.get("ansiedad")

            # Crear o actualizar el resultado del EuroQol
            euroqol, created = EuroQol5D5LResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "movilidad": movilidad,
                    "cuidado_personal": cuidado_personal,
                    "actividades": actividades,
                    "dolor": dolor,
                    "ansiedad": ansiedad,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Cuestionario EuroQol-5D-5L guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el cuestionario EuroQol-5D-5L: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_LawtonBrody(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Buscar la visita-examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Si está pendiente, lo pasamos a en progreso
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Extraer respuestas
            genero = request.POST.get("genero")

            usar_telefono = request.POST.get("usar_telefono_text")
            hacer_compras = request.POST.get("hacer_compras_text")
            preparar_comida = request.POST.get("preparar_comida_text")
            cuidado_casa = request.POST.get("cuidado_casa_text")
            lavar_ropa = request.POST.get("lavar_ropa_text")
            uso_transporte = request.POST.get("uso_transporte_text")
            medicacion = request.POST.get("medicacion_text")
            manejo_dinero = request.POST.get("manejo_dinero_text")

            puntaje_total = request.POST.get("total")
            diagnostico = request.POST.get("diagnostico")

            # Guardar o actualizar resultado
            lawtonbrody, created = LawtonBrodyResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "genero": genero,
                    "usar_telefono": usar_telefono,
                    "hacer_compras": hacer_compras,
                    "preparar_comida": preparar_comida,
                    "cuidado_casa": cuidado_casa,
                    "lavar_ropa": lavar_ropa,
                    "uso_transporte": uso_transporte,
                    "medicacion": medicacion,
                    "manejo_dinero": manejo_dinero,
                    "puntaje_total": puntaje_total,
                    "diagnostico": diagnostico,
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Escala de Lawton y Brody guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el examen Lawton y Brody: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_Yesavage(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Extraer respuestas
            campos = [
                "satisfaccion_vida",
                "disminuir_actividades",
                "vida_vacia",
                "aburrido_frecuente",
                "buen_animo",
                "preocupacion",
                "felicidad",
                "frecuencia_desamparado",
                "quedarse_casa",
                "problemas_memoria",
                "maravilla_vivir",
                "inutil",
                "lleno_energia",
                "sin_esperanza",
                "otras_personas_mejor",
            ]
            respuestas = {campo: request.POST.get(campo) for campo in campos}

            puntaje_total = request.POST.get("puntaje_total")
            interpretacion = request.POST.get("interpretacion")

            # Guardar en la BD
            yesavage, created = ParticipanteYesavageResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    **respuestas,
                    "puntaje_total": puntaje_total,
                    "interpretacion": interpretacion,
                },
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Escala de Depresión Geriátrica de Yesavage guardada exitosamente.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hay error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el examen de Yesavage: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_EVA_EuroQoL(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener el valor del termómetro
            termometro_estado_salud = request.POST.get("termometro_estado_salud")

            # Crear o actualizar el resultado
            evaeuroqol, created = EuroQolEVASaludResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "termometro_estado_salud": termometro_estado_salud,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Autovaloración del Estado de Salud (EVA EuroQol) guardada exitosamente.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar la Autovaloración del Estado de Salud (EVA EuroQol): {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_NPI(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Lista de ítems del NPI
            items = [
                "ideas_delirantes",
                "alucinaciones",
                "agitacion",
                "depresion",
                "ansiedad",
                "euforia",
                "apatia",
                "desinhibicion",
                "irritabilidad",
                "conducta_motor",
                "sueno",
                "apetito",
            ]

            data = {}
            for item in items:
                data[item] = request.POST.get(item)

                # frec = request.POST.get(f"{item}_frecuencia") or request.POST.get(f"{item}_frecuencia_texto")
                # grav = request.POST.get(f"{item}_gravedad") or request.POST.get(f"{item}_gravedad_texto")
                # dist = request.POST.get(f"{item}_distres") or request.POST.get(f"{item}_distres_texto")
                # fg = request.POST.get(f"{item}_resultado") or 0

                # data[f"{item}_frecuencia"] = frec
                # data[f"{item}_gravedad"] = grav
                # data[f"{item}_F_G"] = fg
                # data[f"{item}_distres"] = dist
                data[f"{item}_frecuencia"] = request.POST.get(
                    f"{item}_frecuencia_texto"
                )
                data[f"{item}_gravedad"] = request.POST.get(f"{item}_gravedad_texto")
                data[f"{item}_F_G"] = request.POST.get(f"{item}_resultado")
                data[f"{item}_distres"] = request.POST.get(f"{item}_distres_texto")

                data["carga_total"] = request.POST.get("carga_total", 0)

            # Crear o actualizar el resultado del NPI
            npi, created = CuidadorNPIResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=data
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Inventario Neuropsiquiátrico (NPI) guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar el Inventario Neuropsiquiátrico (NPI): {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_AQD(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Buscar la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Cambiar estado si estaba pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos de la escala (30 ítems)
            campos = [
                "recordar_fecha",
                "orientacion_lugares_nuevos",
                "recordar_llamadas",
                "entender_conversacion",
                "firmar",
                "entender_lectura",
                "mantener_orden",
                "recordar_lugar_objetos",
                "escribir",
                "manejar_dinero",
                "orientacion_zona_donde_vive",
                "recordar_citas",
                "pasatiempos",
                "comunicarse_con_gente",
                "calculos_mentales",
                "recordar_compras",
                "contener_orina",
                "entender_pelicula",
                "orientacion_en_casa",
                "hacer_tareas_hogar",
                "comer_solo",
                "realizar_tramites",
                "decisiones_y_adaptacion",
                "egoismo",
                "enojo_menos_paciencia",
                "llorar_con_facilidad",
                "reir_situaciones_inapropiadas",
                "temas_sexuales",
                "falta_de_interes",
                "deprimido",
            ]

            # Extraer respuestas
            respuestas = {campo: request.POST.get(campo + "_texto") for campo in campos}

            # Calcular puntaje total (30 a 120)
            puntaje_total = 0
            for campo in campos:
                try:
                    valor = int(request.POST.get(campo, 0))
                    puntaje_total += valor
                except ValueError:
                    pass

            # Guardar o actualizar registro
            aqdcuidador, created = AQDCuidadorResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    **respuestas,
                    # "puntaje_total": puntaje_total,  # si luego agregas este campo al modelo
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala AQ-D Cuidador guardada correctamente. Puntaje total: {puntaje_total}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la escala AQ-D Cuidador: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_AQD(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Buscar la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos (30 ítems)
            campos = [
                "recordar_fecha",
                "orientacion_lugares_nuevos",
                "recordar_llamadas",
                "entender_conversacion",
                "firmar",
                "entender_lectura",
                "mantener_orden",
                "recordar_lugar_objetos",
                "escribir",
                "manejar_dinero",
                "orientacion_zona_donde_vive",
                "recordar_citas",
                "pasatiempos",
                "comunicarse_con_gente",
                "calculos_mentales",
                "recordar_compras",
                "contener_orina",
                "entender_pelicula",
                "orientacion_en_casa",
                "hacer_tareas_hogar",
                "comer_solo",
                "realizar_tramites",
                "decisiones_y_adaptacion",
                "egoismo",
                "enojo_menos_paciencia",
                "llorar_con_facilidad",
                "reir_situaciones_inapropiadas",
                "temas_sexuales",
                "falta_de_interes",
                "deprimido",
            ]

            # Extraer respuestas
            respuestas = {campo: request.POST.get(campo + "_texto") for campo in campos}

            # Calcular puntaje total
            puntaje_total = 0
            for campo in campos:
                try:
                    valor = int(request.POST.get(campo, 0))
                    puntaje_total += valor
                except ValueError:
                    pass

            # Guardar en BD (update si ya existe)
            aqdparticipante, created = AQDParticipanteResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    **respuestas,
                    # Si luego necesitas un campo en el modelo, lo puedes añadir
                    # "puntaje_total": puntaje_total,
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala AQ-D Participante guardada exitosamente. Puntaje total: {puntaje_total}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si falla
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la escala AQ-D Participante: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Construimos diccionario con TODAS las respuestas
            defaults = {}

            # Iteramos sobre los campos definidos en el modelo
            for field in CDRParticipanteResult._meta.get_fields():
                if field.name in ["id", "visita_examen", "resultadoexamenbase_ptr"]:
                    continue  # ignorar claves y herencia
                if (
                    hasattr(field, "get_internal_type")
                    and field.get_internal_type() == "BooleanField"
                ):
                    defaults[field.name] = bool(request.POST.get(field.name))
                else:
                    value = request.POST.get(field.name)
                    defaults[field.name] = value if value != "" else None

            # Crear o actualizar el resultado
            cdrparticipante, created = CDRParticipanteResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults=defaults,
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Cuestionario CDR - Participante guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar el cuestionario CDR - Participante: {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_MoCA(request):
    if request.method != "POST":
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")

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

        # =============================
        # 1–4 VISUOESPACIAL
        # =============================
        alternancia = int(request.POST.get("alternancia", 0))
        cubo = int(request.POST.get("cubo", 0))
        reloj = int(request.POST.get("reloj", 0))
        denominacion = int(request.POST.get("denominacion", 0))

        # =============================
        # 6 ATENCIÓN
        # =============================
        atencion_secuencia = int(request.POST.get("atencion_secuencia", 0))
        atencion_inversa = int(request.POST.get("atencion_inversa", 0))

        errores_concentracion = int(request.POST.get("errores_concentracion") or 0)
        concentracion_resultado = request.POST.get("concentracion_resultado")

        concentracion_puntos = 1 if concentracion_resultado == "no_fallo" else 0

        sustracciones = sum(
            1 for i in range(1, 6) if request.POST.get(f"sustraccion_{i}")
        )

        if sustracciones == 0:
            sustraccion_puntos = 0
        elif sustracciones == 1:
            sustraccion_puntos = 1
        elif sustracciones in (2, 3):
            sustraccion_puntos = 2
        else:
            sustraccion_puntos = 3

        atencion = (
            atencion_secuencia
            + atencion_inversa
            + concentracion_puntos
            + sustraccion_puntos
        )

        # =============================
        # 7 REPETICIÓN
        # =============================
        repeticion_frase_1 = bool(request.POST.get("frase_1"))
        repeticion_frase_2 = bool(request.POST.get("frase_2"))
        repeticion = int(repeticion_frase_1) + int(repeticion_frase_2)

        # =============================
        # 8 FLUIDEZ
        # =============================
        numero_palabras_fluidez = int(request.POST.get("numero_palabras_fluidez") or 0)
        fluidez = 1 if numero_palabras_fluidez >= 11 else 0

        # =============================
        # 9 ABSTRACCIÓN
        # =============================
        abstraccion = int(request.POST.get("abstraccion", 0))

        # =============================
        # 10 DIFERIDO
        # =============================
        palabras = [
            "palabra_rostro",
            "palabra_seda",
            "palabra_iglesia",
            "palabra_clavel",
            "palabra_rojo",
        ]

        diferido = sum(1 for palabra in palabras if request.POST.get(palabra))

        # =============================
        # 11 ORIENTACIÓN
        # =============================
        orientacion_items = [
            "orientacion_fecha",
            "orientacion_mes",
            "orientacion_anio",
            "orientacion_dia_semana",
            "orientacion_lugar",
            "orientacion_localidad",
        ]

        orientacion = sum(1 for campo in orientacion_items if request.POST.get(campo))

        # =============================
        # ESCOLARIDAD
        # =============================
        educacion_baja = bool(request.POST.get("educacion_baja"))

        # =============================
        # TOTAL
        # =============================
        puntaje_total = (
            alternancia
            + cubo
            + reloj
            + denominacion
            + atencion
            + repeticion
            + fluidez
            + abstraccion
            + diferido
            + orientacion
        )

        if educacion_baja and puntaje_total < 30:
            puntaje_total += 1

        interpretacion = (
            "Puntaje normal (función cognitiva preservada)"
            if puntaje_total >= 26
            else "Posible deterioro cognitivo. Se recomienda evaluación clínica adicional."
        )

        # =============================
        # GUARDAR
        # =============================
        MoCAResult.objects.update_or_create(
            visita_examen=visita_examen,
            defaults={
                "alternancia": alternancia,
                "cubo": cubo,
                "reloj": reloj,
                "denominacion": denominacion,
                "atencion_secuencia": atencion_secuencia,
                "atencion_inversa": atencion_inversa,
                "errores_concentracion": errores_concentracion,
                "concentracion_resultado": concentracion_resultado,
                "sustraccion_1": bool(request.POST.get("sustraccion_1")),
                "sustraccion_2": bool(request.POST.get("sustraccion_2")),
                "sustraccion_3": bool(request.POST.get("sustraccion_3")),
                "sustraccion_4": bool(request.POST.get("sustraccion_4")),
                "sustraccion_5": bool(request.POST.get("sustraccion_5")),
                "atencion": atencion,
                "repeticion_frase_1": repeticion_frase_1,
                "repeticion_frase_2": repeticion_frase_2,
                "repeticion": repeticion,
                "numero_palabras_fluidez": numero_palabras_fluidez,
                "fluidez": fluidez,
                "abstraccion": abstraccion,
                "palabra_rostro": request.POST.get("palabra_rostro") is not None,
                "palabra_seda": request.POST.get("palabra_seda") is not None,
                "palabra_iglesia": request.POST.get("palabra_iglesia") is not None,
                "palabra_clavel": request.POST.get("palabra_clavel") is not None,
                "palabra_rojo": request.POST.get("palabra_rojo") is not None,
                "diferido": diferido,
                "orientacion_fecha": request.POST.get("orientacion_fecha") is not None,
                "orientacion_mes": request.POST.get("orientacion_mes") is not None,
                "orientacion_anio": request.POST.get("orientacion_anio") is not None,
                "orientacion_dia_semana": request.POST.get("orientacion_dia_semana")
                is not None,
                "orientacion_lugar": request.POST.get("orientacion_lugar") is not None,
                "orientacion_localidad": request.POST.get("orientacion_localidad")
                is not None,
                "orientacion": orientacion,
                "educacion_baja": educacion_baja,
                "puntaje_total": puntaje_total,
                "interpretacion": interpretacion,
            },
        )

        visita_examen.estado = "completado"
        visita_examen.fecha_completado = timezone.now()
        visita_examen.save()

        messages.success(
            request,
            f"✅ Escala MoCA guardada correctamente | Puntaje: {puntaje_total}/30",
        )

        return redirect("detalle_paciente", paciente_id=paciente_id)

    except Exception as e:
        messages.error(request, f"❌ Error al guardar MoCA: {str(e)}")
        return redirect("detalle_paciente", paciente_id=paciente_id)


@login_required
def guardar_examen_Cuidador_CDR(request):
    if request.method == "POST":
        print(">>> NIVEL:", request.POST.get("nivel_desempeno_domestico"))
        print(
            ">>> LONGITUD:",
            len(request.POST.get("nivel_desempeno_domestico") or ""),
        )

        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Recoger todos los campos EXACTOS del modelo
            campos = {
                "memoria_p1": request.POST.get("memoria_p1", ""),
                "memoria_p1_1": request.POST.get("memoria_p1_1", ""),
                "memoria_p2": request.POST.get("memoria_p2", ""),
                "memoria_p3": request.POST.get("memoria_p3", ""),
                "memoria_p4": request.POST.get("memoria_p4", ""),
                "memoria_p5": request.POST.get("memoria_p5", ""),
                "memoria_p6": request.POST.get("memoria_p6", ""),
                "memoria_p7": request.POST.get("memoria_p7", ""),
                "memoria_p8": request.POST.get("memoria_p8", ""),
                "evento_recuerda_semana": request.POST.get(
                    "evento_recuerda_semana", ""
                ),
                "evento_recuerda_mes": request.POST.get("evento_recuerda_mes", ""),
                "nacimiento_fecha": request.POST.get("nacimiento_fecha") or None,
                "nacimiento_lugar": request.POST.get("nacimiento_lugar", ""),
                "colegio_nombre": request.POST.get("colegio_nombre", ""),
                "colegio_lugar": request.POST.get("colegio_lugar", ""),
                "colegio_grado": request.POST.get("colegio_grado", ""),
                "ocupacion_principal": request.POST.get("ocupacion_principal", ""),
                "ultimo_trabajo": request.POST.get("ultimo_trabajo", ""),
                "jubilacion": request.POST.get("jubilacion", ""),
                "orientacion_p1": request.POST.get("orientacion_p1", ""),
                "orientacion_p2": request.POST.get("orientacion_p2", ""),
                "orientacion_p3": request.POST.get("orientacion_p3", ""),
                "orientacion_p4": request.POST.get("orientacion_p4", ""),
                "orientacion_p5": request.POST.get("orientacion_p5", ""),
                "orientacion_p6": request.POST.get("orientacion_p6", ""),
                "orientacion_p7": request.POST.get("orientacion_p7", ""),
                "orientacion_p8": request.POST.get("orientacion_p8", ""),
                "juicio_p1": request.POST.get("juicio_p1", ""),
                "juicio_p2": request.POST.get("juicio_p2", ""),
                "juicio_p3": request.POST.get("juicio_p3", ""),
                "juicio_p4": request.POST.get("juicio_p4", ""),
                "juicio_p5": request.POST.get("juicio_p5", ""),
                "juicio_p6": request.POST.get("juicio_p6", ""),
                "trabaja_actualmente": request.POST.get("trabaja_actualmente", ""),
                "memoria_causa_jubilacion": request.POST.get(
                    "memoria_causa_jubilacion", ""
                ),
                "dificultades_trabajo_memoria": request.POST.get(
                    "dificultades_trabajo_memoria", ""
                ),
                "condujo_alguna_vez": request.POST.get("condujo_alguna_vez", ""),
                "conduce_actualmente": request.POST.get("conduce_actualmente", ""),
                "dejo_de_conducir_por_memoria": request.POST.get(
                    "dejo_de_conducir_por_memoria", ""
                ),
                "riesgos_conduccion": request.POST.get("riesgos_conduccion", ""),
                "compras_independientes": request.POST.get(
                    "compras_independientes", ""
                ),
                "actividades_fuera_hogar": request.POST.get(
                    "actividades_fuera_hogar", ""
                ),
                "asiste_funciones_sociales": request.POST.get(
                    "asiste_funciones_sociales", ""
                ),
                "motivo_no_funciones": request.POST.get("motivo_no_funciones", ""),
                "parece_enfermo": request.POST.get("parece_enfermo", ""),
                "participa_hogar_geriatrico": request.POST.get(
                    "participa_hogar_geriatrico", ""
                ),
                "info_suficiente_comunitarias": request.POST.get(
                    "info_suficiente_comunitarias", ""
                ),
                "notas_comunitarias": request.POST.get("notas_comunitarias", ""),
                "cambios_tareas_domesticas": request.POST.get(
                    "cambios_tareas_domesticas", ""
                ),
                "cosas_que_aun_realiza_domesticas": request.POST.get(
                    "cosas_que_aun_realiza_domesticas", ""
                ),
                "cambios_pasatiempos": request.POST.get("cambios_pasatiempos", ""),
                "cosas_que_aun_realiza_pasatiempos": request.POST.get(
                    "cosas_que_aun_realiza_pasatiempos", ""
                ),
                "actividades_no_realiza_en_hogar": request.POST.get(
                    "actividades_no_realiza_en_hogar", ""
                ),
                "habilidad_domestica_dementia_scale": request.POST.get(
                    "habilidad_domestica_dementia_scale"
                )
                or None,
                "descripcion_habilidad_domestica": request.POST.get(
                    "descripcion_habilidad_domestica", ""
                ),
                "nivel_desempeno_domestico": request.POST.get(
                    "nivel_desempeno_domestico", ""
                ),
                "notas_domesticas_pasatiempos": request.POST.get(
                    "notas_domesticas_pasatiempos", ""
                ),
                "cuidado_p1": request.POST.get("cuidado_p1") or None,
                "cuidado_p2": request.POST.get("cuidado_p2") or None,
                "cuidado_p3": request.POST.get("cuidado_p3") or None,
                "cuidado_p4": request.POST.get("cuidado_p4") or None,
            }

            # Guardar o actualizar
            cdrcuidador, created = CDRCuidadorResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=campos
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "✅ Escala CDR (Cuidador) guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar el cuestionario CDR (Cuidador): {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_RedLatSpanish(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de la visita
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Si está pendiente, marcar como en progreso
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Recoger los campos EXACTOS del modelo
            campos = {
                k: request.POST.get(k + "_texto", "")
                for k in [
                    # Autocuidado
                    "comer",
                    "vestirse",
                    "banarse",
                    "bano",
                    "medicamentos",
                    "apariencia",
                    # Cuidado del hogar
                    "cocinar",
                    "poner_mesa",
                    "aseo_hogar",
                    "mantener_casa",
                    "reparar_hogar",
                    "lavado_ropa",
                    # Trabajo y recreación
                    "trabajo",
                    "recreacion",
                    "organizaciones",
                    "desplazamiento",
                    # Compras y dinero
                    "alimentos",
                    "dinero_efectivo",
                    "finanzas",
                    # Viajes
                    "transporte_publico",
                    "manejo_vehiculos",
                    "movilidad_barrio",
                    "viajes_fuera",
                    # Comunicación
                    "telefono",
                    "conversacion",
                    "comprension",
                    "lectura",
                    "escritura",
                    # Tecnología
                    "computador",
                    "telefono_celular",
                    "cajero",
                    "internet",
                    "email",
                    "redes_sociales",
                ]
            }

            # Recoger los puntajes de cada sección
            puntajes = {
                "puntaje_autocuidado": request.POST.get("puntaje_autocuidado"),
                "puntaje_cuidado_hogar": request.POST.get("puntaje_cuidado_hogar"),
                "puntaje_trabajo_recreacion": request.POST.get(
                    "puntaje_trabajo_recreacion"
                ),
                "puntaje_compras_dinero": request.POST.get("puntaje_compras_dinero"),
                "puntaje_viajes": request.POST.get("puntaje_viajes"),
                "puntaje_comunicacion": request.POST.get("puntaje_comunicacion"),
                "puntaje_tecnologia": request.POST.get("puntaje_tecnologia"),
            }

            # Combinar campos de texto y puntajes
            defaults = {**campos, **puntajes}

            # Crear o actualizar
            redlatspanish, created = RedLatSpanishResult.objects.update_or_create(
                visita_examen=visita_examen,  # campo de búsqueda
                defaults=defaults,
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Evaluación RedLat Spanish guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la Evaluación RedLat Spanish: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_BettyFerrel(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            campos = {
                k: request.POST.get(k + "_texto", "")
                for k in [
                    "agotamiento",
                    "cambios_alimenticios",
                    "dolor",
                    "cambios_sueno",
                    "salud_fisica_general",
                    "facilidad_enfrentar",
                    "felicidad",
                    "control_vida",
                    "satisfaccion_vida",
                    "concentracion",
                    "utilidad_personal",
                    "angustia_diagnostico",
                    "ansiedad",
                    "depresion",
                    "miedo_otra_enfermedad",
                    "miedo_retroceso",
                    "miedo_avance",
                    "estado_psicologico",
                    "angustia_familiar",
                    "nivel_ayuda",
                    "relaciones_personales",
                    "vida_sexual",
                    "trabajo",
                    "actividades_hogar",
                    "aislamiento",
                    "carga_economica",
                    "estado_social",
                    "actividades_religiosas",
                    "actividades_espirituales_personales",
                    "incertidumbre_futuro",
                    "cambios_positivos",
                    "proposito_vida",
                    "esperanza",
                    "estado_espiritual",
                ]
            }

            # Obtener puntaje total enviado por JS
            puntaje_total = request.POST.get("puntaje_total", 0)
            try:
                puntaje_total = int(puntaje_total)
            except ValueError:
                puntaje_total = 0

            campos["puntaje_total"] = puntaje_total

            # Guardar o actualizar
            bettyferrel, created = BettyFerrelResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=campos
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Examen Calidad de Vida Betty Ferrel guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar el cuestionario Betty Ferrel: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_evaluacion_clinica_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "cdr_memoria": request.POST.get("cdr_memoria", ""),
                "cdr_orientacion": request.POST.get("cdr_orientacion", ""),
                "cdr_juicio": request.POST.get("cdr_juicio", ""),
                "cdr_comunitarias": request.POST.get("cdr_comunitarias", ""),
                "cdr_pasatiempos": request.POST.get("cdr_pasatiempos", ""),
                "cdr_cuidado": request.POST.get("cdr_cuidado", ""),
                "cdr_global": request.POST.get("cdr_global", ""),
                "cdr_interpretacion": request.POST.get("cdr_interpretacion", ""),
            }

            # Guardar o actualizar
            cdr_result, created = PuntajeCDRResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=campos
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Evaluación clínica CDR guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar la evaluación clínica CDR: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_consentimiento_participante(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "fecha": request.POST.get("fecha"),
                "hora_inicio": request.POST.get("hora_inicio"),
                "investigador": request.POST.get("investigador"),
                "version_consentimiento": request.POST.get("version_consentimiento"),
                "descripcion_proceso": request.POST.get("descripcion_proceso", ""),
                "preguntas": request.POST.get("preguntas", ""),
                "acepta": request.POST.get("acepta"),
                "hora_firma": request.POST.get("hora_firma"),
                "fecha_firma": request.POST.get("fecha_firma"),
                "testigo1": request.POST.get("testigo1", ""),
                "testigo2": request.POST.get("testigo2", ""),
                "copia_entregada": request.POST.get("copia_entregada"),
                "hora_finalizacion": request.POST.get("hora_finalizacion"),
                "firma_participante": request.POST.get("firma_participante", ""),
            }

            # Guardar o actualizar
            consentimientoparticipante, created = (
                ConsentimientoInformadoParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Consentimiento Informado Participante guardado exitosamente.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request,
                f"❌ Error al guardar el Consentimiento Informado Participante: {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_consentimiento_cuidador(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "fecha": request.POST.get("fecha"),
                "hora_inicio": request.POST.get("hora_inicio"),
                "investigador": request.POST.get("investigador"),
                "nombre_acompanante": request.POST.get("nombre_acompanante"),
                "nombre_participante": request.POST.get("nombre_participante"),
                "version_consentimiento": request.POST.get("version_consentimiento"),
                "descripcion_proceso": request.POST.get("descripcion_proceso", ""),
                "preguntas": request.POST.get("preguntas", ""),
                "acepta": request.POST.get("acepta"),
                "hora_firma": request.POST.get("hora_firma"),
                "fecha_firma": request.POST.get("fecha_firma"),
                "testigo1": request.POST.get("testigo1", ""),
                "testigo2": request.POST.get("testigo2", ""),
                "copia_entregada": request.POST.get("copia_entregada"),
                "hora_finalizacion": request.POST.get("hora_finalizacion"),
                "firma_cuidador": request.POST.get("firma_cuidador", ""),
            }

            # Guardar o actualizar
            consentimientocuidador, created = (
                ConsentimientoInformadoCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Consentimiento Informado Cuidador guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request,
                f"❌ Error al guardar el Consentimiento Informado Cuidador: {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_anamnesis_cuidador(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "nombres_apellidos": request.POST.get("nombres_apellidos"),
                "documento": request.POST.get("documento"),
                "lugar_nacimiento": request.POST.get("lugar_nacimiento"),
                "lugar_procedencia": request.POST.get("lugar_procedencia"),
                "edad": request.POST.get("edad"),
                "sexo": request.POST.get("sexo"),
                "estado_civil": request.POST.get("estado_civil"),
                "relacion": request.POST.get("relacion"),
                "tiempo_acompanando": request.POST.get("tiempo_acompanando"),
                "ocupacion": request.POST.get("ocupacion", ""),
                "escolaridad": request.POST.get("escolaridad", ""),
                "ingresos_hogar": request.POST.get("ingresos_hogar"),
                "estrato": request.POST.get("estrato"),
                "religion": request.POST.get("religion", ""),
                "lateralidad": request.POST.get("lateralidad", ""),
                "convivencia": request.POST.get("convivencia", ""),
                "eps": request.POST.get("eps", ""),
            }

            # Guardar o actualizar
            anamnesis_cuidador, created = (
                AnamnesisCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "✅ Anamnesis Cuidador guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(request, f"❌ Error al guardar Anamnesis Cuidador: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_anamnesis_participante(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "nombres_apellidos": request.POST.get("nombres_apellidos"),
                "documento": request.POST.get("documento"),
                "lugar_nacimiento": request.POST.get("lugar_nacimiento"),
                "edad": request.POST.get("edad"),
                "sexo": request.POST.get("sexo"),
                "tiempo_acompanando": request.POST.get("tiempo_acompanando"),
                "ingresos_hogar": request.POST.get("ingresos_hogar"),
                "estrato": request.POST.get("estrato"),
                "religion": request.POST.get("religion", ""),
                "lateralidad": request.POST.get("lateralidad", ""),
                "convivencia": request.POST.get("convivencia", ""),
                "eps": request.POST.get("eps", ""),
            }

            # Guardar o actualizar
            anamnesis_participante, created = (
                AnamnesisParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Anamnesis Participante guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar la Anamnesis Participante: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_Zarit(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener respuestas de las preguntas

            campos = [
                "pide_ayuda",
                "falta_tiempo_propio",
                "agobio",
                "verguenza_conducta",
                "sentir_enfado",
                "afectar_relacion_negativamente",
                "miedo_futuro",
                "dependencia",
                "sentir_tension",
                "deterioro_salud",
                "menos_intimidad",
                "resentir_vida_social",
                "desatender_amistades",
                "unica_dependencia",
                "dinero_insuficiente",
                "incapaz_mas_tiempo",
                "perder_control_vida",
                "cuidado_a_otros",
                "indecision_que_hacer",
                "hacer_mas",
                "cuidar_mejor",
                "grado_carga",
            ]
            # respuestas = {campo+"_value": request.POST.get(campo) for campo in campos}

            respuestas_texto = {
                campo: request.POST.get(campo + "_texto") for campo in campos
            }

            puntaje_total = request.POST.get("puntaje_total")
            interpretacion = request.POST.get("interpretacion")

            zarit, created = ZaritResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # **respuestas,
                    **respuestas_texto,
                    "puntaje_total": puntaje_total,
                    "interpretacion": interpretacion,
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "✅ Escala de Zarit guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si falla
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar la escala de Zarit: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_intervenciones(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            numero_sesion = request.POST.get("num_sesion")
            nombre_sesion = request.POST.get("nombre")
            fecha = request.POST.get("fecha")
            hora_inicio = request.POST.get("hora_inicio")
            hora_fin = request.POST.get("hora_fin")
            asistencia = request.POST.get("asistencia")
            participacion = request.POST.get("participacion")
            estado = request.POST.get("estado")
            tematica = request.POST.get("tematica")
            observaciones = request.POST.get("observaciones")

            # Guardar o actualizar la sesión
            sesion, created = SeguimientoIntervencionesResult.objects.update_or_create(
                visita_examen=visita_examen,
                numero_sesion=numero_sesion,
                defaults={
                    "nombre_sesion": nombre_sesion,
                    "fecha": fecha or None,
                    "hora_inicio": hora_inicio or None,
                    "hora_fin": hora_fin or None,
                    "asistencia": asistencia,
                    "participacion": participacion or None,
                    "estado": estado,
                    "tematica": tematica,
                    "observaciones": observaciones,
                },
            )

            # Verificar cantidad de sesiones
            total_sesiones = SeguimientoIntervencionesResult.objects.filter(
                visita_examen=visita_examen
            ).count()

            if total_sesiones >= 18:
                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
            else:
                visita_examen.estado = "en_progreso"

            visita_examen.save()

            # Mensaje de confirmación
            if created:
                messages.success(
                    request, f"✅ Sesión {numero_sesion} guardada exitosamente."
                )
            else:
                messages.success(
                    request, f"✅ Sesión {numero_sesion} actualizada exitosamente."
                )

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"❌ Error al guardar la sesión: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def obtener_datos_sesion(request, visita_id, examen_id, num_sesion):
    visita_examen = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )
    try:
        sesion = SeguimientoIntervencionesResult.objects.get(
            visita_examen=visita_examen, numero_sesion=num_sesion
        )
        data = {
            "nombre": sesion.nombre_sesion,
            "fecha": sesion.fecha.strftime("%Y-%m-%d") if sesion.fecha else "",
            "hora_inicio": sesion.hora_inicio.strftime("%H:%M")
            if sesion.hora_inicio
            else "",
            "hora_fin": sesion.hora_fin.strftime("%H:%M") if sesion.hora_fin else "",
            "asistencia": sesion.asistencia,
            "participacion": sesion.participacion,
            "estado": sesion.estado,
            "tematica": sesion.tematica,
            "observaciones": sesion.observaciones,
        }
    except SeguimientoIntervencionesResult.DoesNotExist:
        data = {}

    return JsonResponse(data)


@login_required
def resumen_sesiones(request, visita_id, examen_id):
    visita_examen = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )

    sesiones = SeguimientoIntervencionesResult.objects.filter(
        visita_examen=visita_examen
    ).order_by("numero_sesion")

    if sesiones.count() < 18:
        return JsonResponse({"error": "Aún no se han completado las 18 sesiones."})

    total_sesiones = 18
    asistidas = sesiones.filter(asistencia="Sí").count()

    porcentaje_asistencia = round((asistidas / total_sesiones) * 100, 2)
    conteo_asistencia = f"{asistidas}/{total_sesiones}"

    participaciones = [s.participacion for s in sesiones if s.participacion]
    promedio_participacion = (
        round(sum(map(int, participaciones)) / len(participaciones), 2)
        if participaciones
        else 0
    )

    tendencia_participacion = [
        int(s.participacion) if s.participacion else None for s in sesiones
    ]

    alerta = None
    if porcentaje_asistencia < 70:
        alerta = "⚠️ Riesgo de abandono (asistencia < 70%)"

    data = {
        "porcentaje_asistencia": porcentaje_asistencia,
        "conteo_asistencia": conteo_asistencia,
        "promedio_participacion": promedio_participacion,
        "tendencia_participacion": tendencia_participacion,
        "alerta": alerta,
    }

    return JsonResponse(data)


# Estadísticas - RecuérdaMe


