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
def guardar_examen_fisico_sueno(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # CAMBIO: Usar el nuevo método para marcar como iniciado
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Crear o actualizar el resultado del examen físico de sueño
            sueno_fisico, created = SuenoFisicoResult.objects.get_or_create(
                visita_examen=visita_examen,
                defaults={
                    "peso": request.POST.get("peso")
                    or request.POST.get("weight")
                    or None,
                    "talla": request.POST.get("talla")
                    or request.POST.get("height")
                    or None,
                    "imc": request.POST.get("imc") or request.POST.get("bmi") or None,
                    "rango_imc": request.POST.get("rango_imc")
                    or request.POST.get("bmi_range")
                    or "",
                    "circunferencia_cuello": request.POST.get("circunferencia_cuello")
                    or request.POST.get("neck_circumference")
                    or None,
                    "perimetro_abdominal": request.POST.get("perimetro_abdominal")
                    or request.POST.get("abdominal_perimeter")
                    or None,
                    # Examen nasal
                    "simetria_narinas": request.POST.get("simetria_narinas")
                    or request.POST.get("nostril_symmetry")
                    or "",
                    "tipo_narina": request.POST.get("tipo_narina")
                    or request.POST.get("nostril_type")
                    or "",
                    "desviacion_septo": request.POST.get("desviacion_septo")
                    or request.POST.get("septum_deviation")
                    or "",
                    "hipertrofia_cornetes": request.POST.get("hipertrofia_cornetes")
                    or request.POST.get("turbinate_hypertrophy")
                    or "",
                    "grado": request.POST.get("grado")
                    or request.POST.get("grade")
                    or "",
                    # Examen orofaríngeo
                    "hipertrofia_uvula": request.POST.get("hipertrofia_uvula")
                    or request.POST.get("uvula_hypertrophy")
                    or "",
                    "biotipo": request.POST.get("biotipo")
                    or request.POST.get("biotype")
                    or "",
                    "mallampati": request.POST.get("mallampati")
                    or request.POST.get("mallampati_score")
                    or "",
                    "amigdalas": request.POST.get("amigdalas")
                    or request.POST.get("tonsils")
                    or "",
                    "tipo_mordida": request.POST.get("tipo_mordida")
                    or request.POST.get("bite_type")
                    or "",
                    # Otros
                    "alteracion_craneo": request.POST.get("alteracion_craneo")
                    or request.POST.get("cranial_alteration")
                    or "",  # Signos vitales
                    "frecuencia_cardiaca": request.POST.get("frecuencia_cardiaca")
                    or None,
                    "frecuencia_respiratoria": request.POST.get(
                        "frecuencia_respiratoria"
                    )
                    or None,
                    "saturacion_oxigeno": request.POST.get("saturacion_oxigeno")
                    or None,
                    "presion_arterial_sistolica": request.POST.get(
                        "presion_arterial_sistolica"
                    )
                    or None,
                    "presion_arterial_diastolica": request.POST.get(
                        "presion_arterial_diastolica"
                    )
                    or None,
                },
            )

            # Si no es nuevo, actualizar los campos
            if not created:
                sueno_fisico.peso = (
                    request.POST.get("peso") or request.POST.get("weight") or None
                )
                sueno_fisico.talla = (
                    request.POST.get("talla") or request.POST.get("height") or None
                )
                sueno_fisico.imc = (
                    request.POST.get("imc") or request.POST.get("bmi") or None
                )
                sueno_fisico.rango_imc = (
                    request.POST.get("rango_imc") or request.POST.get("bmi_range") or ""
                )
                sueno_fisico.circunferencia_cuello = (
                    request.POST.get("circunferencia_cuello")
                    or request.POST.get("neck_circumference")
                    or None
                )
                sueno_fisico.perimetro_abdominal = (
                    request.POST.get("perimetro_abdominal")
                    or request.POST.get("abdominal_perimeter")
                    or None
                )
                sueno_fisico.simetria_narinas = (
                    request.POST.get("simetria_narinas")
                    or request.POST.get("nostril_symmetry")
                    or ""
                )
                sueno_fisico.tipo_narina = (
                    request.POST.get("tipo_narina")
                    or request.POST.get("nostril_type")
                    or ""
                )
                sueno_fisico.desviacion_septo = (
                    request.POST.get("desviacion_septo")
                    or request.POST.get("septum_deviation")
                    or ""
                )
                sueno_fisico.hipertrofia_cornetes = (
                    request.POST.get("hipertrofia_cornetes")
                    or request.POST.get("turbinate_hypertrophy")
                    or ""
                )
                sueno_fisico.grado = (
                    request.POST.get("grado") or request.POST.get("grade") or ""
                )
                sueno_fisico.hipertrofia_uvula = (
                    request.POST.get("hipertrofia_uvula")
                    or request.POST.get("uvula_hypertrophy")
                    or ""
                )
                sueno_fisico.biotipo = (
                    request.POST.get("biotipo") or request.POST.get("biotype") or ""
                )
                sueno_fisico.mallampati = (
                    request.POST.get("mallampati")
                    or request.POST.get("mallampati_score")
                    or ""
                )
                sueno_fisico.amigdalas = (
                    request.POST.get("amigdalas") or request.POST.get("tonsils") or ""
                )
                sueno_fisico.tipo_mordida = (
                    request.POST.get("tipo_mordida")
                    or request.POST.get("bite_type")
                    or ""
                )
                sueno_fisico.alteracion_craneo = (
                    request.POST.get("alteracion_craneo")
                    or request.POST.get("cranial_alteration")
                    or ""
                )
                # Signos vitales
                sueno_fisico.frecuencia_cardiaca = (
                    request.POST.get("frecuencia_cardiaca") or None
                )
                sueno_fisico.frecuencia_respiratoria = (
                    request.POST.get("frecuencia_respiratoria") or None
                )
                sueno_fisico.saturacion_oxigeno = (
                    request.POST.get("saturacion_oxigeno") or None
                )
                sueno_fisico.presion_arterial_sistolica = (
                    request.POST.get("presion_arterial_sistolica") or None
                )
                sueno_fisico.presion_arterial_diastolica = (
                    request.POST.get("presion_arterial_diastolica") or None
                )

                sueno_fisico.save()

            # CAMBIO: Marcar el examen como completado usando el nuevo método
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "Examen físico de sueño guardado exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"Error al guardar el examen: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "Método no permitido.")
        return redirect("index")


@login_required
def guardar_sueno_anamnesis(request):
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

            # Crear o actualizar el resultado principal
            anamnesis, created = SuenoAnamnesisResult.objects.get_or_create(
                visita_examen=visita_examen
            )

            # ==============================
            # Guardar campos simples
            # ==============================
            campos_simples = [
                "motivo_consulta",
                "enfermedad_actual",
                "presenta_queja",
                "observaciones_queja",
                "causa_conocida",
                "especificacion_causa",
                "rutina_dormir",
                "describa_rutina",
                "jornada_laboral",
                "hora_acostarse_laboral",
                "tiempo_dormirse_laboral",
                "hora_intencion_dormir_laboral",
                "hora_despertar_laboral",
                "tiempo_salir_cama_laboral",
                "sueno_reparador_laboral",
                "companero_cama_laboral",
                "despertador_laboral",
                "jornada_fds",
                "hora_acostarse_fds",
                "tiempo_dormirse_fds",
                "hora_intencion_dormir_fds",
                "hora_despertar_fds",
                "tiempo_salir_cama_fds",
                "sueno_reparador_fds",
                "companero_cama_fds",
                "despertador_fds",
                "hora_acostarse_vacaciones",
                "tiempo_dormirse_vacaciones",
                "hora_intencion_dormir_vacaciones",
                "hora_despertar_vacaciones",
                "tiempo_salir_cama_vacaciones",
                "sueno_reparador_vacaciones",
                "companero_cama_vacaciones",
                "despertador_vacaciones",
                "realiza_siestas",
                "numero_siestas",
                "duracion_siestas",
                "siesta_frecuencia",
                "siesta_reparadora",
                "momento_dia_siesta",
                "periodo_siestas",
                "iluminacion",
                "comodidad",
                "ruido",
                "posicion_dormir",
                "posicion_dormir_otra",
                "consume",
                "consume_medicamento",
                "usa_pantallas",
                "cama_actividades",
                "actividad_fisica",
                "sintomas_sueno",
                "sintomas_diurnos",
                "observaciones",
            ]

            for campo in campos_simples:
                if campo == "periodo_siestas":
                    valores = request.POST.getlist("periodo_siestas")
                    # unir las selecciones en una sola cadena separada por punto y coma
                    valor = "; ".join([v for v in valores if v]) if valores else ""
                else:
                    valor = request.POST.get(campo, "")
                setattr(anamnesis, campo, valor)

            anamnesis.save()

            # ==============================
            # Guardar relaciones hijas
            # ==============================

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

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener respuestas de las preguntas (1-8)
            pregunta_1 = request.POST.get("induccion_dormir", "0")
            pregunta_2 = request.POST.get("despertares_noche", "0")
            pregunta_3 = request.POST.get("despertar_temprano", "0")
            pregunta_4 = request.POST.get("duracion_dormir", "0")
            pregunta_5 = request.POST.get("calidad_dormir", "0")
            pregunta_6 = request.POST.get("bienestar_dia", "0")
            pregunta_7 = request.POST.get("funcionamiento_dia", "0")
            pregunta_8 = request.POST.get("somnolencia_dia", "0")

            # Calcular puntuación total
            puntuacion_total = request.POST.get("puntuacion_total", "0")

            # Crear o actualizar el resultado de Atenas
            atenas, created = AtenasResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Preguntas individuales
                    "induccion_dormir": pregunta_1,
                    "despertares_noche": pregunta_2,
                    "despertar_temprano": pregunta_3,
                    "duracion_dormir": pregunta_4,
                    "calidad_dormir": pregunta_5,
                    "bienestar_dia": pregunta_6,
                    "funcionamiento_dia": pregunta_7,
                    "somnolencia_dia": pregunta_8,
                    # Puntuación y interpretación
                    "puntuacion_total": puntuacion_total,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala de Atenas guardada exitosamente. Puntuación: {puntuacion_total}",
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
                request, f"❌ Error al guardar la escala de Atenas: {str(e)}"
            )
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

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener los campos según tu modelo BerlinResult
            peso_cambio = request.POST.get("peso_cambio", "")
            ronca = request.POST.get("ronca", "")
            tipo_ronquido = request.POST.get("tipo_ronquido", "")
            frecuencia_ronquidos = request.POST.get("frecuencia_ronquidos", "")
            ronquido_molesto = request.POST.get("ronquido_molesto", "")
            apnea_observada = request.POST.get("apnea_observada", "")
            fatiga_matutina = request.POST.get("fatiga_matutina", "")
            fatiga_dia = request.POST.get("fatiga_dia", "")
            somnolencia_conducir = request.POST.get("somnolencia_conducir", "")
            presion_alta = request.POST.get("presion_alta", "")

            # Crear o actualizar el resultado de Berlín usando los campos exactos del modelo
            berlin, created = BerlinResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos exactos según tu modelo BerlinResult
                    "peso_cambio": peso_cambio,
                    "ronca": ronca,
                    "tipo_ronquido": tipo_ronquido,
                    "frecuencia_ronquidos": frecuencia_ronquidos,
                    "ronquido_molesto": ronquido_molesto,
                    "apnea_observada": apnea_observada,
                    "fatiga_matutina": fatiga_matutina,
                    "fatiga_dia": fatiga_dia,
                    "somnolencia_conducir": somnolencia_conducir,
                    "presion_alta": presion_alta,
                },
            )
            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Cuestionario de Berlín guardado exitosamente."
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
                request, f"❌ Error al guardar el cuestionario de Berlín: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Epworth(request):
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

            # Obtener las respuestas según los nombres en tu HTML
            sentado_leyendo = request.POST.get("epworth_leyendo", "0")
            viendo_tv = request.POST.get("epworth_tv", "0")
            sentado_teatro = request.POST.get("epworth_teatro", "0")
            pasajero_coche = request.POST.get("epworth_pasajero", "0")
            tumbado_tarde = request.POST.get("epworth_tumbado", "0")
            charlando = request.POST.get("epworth_charlando", "0")
            despues_comer = request.POST.get("epworth_comida", "0")
            trafico = request.POST.get("epworth_trafico", "0")

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

            # Crear o actualizar el resultado de Epworth usando los campos exactos del modelo
            epworth, created = EpworthResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos exactos según tu modelo EpworthResult
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

            messages.success(request, f"✅ Escala de Epworth guardada exitosamente.\n")
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
            dificultad_dormir = request.POST.get("dificultad_dormir", "")
            dificultad_mantener_sueno = request.POST.get(
                "dificultad_mantener_sueno", ""
            )
            despertar_temprano = request.POST.get("despertar_temprano", "")
            satisfaccion_sueno = request.POST.get("satisfaccion_sueno", "")
            notabilidad_problema = request.POST.get("notabilidad_problema", "")
            preocupacion_sueno = request.POST.get("preocupacion_sueno", "")
            interferencia_sueno = request.POST.get("interferencia_sueno", "")

            puntuacion = request.POST.get("puntuacion_total", "0")

            # Crear o actualizar el resultado ISI
            isi_result, created = ISIResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "dificultad_dormir": dificultad_dormir,
                    "dificultad_mantener_sueno": dificultad_mantener_sueno,
                    "despertar_temprano": despertar_temprano,
                    "satisfaccion_sueno": satisfaccion_sueno,
                    "notabilidad_problema": notabilidad_problema,
                    "preocupacion_sueno": preocupacion_sueno,
                    "interferencia_sueno": interferencia_sueno,
                    "puntuacion_total": puntuacion,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Índice de Severidad del Insomnio (ISI) guardado exitosamente.\n",
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

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener los campos del formulario
            hora_levantarse = request.POST.get("hora_levantarse_meq", "")
            hora_acostarse = request.POST.get("hora_acostarse_meq", "")
            uso_despertador = request.POST.get("uso_despertador_meq", "")
            facilidad_levantarse = request.POST.get("facilidad_levantarse_meq", "")
            alerta_manana = request.POST.get("alerta_manana_meq", "")
            apetito_manana = request.POST.get("apetito_manana_meq", "")
            descanso_manana = request.POST.get("descanso_manana_meq", "")
            hora_acostarse_libre = request.POST.get("hora_acostarse_libre_meq", "")

            # Nuevos campos agregados
            ejercicio_manana = request.POST.get("ejercicio_manana_meq", "")
            ejercicio_fisico = request.POST.get("ejercicio_fisico_meq", "")
            hora_cansancio_noche = request.POST.get("hora_cansancio_noche_meq", "")
            prueba_mental = request.POST.get("prueba_mental_meq", "")
            cansancio_11pm = request.POST.get("cansancio_11pm_meq", "")
            despertar_tarde = request.POST.get("despertar_tarde_meq", "")

            # Campos existentes
            nivel_cansancia_11 = request.POST.get("nivel_cansancia_11", "")
            hora_despertarse_si_tarde = request.POST.get(
                "hora_despertarse_si_tarde", ""
            )
            guardia_nocturna = request.POST.get("guardia_nocturna_meq", "")
            trabajo_fisico = request.POST.get("trabajo_fisico_meq", "")
            horario_trabajo_fisico = request.POST.get("horario_trabajo_fisico", "")
            ejercicio_nocturno = request.POST.get("ejercicio_nocturno_meq", "")
            horario_trabajo = request.POST.get("horario_trabajo_meq", "")
            maximo_bienestar = request.POST.get("maximo_bienestar_meq", "")
            tipo_persona = request.POST.get("tipo_persona_meq", "")

            # OBTENER LA PUNTUACIÓN CALCULADA EN EL FRONTEND
            puntuacion_calculada = request.POST.get("puntuacion", "0")

            try:
                puntuacion_final = (
                    int(puntuacion_calculada) if puntuacion_calculada.isdigit() else 0
                )
            except (ValueError, TypeError):
                puntuacion_final = 0

            # Determinar cronotipo según puntuación MEW
            if puntuacion_final >= 70:
                tipo_persona_calculado = "Definitivamente matutino"
            elif puntuacion_final >= 59:
                tipo_persona_calculado = "Moderadamente matutino"
            elif puntuacion_final >= 42:
                tipo_persona_calculado = "Ni matutino ni vespertino"
            elif puntuacion_final >= 31:
                tipo_persona_calculado = "Moderadamente vespertino"
            else:
                tipo_persona_calculado = "Definitivamente vespertino"

            # Crear o actualizar el resultado MEW
            mew_result, created = MEWResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos del modelo MEWResult
                    "hora_levantarse": hora_levantarse,
                    "hora_acostarse": hora_acostarse,
                    "uso_despertador": uso_despertador,
                    "facilidad_levantarse": facilidad_levantarse,
                    "alerta_manana": alerta_manana,
                    "apetito_manana": apetito_manana,
                    "descanso_manana": descanso_manana,
                    "hora_acostarse_libre": hora_acostarse_libre,
                    # Nuevos campos agregados al modelo
                    "ejercicio_manana": ejercicio_manana,
                    "prueba_mental": prueba_mental,
                    "cansancio_11pm": cansancio_11pm,
                    "despertar_tarde": despertar_tarde,
                    "trabajo_fisico": trabajo_fisico,
                    # Campos existentes en el modelo
                    "ejercicio_fisico": ejercicio_fisico,
                    "hora_cansancio_noche": hora_cansancio_noche,
                    "nivel_cansancia_11": nivel_cansancia_11,
                    "hora_despertarse_si_tarde": hora_despertarse_si_tarde,
                    "guardia_nocturna": guardia_nocturna,
                    "horario_trabajo_fisico": horario_trabajo_fisico,
                    "ejercicio_nocturno": ejercicio_nocturno,
                    "horario_trabajo": horario_trabajo,
                    "maximo_bienestar": maximo_bienestar,
                    "tipo_persona": tipo_persona or tipo_persona_calculado,
                    "puntuacion": puntuacion_final,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Cuestionario MEW guardado exitosamente.\n"
                f"📊 Puntuación: {puntuacion_final}/86 - {tipo_persona_calculado}",
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
                request, f"❌ Error al guardar el cuestionario MEW: {str(e)}"
            )
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

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener los campos según los NOMBRES EXACTOS del modelo PittsburghResult
            hora_acostarse = request.POST.get("hora_acostarse", "")
            hora_levantarse = request.POST.get("hora_levantarse", "")
            latencia_sueno = request.POST.get("latencia_sueno", "")
            horas_dormidas = request.POST.get(
                "horas_sueno_real", "0"
            )  # ✅ CAMPO CORRECTO DEL MODELO

            # Problemas durante el sueño - NOMBRES EXACTOS DEL MODELO
            conciliar_sueno = request.POST.get("conciliar_sueno", "")
            despertarse_sueno = request.POST.get("despertarse_sueno", "")
            levantarse_servicio_sueno = request.POST.get(
                "levantarse_servicio_sueno", ""
            )
            respirar = request.POST.get("respirar", "")
            toser_roncar_sueno = request.POST.get("toser_roncar_sueno", "")
            sentir_frio_sueno = request.POST.get(
                "sentir_frio_sueno", ""
            )  # ✅ Sin mayúscula
            calor_sueno = request.POST.get("calor_sueno", "")
            pesadillas_sueno = request.POST.get("pesadillas_sueno", "")
            dolores_sueno = request.POST.get("dolores_sueno", "")
            otras_razones = request.POST.get(
                "otras_razones", ""
            )  # ✅ NOMBRE CORRECTO DEL MODELO
            otras_sueno = request.POST.get("otras_sueno", "")

            # Evaluación general - NOMBRES EXACTOS DEL MODELO
            calidad_sueno = request.POST.get("calidad_sueno", "")
            medicinas_sueno = request.POST.get("medicinas_sueno", "")
            somnolencia_sueno = request.POST.get("somnolencia_sueno", "")
            problemas_animos_sueno = request.POST.get("problemas_animos_sueno", "")

            # Información de compañía - NOMBRES EXACTOS DEL MODELO
            duerme_acompanado = request.POST.get("duerme_acompanado", "")
            ronquidos_ruidosos = request.POST.get("ronquidos_ruidosos", "")
            pausas_respiracion = request.POST.get("pausas_respiracion", "")
            sacudidas_piernas = request.POST.get("sacudidas_piernas", "")
            desorientacion_confusion = request.POST.get("desorientacion_confusion", "")
            descripcion_inconvenientes = request.POST.get(
                "descripcion_inconvenientes", ""
            )
            otros_inconvenientes = request.POST.get("otros_inconvenientes", "")
            puntuacion_total = request.POST.get("puntuacion_total", 0)

            # Crear o actualizar el resultado Pittsburgh usando los CAMPOS EXACTOS del modelo
            pitsburg_result, created = PittsburghResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos de tiempo - NOMBRES EXACTOS DEL MODELO
                    "hora_acostarse": hora_acostarse,
                    "hora_levantarse": hora_levantarse,
                    "latencia_sueno": latencia_sueno,
                    "horas_dormidas": horas_dormidas,
                    "conciliar_sueno": conciliar_sueno,
                    "despertarse_sueno": despertarse_sueno,
                    "levantarse_servicio_sueno": levantarse_servicio_sueno,
                    "respirar": respirar,
                    "toser_roncar_sueno": toser_roncar_sueno,
                    "sentir_frio_sueno": sentir_frio_sueno,
                    "calor_sueno": calor_sueno,
                    "pesadillas_sueno": pesadillas_sueno,
                    "dolores_sueno": dolores_sueno,
                    "otras_razones": otras_razones,  # ✅ CAMPO CORRECTO DEL MODELO
                    "otras_sueno": otras_sueno,
                    # Evaluación general - NOMBRES EXACTOS DEL MODELO
                    "calidad_sueno": calidad_sueno,
                    "medicinas_sueno": medicinas_sueno,
                    "somnolencia_sueno": somnolencia_sueno,
                    "problemas_animos_sueno": problemas_animos_sueno,
                    # Información de compañía - NOMBRES EXACTOS DEL MODELO
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

            messages.success(
                request,
                f"✅ Cuestionario de Pittsburgh guardado exitosamente.\n"
                f"📊 Hora acostarse: {hora_acostarse} | Hora levantarse: {hora_levantarse}\n"
                f"🛏️ Calidad de sueño: {calidad_sueno}\n",
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
                request, f"❌ Error al guardar el cuestionario de Pittsburgh: {str(e)}"
            )
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

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # CAMBIO: Convertir valores correctamente (ahora recibimos "0" y "1")
            def convert_to_bool(value):
                """Convierte valor del formulario a booleano"""
                if value is None:
                    return False
                # Si viene como string "1" o "0"
                if isinstance(value, str):
                    return value == "1" or value.lower() == "true"
                # Si viene como entero
                return bool(int(value)) if str(value).isdigit() else False

            # Aplicar conversión a todos los campos
            ronca_fuerte = convert_to_bool(request.POST.get("ronca_fuerte"))
            cansado_frecuencia = convert_to_bool(request.POST.get("cansado_frecuencia"))
            deja_respirar = convert_to_bool(request.POST.get("deja_respirar"))
            presion_arterial = convert_to_bool(request.POST.get("presion_arterial"))
            imc_alto = convert_to_bool(request.POST.get("imc_alto"))
            mayor_50 = convert_to_bool(request.POST.get("mayor_50"))
            cuello_grande = convert_to_bool(request.POST.get("cuello_grande"))
            masculino = convert_to_bool(request.POST.get("masculino"))

            # Calcular puntuación
            campos = [
                ronca_fuerte,
                cansado_frecuencia,
                deja_respirar,
                presion_arterial,
                imc_alto,
                mayor_50,
                cuello_grande,
                masculino,
            ]
            puntaje_total = sum(campos)

            # STOP (primeros 4) y BANG (últimos 4)
            stop_positivos = sum(campos[:4])
            bang_positivos = sum(campos[4:])

            # Determinar riesgo
            if puntaje_total <= 2:
                riesgo = "Bajo"
            elif puntaje_total <= 4:
                riesgo = "Intermedio"
            else:
                riesgo = "Alto"

            # Alternativa: alto riesgo si STOP≥2 y BANG≥2
            alto_riesgo_alternativo = stop_positivos >= 2 and bang_positivos >= 2

            # Guardar resultado en la BD
            stopbang_result, created = StopBangResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "ronca_fuerte": ronca_fuerte,
                    "cansado_frecuencia": cansado_frecuencia,
                    "deja_respirar": deja_respirar,
                    "presion_arterial": presion_arterial,
                    "imc_alto": imc_alto,
                    "mayor_50": mayor_50,
                    "cuello_grande": cuello_grande,
                    "masculino": masculino,
                    "puntaje_total": puntaje_total,
                    "riesgo": riesgo,
                    "stop_positivos": stop_positivos,
                    "bang_positivos": bang_positivos,
                    "alto_riesgo_alternativo": alto_riesgo_alternativo,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Cuestionario STOP-BANG guardado exitosamente.\n"
                f"📊 Puntuación: {puntaje_total}/8 - {riesgo} riesgo\n"
                f"🔍 STOP: {stop_positivos} | BANG: {bang_positivos}",
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
                request, f"❌ Error al guardar el cuestionario STOP-BANG: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


### Anosognosia


