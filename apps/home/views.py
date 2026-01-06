# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings  # Integración RecuérdaMe
from django.http import JsonResponse, HttpResponseServerError  # Integración RecuérdaMe
from datetime import datetime, timedelta
from .models import *
from .forms import ProyectoForm, RegistroDemograficoForm
import json
from django.forms.models import model_to_dict
import requests  # Integración RecuérdaMe
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
import logging
import os
from django.core.mail import EmailMessage
# AGENDAMIENTO PUBLICO


class AgendarCitaPublicaView(TemplateView):
    """
    Vista pública para que los pacientes vean disponibilidad y agenden citas
    """

    template_name = "scheduling/agendar_cita.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener profesionales que tienen disponibilidades activas
        profesionales_con_disponibilidad = User.objects.filter(
            disponibilidades__activa=True, is_active=True
        ).distinct()

        context.update(
            {
                "profesionales": profesionales_con_disponibilidad,
                "titulo": "Reservar Cita Médica",
            }
        )

        return context


def api_eventos_disponibilidad_publica(request):
    """
    API endpoint para obtener disponibilidades públicas (solo para agendar citas)
    """
    try:
        # Obtener parámetros de filtro
        publico = request.GET.get("publico", False)
        profesional_filtro = request.GET.get("profesional", "")

        if not publico:
            return JsonResponse({"error": "Acceso no autorizado"}, status=403)

        # Filtrar solo disponibilidades futuras y activas
        disponibilidades = DisponibilidadUsuario.objects.filter(
            activa=True,
            usuario__is_active=True,
        ).select_related("usuario", "sala")

        # Filtrar por fecha_fin si existe, o permitir indefinidas
        fecha_actual = datetime.now().date()
        disponibilidades = disponibilidades.filter(
            models.Q(fecha_fin__isnull=True) | models.Q(fecha_fin__gte=fecha_actual),
            fecha_inicio__lte=fecha_actual + timedelta(weeks=8),  # Máximo 8 semanas
        )

        # Aplicar filtro de profesional si se proporciona
        if profesional_filtro:
            disponibilidades = disponibilidades.filter(usuario_id=profesional_filtro)

        eventos = []

        for disponibilidad in disponibilidades:
            # Generar eventos para las próximas 8 semanas
            fecha_limite = disponibilidad.fecha_fin or (
                fecha_actual + timedelta(weeks=8)
            )
            fecha_limite = min(fecha_limite, fecha_actual + timedelta(weeks=8))

            # Generar fechas que coinciden con el día de la semana
            fechas_a_revisar = []
            current_date = max(fecha_actual, disponibilidad.fecha_inicio)

            while current_date <= fecha_limite:
                if current_date.weekday() == disponibilidad.dia_semana:
                    fechas_a_revisar.append(current_date)
                current_date += timedelta(days=1)

            # Para cada fecha válida, generar slots de tiempo
            for fecha in fechas_a_revisar:
                # Generar slots de 1 hora dentro del horario disponible
                hora_actual = disponibilidad.hora_inicio

                while hora_actual < disponibilidad.hora_fin:
                    # Calcular hora de fin del slot (1 hora)
                    datetime_actual = datetime.combine(fecha, hora_actual)
                    datetime_fin_slot = datetime_actual + timedelta(hours=1)
                    hora_fin_slot = datetime_fin_slot.time()

                    if hora_fin_slot <= disponibilidad.hora_fin:
                        # 🔧 VERIFICAR SI YA HAY UNA CITA AGENDADA
                        cita_existente = CitaMedica.objects.filter(
                            disponibilidad=disponibilidad,
                            fecha_cita=fecha,
                            estado__in=["agendada", "confirmada"],
                        ).first()

                        # Solo mostrar como disponible si no hay cita agendada
                        if not cita_existente:
                            evento = {
                                "id": f"{disponibilidad.id}_{fecha}_{hora_actual}",
                                "title": f"Dr(a). {disponibilidad.usuario.get_full_name() or disponibilidad.usuario.username}",
                                "start": f"{fecha}T{hora_actual}",
                                "end": f"{fecha}T{hora_fin_slot}",
                                "backgroundColor": "#28a745",
                                "borderColor": "#28a745",
                                "textColor": "#ffffff",
                                "extendedProps": {
                                    "disponibilidad_id": disponibilidad.id,
                                    "profesional_id": disponibilidad.usuario.id,
                                    "sala": disponibilidad.sala.nombre,
                                    "especialidad": "Medicina General",
                                    "disponible": True,
                                    "es_mio": False,
                                    "tipo": "cita_disponible",
                                    "fecha_cita": fecha.strftime("%Y-%m-%d"),
                                    "hora_inicio": hora_actual.strftime("%H:%M"),
                                    "hora_fin": hora_fin_slot.strftime("%H:%M"),
                                },
                            }
                            eventos.append(evento)
                        else:
                            # 📅 OPCIONAL: Mostrar citas ocupadas (solo para información)
                            evento_ocupado = {
                                "id": f"ocupado_{disponibilidad.id}_{fecha}_{hora_actual}",
                                "title": f"🔒 Ocupado - Dr(a). {disponibilidad.usuario.get_full_name()}",
                                "start": f"{fecha}T{hora_actual}",
                                "end": f"{fecha}T{hora_fin_slot}",
                                "backgroundColor": "#dc3545",
                                "borderColor": "#dc3545",
                                "textColor": "#ffffff",
                                "extendedProps": {
                                    "disponible": False,
                                    "ocupado": True,
                                    "tipo": "cita_ocupada",
                                    "paciente": cita_existente.nombre_paciente,
                                },
                                "display": "background",  # Mostrar como fondo
                            }
                            # eventos.append(evento_ocupado)  # Descomenta si quieres mostrar ocupados

                    # Avanzar al siguiente slot (1 hora)
                    hora_actual = hora_fin_slot

        return JsonResponse(eventos, safe=False)

    except Exception as e:
        import traceback

        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def agendar_cita_ajax(request):
    """
    Vista para agendar una cita médica desde la agenda pública
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            # Obtener datos del formulario
            disponibilidad_id = data.get("disponibilidad_id")
            fecha_cita_str = data.get("fecha_cita")
            email_paciente = data.get("email_paciente")
            nombre_paciente = data.get("nombre_paciente")
            telefono_paciente = data.get("telefono_paciente", "")
            motivo_consulta = data.get("motivo_consulta", "")

            # Validaciones básicas
            if not all(
                [disponibilidad_id, fecha_cita_str, email_paciente, nombre_paciente]
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Faltan datos obligatorios: disponibilidad, fecha, email y nombre son requeridos.",
                    }
                )

            # Obtener la disponibilidad
            try:
                disponibilidad = DisponibilidadUsuario.objects.get(
                    id=disponibilidad_id, activa=True
                )
            except DisponibilidadUsuario.DoesNotExist:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "La disponibilidad seleccionada no existe o no está activa.",
                    }
                )

            # Convertir fecha
            try:
                fecha_cita = datetime.strptime(fecha_cita_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Formato de fecha inválido. Use YYYY-MM-DD.",
                    }
                )

            # Validar que la fecha sea futura
            if fecha_cita < datetime.now().date():
                return JsonResponse(
                    {
                        "success": False,
                        "message": "No se pueden agendar citas en fechas pasadas.",
                    }
                )

            # Validar que la fecha coincida con el día de semana de la disponibilidad
            if fecha_cita.weekday() != disponibilidad.dia_semana:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "La fecha seleccionada no coincide con el día de disponibilidad del profesional.",
                    }
                )

            # Verificar si ya existe una cita para esa fecha y disponibilidad
            cita_existente = CitaMedica.objects.filter(
                disponibilidad=disponibilidad,
                fecha_cita=fecha_cita,
                estado__in=["agendada", "confirmada"],
            ).first()

            if cita_existente:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Este horario ya está ocupado para la fecha seleccionada.",
                    }
                )

            # Crear la nueva cita
            nueva_cita = CitaMedica.objects.create(
                disponibilidad=disponibilidad,
                fecha_cita=fecha_cita,
                email_paciente=email_paciente.lower().strip(),
                nombre_paciente=nombre_paciente.strip(),
                telefono_paciente=telefono_paciente.strip(),
                motivo_consulta=motivo_consulta.strip(),
                estado="agendada",
            )

            # Formatear información para la respuesta
            hora_inicio = disponibilidad.hora_inicio.strftime("%H:%M")
            hora_fin = disponibilidad.hora_fin.strftime("%H:%M")
            fecha_formateada = fecha_cita.strftime("%d/%m/%Y")

            # Preparar datos para envío de correo
            cita_data = {
                "email_paciente": email_paciente.lower().strip(),
                "nombre_paciente": nombre_paciente.strip(),
                "fecha_cita": fecha_formateada,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "profesional": disponibilidad.usuario.get_full_name()
                or disponibilidad.usuario.username,
                "sala": disponibilidad.sala.nombre,
                "cita_id": nueva_cita.id,
                "telefono_paciente": telefono_paciente.strip(),
                "motivo_consulta": motivo_consulta.strip(),
                "profesional_email": getattr(disponibilidad.usuario, "email", None),
            }

            # Enviar correo de confirmación al paciente
            correo_enviado = False
            try:
                correo_enviado = enviar_correo_confirmacion_cita(cita_data)

            except Exception as e:
                correo_enviado = False

            # Enviar notificación al profesional (opcional)
            try:
                if cita_data.get("profesional_email"):
                    enviar_notificacion_profesional(cita_data)
            except Exception as e:
                logger.error(f"❌ Error al notificar al profesional: {str(e)}")

            # Mensaje de respuesta
            mensaje_base = (
                f"¡Cita agendada exitosamente!\n"
                f"📅 Fecha: {fecha_formateada}\n"
                f"🕒 Horario: {hora_inicio} - {hora_fin}\n"
                f"👨‍⚕️ Profesional: Dr(a). {disponibilidad.usuario.get_full_name()}\n"
                f"🏥 Sala: {disponibilidad.sala.nombre}\n"
            )

            if correo_enviado:
                mensaje_final = (
                    mensaje_base + f"📧 Confirmación enviada a: {email_paciente}"
                )
            else:
                mensaje_final = mensaje_base + f"⚠️ Cita agendada correctamente"

            return JsonResponse(
                {
                    "success": True,
                    "message": f"¡Cita agendada exitosamente!\n"
                    f"📅 Fecha: {fecha_formateada}\n"
                    f"🕒 Horario: {hora_inicio} - {hora_fin}\n"
                    f"👨‍⚕️ Profesional: Dr(a). {disponibilidad.usuario.get_full_name()}\n"
                    f"🏥 Sala: {disponibilidad.sala.nombre}\n"
                    f"📧 Se enviará confirmación a: {email_paciente}",
                    "cita_id": nueva_cita.id,
                    "fecha_cita": fecha_cita.strftime("%Y-%m-%d"),
                    "hora_inicio": hora_inicio,
                    "hora_fin": hora_fin,
                    "profesional": disponibilidad.usuario.get_full_name()
                    or disponibilidad.usuario.username,
                    "sala": disponibilidad.sala.nombre,
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Error en el formato de los datos enviados.",
                }
            )
        except Exception as e:
            import traceback

            return JsonResponse(
                {
                    "success": False,
                    "message": "Error interno del servidor. Inténtelo nuevamente.",
                }
            )

    return JsonResponse({"success": False, "message": "Método no permitido. Use POST."})


logger = logging.getLogger(__name__)


def enviar_correo_confirmacion_cita(cita_data):
    try:
        mensaje = f"""
        <p>Estimado/a {cita_data["nombre_paciente"]},</p>

        <p>Su cita médica ha sido agendada exitosamente.</p>

        <h3>🔹 DETALLES DE LA CITA</h3>
        <ul>
            <li><strong>Fecha:</strong> {cita_data["fecha_cita"]}</li>
            <li><strong>Hora:</strong> {cita_data["hora_inicio"]} - {cita_data["hora_fin"]}</li>
            <li><strong>Profesional:</strong> {cita_data["profesional"]}</li>
            <li><strong>Consultorio:</strong> {cita_data["sala"]} — Laboratorio de Neuropsicología y Conducta – GRUNECO</li>
            <li><strong>Código de cita:</strong> #{cita_data["cita_id"]}</li>
        </ul>

        <h3>📝 ACCIÓN IMPORTANTE ANTES DE SU CITA</h3>

        <p><strong>Por favor registre sus datos demográficos en el siguiente enlace:</strong></p>

        <p style="font-size: 18px;">
            <a href="https://www.gruneco.com.co/registro-demografico/" 
            style="font-weight: bold; color: #004aad;">
            https://www.gruneco.com.co/registro-demografico/
            </a>
        </p>

        <p>➡ <strong>Después de registrar sus datos demográficos, aparecerá un botón para completar sus exámenes pendientes.</strong></p>

        <h3>📄 CONSENTIMIENTO INFORMADO</h3>
        <p>Adjunto encontrará el consentimiento informado del Proyecto Sueño. Por favor léalo antes de asistir a su cita.</p>

        <h3>📌 RECORDATORIO</h3>
        <p>Duerma de manera habitual la noche anterior y llegue 10 minutos antes de su hora programada.</p>
        <p>Esta cita no requiere dormir durante la sesión.</p>

        <p>Se generará una constancia de asistencia al finalizar la evaluación.
        La constancia no constituye excusa válida para ausencias académicas.</p>

        <p>Para cancelar o reprogramar, comuníquese con anticipación a 
        <strong>gruponeuropsicologia@udea.edu.co</strong></p>

        <p>Gracias por confiar en nosotros.</p>

        <p>Saludos cordiales,<br><strong>GRUNECO</strong></p>
        """

        # Construir el correo con adjunto
        correo = EmailMessage(
            subject=f"Confirmación de Cita Médica - {cita_data['fecha_cita']}",
            body=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[cita_data["email_paciente"]],
        )

        correo.content_subtype = "html"

        # -------------------------------
        # 📎 ADJUNTAR EL PDF DEL CONSENTIMIENTO
        # -------------------------------
        static_root_path = settings.STATICFILES_DIRS[0]  # apps/static
        pdf_path = os.path.join(
            static_root_path,
            "assets",
            "pdfs",
            "CI_ProyectoSueno.pdf",
        )

        if os.path.exists(pdf_path):
            correo.attach_file(pdf_path)
            logger.info(f"📎 PDF adjuntado: {pdf_path}")
        else:
            logger.warning(f"⚠️ No se encontró el PDF: {pdf_path}")

        correo.send(fail_silently=False)

        logger.info(f"✅ Correo enviado exitosamente a {cita_data['email_paciente']}")
        return True

    except Exception as e:
        logger.error(
            f"❌ Error al enviar correo a {cita_data.get('email_paciente', 'unknown')}: {str(e)}"
        )
        return False


def enviar_notificacion_profesional(cita_data):
    try:
        mensaje = f"""
        <p><strong>Se ha agendado una nueva cita.</strong></p>

        <h4>DETALLES DE LA CITA:</h4>
        <ul>
            <li><strong>Paciente:</strong> {cita_data["nombre_paciente"]}</li>
            <li><strong>Email del paciente:</strong> {cita_data["email_paciente"]}</li>
            <li><strong>Teléfono:</strong> {cita_data["telefono_paciente"] or "No registrado"}</li>
            <li><strong>Motivo de consulta:</strong> {cita_data["motivo_consulta"] or "No especificado"}</li>
            <li><strong>Fecha:</strong> {cita_data["fecha_cita"]}</li>
            <li><strong>Hora:</strong> {cita_data["hora_inicio"]} - {cita_data["hora_fin"]}</li>
            <li><strong>Sala:</strong> {cita_data["sala"]}</li>
            <li><strong>Código de cita:</strong> #{cita_data["cita_id"]}</li>
        </ul>

        <p>Por favor revise su agenda en la plataforma.</p>

        <p>Saludos,<br>Sistema de Gestión de Citas GRUNECO</p>
        """

        send_mail(
            subject=f"📢 Nueva cita agendada - {cita_data['fecha_cita']}",
            message="",  # solo HTML
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[cita_data["profesional_email"]],
            html_message=mensaje,
            fail_silently=False,
        )

        logger.info(
            f"📨 Notificación enviada al profesional {cita_data['profesional_email']}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Error al notificar al profesional: {str(e)}")
        return False


# DISPONIBILIDAD USUARIO


@login_required
def gestionar_disponibilidad(request):
    """Vista principal del calendario de disponibilidad"""
    # Procesar formularios si es POST
    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "agregar_disponibilidad":
            return agregar_disponibilidad(request)
        elif accion == "eliminar_disponibilidad":
            return eliminar_disponibilidad(request)

    # Datos para el contexto
    salas = Sala.objects.filter(activa=True)
    disponibilidades_usuario = DisponibilidadUsuario.objects.filter(
        usuario=request.user, activa=True
    ).select_related("sala")

    citas_usuario = CitaMedica.objects.filter(disponibilidad__usuario=request.user)

    context = {
        "salas": salas,
        "disponibilidades_usuario": disponibilidades_usuario,
        "citas_usuario": citas_usuario,
        "dias_semana": DisponibilidadUsuario.DIAS_SEMANA,
        "segment": "calendario_disponibilidad",
    }

    return render(request, "scheduling/calendario_disponibilidad.html", context)


@login_required
def api_eventos_disponibilidad(request):
    try:
        disponibilidades = DisponibilidadUsuario.objects.filter(
            activa=True
        ).select_related("usuario", "sala")

        eventos = []
        fecha_inicio = timezone.now().date()

        # ================================
        # 1️⃣ EVENTOS DE DISPONIBILIDAD
        # ================================
        for disp in disponibilidades:
            for semana in range(12):
                fecha_base = fecha_inicio + timedelta(weeks=semana)
                dias_diferencia = (disp.dia_semana - fecha_base.weekday()) % 7
                fecha_evento = fecha_base + timedelta(days=dias_diferencia)

                if fecha_evento >= disp.fecha_inicio:
                    if not disp.fecha_fin or fecha_evento <= disp.fecha_fin:
                        eventos.append(
                            {
                                "id": f"disp_{disp.id}_{fecha_evento.strftime('%Y%m%d')}",
                                "title": f"Disponible - {disp.sala.nombre}",
                                "start": f"{fecha_evento}T{disp.hora_inicio}",
                                "end": f"{fecha_evento}T{disp.hora_fin}",
                                "backgroundColor": "#007bff",
                                "borderColor": "#007bff",
                                "extendedProps": {
                                    "tipo": "disponibilidad",
                                    "sala": disp.sala.nombre,
                                    "usuario": disp.usuario.get_full_name(),
                                    "disponibilidad_id": disp.id,
                                },
                            }
                        )

        # ================================
        # 2️⃣ EVENTOS DE CITAS
        # ================================
        citas = CitaMedica.objects.filter(
            estado__in=["agendada", "confirmada"]
        ).select_related("disponibilidad", "disponibilidad__sala")

        for cita in citas:
            eventos.append(
                {
                    "id": f"cita_{cita.id}",
                    "title": f"Cita: {cita.nombre_paciente}",
                    "start": f"{cita.fecha_cita}T{cita.disponibilidad.hora_inicio}",
                    "end": f"{cita.fecha_cita}T{cita.disponibilidad.hora_fin}",
                    "backgroundColor": "#dc3545",
                    "borderColor": "#dc3545",
                    "extendedProps": {
                        "tipo": "cita",
                        "cita_id": cita.id,
                        "paciente": cita.nombre_paciente,
                        "email": cita.email_paciente,
                        "sala": cita.disponibilidad.sala.nombre,
                        "profesional": cita.disponibilidad.usuario.get_full_name(),
                        "motivo": cita.motivo_consulta,
                    },
                }
            )

        return JsonResponse(eventos, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def validar_conflictos_disponibilidad(
    usuario,
    sala,
    dia_semana,
    hora_inicio,
    hora_fin,
    fecha_inicio,
    fecha_fin=None,
    disponibilidad_id=None,
):
    """
    Valida conflictos de disponibilidad por fechas específicas
    """
    from datetime import datetime, date, time, timedelta

    # Convertir strings a objetos datetime si es necesario
    if isinstance(hora_inicio, str):
        hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()
    if isinstance(hora_fin, str):
        hora_fin = datetime.strptime(hora_fin, "%H:%M").time()
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    if fecha_fin and isinstance(fecha_fin, str):
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

    # Buscar disponibilidades en la misma sala
    conflictos = DisponibilidadUsuario.objects.filter(sala=sala, activa=True)

    # Excluir la disponibilidad actual si se está editando
    if disponibilidad_id:
        conflictos = conflictos.exclude(pk=disponibilidad_id)

    fecha_fin_actual = fecha_fin or date(2099, 12, 31)

    # 🔧 NUEVA LÓGICA: Validar por fechas específicas
    for disponibilidad in conflictos:
        # Verificar solapamiento de horarios
        if not (
            hora_inicio < disponibilidad.hora_fin
            and hora_fin > disponibilidad.hora_inicio
        ):
            continue  # Sin solapamiento de horarios, continuar

        # Verificar solapamiento de rangos de fechas
        fecha_fin_existente = disponibilidad.fecha_fin or date(2099, 12, 31)

        if not (
            fecha_inicio <= fecha_fin_existente
            and fecha_fin_actual >= disponibilidad.fecha_inicio
        ):
            continue  # Sin solapamiento de fechas, continuar

        # 🔧 NUEVA VALIDACIÓN: Generar fechas específicas que coinciden
        fechas_conflicto = obtener_fechas_conflicto_python(
            fecha_inicio,
            fecha_fin_actual,
            dia_semana,
            disponibilidad.fecha_inicio,
            fecha_fin_existente,
            disponibilidad.dia_semana,
        )

        if fechas_conflicto:
            usuario_ocupante = (
                disponibilidad.usuario.get_full_name()
                or disponibilidad.usuario.username
            )
            fechas_texto = ", ".join(
                [f.strftime("%d/%m/%Y") for f in fechas_conflicto[:3]]
            )
            mas_fechas = (
                f" y {len(fechas_conflicto) - 3} fecha(s) más"
                if len(fechas_conflicto) > 3
                else ""
            )

            if disponibilidad.usuario == usuario:
                return (
                    f"Ya tienes disponibilidad en las siguientes fechas: {fechas_texto}{mas_fechas} "
                    f"de {disponibilidad.hora_inicio.strftime('%H:%M')} a {disponibilidad.hora_fin.strftime('%H:%M')} "
                    f"en {sala.nombre}"
                )
            else:
                return (
                    f"Conflicto: {usuario_ocupante} ya tiene disponibilidad "
                    f"en las siguientes fechas: {fechas_texto}{mas_fechas} "
                    f"de {disponibilidad.hora_inicio.strftime('%H:%M')} a {disponibilidad.hora_fin.strftime('%H:%M')} "
                    f"en {sala.nombre}"
                )

    return None


def obtener_fechas_conflicto_python(
    fecha_inicio_1, fecha_fin_1, dia_semana_1, fecha_inicio_2, fecha_fin_2, dia_semana_2
):
    """
    Obtiene las fechas específicas que tienen conflicto entre dos disponibilidades
    """
    from datetime import timedelta

    def generar_fechas_por_dia_semana(fecha_inicio, fecha_fin, dia_semana):
        fechas = []
        fecha_actual = fecha_inicio

        # Encontrar la primera fecha que coincida con el día de la semana
        while fecha_actual.weekday() != dia_semana and fecha_actual <= fecha_fin:
            fecha_actual += timedelta(days=1)

        # Generar todas las fechas que coincidan
        while fecha_actual <= fecha_fin:
            if fecha_actual.weekday() == dia_semana:
                fechas.append(fecha_actual)
                fecha_actual += timedelta(days=7)  # Siguiente semana
            else:
                fecha_actual += timedelta(days=1)

        return fechas

    # Generar fechas para ambas disponibilidades
    fechas_1 = generar_fechas_por_dia_semana(fecha_inicio_1, fecha_fin_1, dia_semana_1)
    fechas_2 = generar_fechas_por_dia_semana(fecha_inicio_2, fecha_fin_2, dia_semana_2)

    # Encontrar fechas que coinciden
    fechas_conflicto = []
    for fecha1 in fechas_1:
        if fecha1 in fechas_2:
            fechas_conflicto.append(fecha1)

    return fechas_conflicto


def agregar_disponibilidad(request):
    try:
        sala_id = request.POST.get("sala")
        dia_semana = int(request.POST.get("dia_semana"))
        hora_inicio = request.POST.get("hora_inicio")
        hora_fin = request.POST.get("hora_fin")
        fecha_inicio = request.POST.get("fecha_inicio")
        fecha_fin = request.POST.get("fecha_fin") or None

        sala = get_object_or_404(Sala, id=sala_id, activa=True)

        # Convertir horas a datetime
        hora_inicio_dt = datetime.strptime(hora_inicio, "%H:%M")
        hora_fin_dt = datetime.strptime(hora_fin, "%H:%M")

        if hora_fin_dt <= hora_inicio_dt:
            messages.error(request, "❌ La hora fin debe ser mayor que la hora inicio.")
            return redirect("gestionar_disponibilidad")

        bloque_actual = hora_inicio_dt
        creados = 0

        while bloque_actual < hora_fin_dt:
            bloque_siguiente = bloque_actual + timedelta(hours=1)

            # Evitar pasar el límite
            if bloque_siguiente > hora_fin_dt:
                break

            conflictos = validar_conflictos_disponibilidad(
                usuario=request.user,
                sala=sala,
                dia_semana=dia_semana,
                hora_inicio=bloque_actual.time(),
                hora_fin=bloque_siguiente.time(),
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )

            if not conflictos:
                DisponibilidadUsuario.objects.create(
                    usuario=request.user,
                    sala=sala,
                    dia_semana=dia_semana,
                    hora_inicio=bloque_actual.time(),
                    hora_fin=bloque_siguiente.time(),
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                )
                creados += 1

            bloque_actual = bloque_siguiente

        if creados == 0:
            messages.error(
                request, "❌ No se pudo crear la disponibilidad por conflictos."
            )
        else:
            messages.success(
                request, f"✅ Disponibilidad creada en {creados} bloques de 1 hora."
            )

    except Exception as e:
        messages.error(request, f"❌ Error al agregar disponibilidad: {str(e)}")

    return redirect("gestionar_disponibilidad")


def eliminar_disponibilidad(request):
    try:
        disponibilidad_id = request.POST.get("disponibilidad_id")

        disponibilidad = get_object_or_404(
            DisponibilidadUsuario, id=disponibilidad_id, usuario=request.user
        )

        # ---------------------------------------------------------------------
        # 1️⃣ CANCELAR TODAS LAS CITAS ASOCIADAS A ESTA DISPONIBILIDAD
        # ---------------------------------------------------------------------
        citas = CitaMedica.objects.filter(
            disponibilidad=disponibilidad, estado="Agendada"
        )

        for cita in citas:
            paciente_email = cita.email_paciente

            # Cambiar estado de la cita
            cita.estado = "Cancelada"
            cita.save()

            # Enviar correo de cancelación
            if paciente_email:
                try:
                    send_mail(
                        subject="Cancelación de cita médica",
                        message=(
                            f"Hola {cita.nombre_paciente},\n\n"
                            "Te informamos que tu cita ha sido CANCELADA debido a cambios "
                            "en la disponibilidad del profesional.\n\n"
                            f"Fecha de la cita: {cita.fecha_cita}\n"
                            f"Hora: {cita.hora_inicio.strftime('%H:%M')} - {cita.hora_fin.strftime('%H:%M')}\n"
                            f"Sala: {cita.sala.nombre}\n\n"
                            "Por favor ingresa nuevamente al sistema para reprogramar tu cita.\n\n"
                            "Gracias por tu comprensión."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[cita.email_paciente],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"⚠️ Error enviando correo a {paciente_email}: {e}")

        # ---------------------------------------------------------------------
        # 2️⃣ ELIMINAR LA DISPONIBILIDAD
        # ---------------------------------------------------------------------
        disponibilidad.delete()

        messages.success(
            request,
            "✅ Disponibilidad eliminada. Las citas fueron canceladas y se enviaron los correos.",
        )

    except Exception as e:
        messages.error(request, f"❌ Error al eliminar disponibilidad: {str(e)}")

    return redirect("gestionar_disponibilidad")


def bloquear_fecha(request):
    try:
        disponibilidad_id = request.POST.get("disponibilidad_id")
        fecha = request.POST.get("fecha")
        hora_inicio = request.POST.get("hora_inicio_bloqueo")
        hora_fin = request.POST.get("hora_fin_bloqueo")
        motivo = request.POST.get("motivo", "")

        disponibilidad = get_object_or_404(
            DisponibilidadUsuario, id=disponibilidad_id, usuario=request.user
        )

        BloqueoDisponibilidad.objects.create(
            disponibilidad=disponibilidad,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            motivo=motivo,
        )

        messages.success(request, "Bloqueo de fecha creado correctamente.")

    except Exception as e:
        messages.error(request, f"Error al crear bloqueo: {str(e)}")

    return redirect("gestionar_disponibilidad")


def is_superuser(user):
    return user.is_superuser


@login_required
def generar_pdf_examen_generico(request, visita_examen_id):
    context = {"segment": "home"}
    html_template = loader.get_template("home/home-page.html")
    return HttpResponse(html_template.render(context, request))


# vista principal #############################################################
def home(request):
    context = {"segment": "home"}
    html_template = loader.get_template("home/home-page.html")
    return HttpResponse(html_template.render(context, request))


# Ingreso y Salida #############################################################
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            return render(
                request, "home/login.html", {"error": "Credenciales inválidas"}
            )
    return render(request, "home/login.html")


# Perfil #########################################################
@login_required
def profile_view(request):
    return render(request, "home/profile.html")


@login_required
def cambiar_contrasena(request):
    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password and confirm_password:
            if new_password == confirm_password:
                user = request.user
                user.set_password(new_password)  # Cambia la contraseña
                user.save()
                update_session_auth_hash(request, user)  # Mantiene la sesión activa
                messages.success(request, "¡Contraseña actualizada con éxito!")
                return render(request, "home/profile.html")
            else:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, "home/profile.html")
        else:
            messages.error(request, "Todos los campos son obligatorios.")

    return render(request, "home/profile.html")


# gestion de usuarios #########################################################
@login_required
@user_passes_test(is_superuser, login_url="/login/")
def administrar_usuarios(request):
    """Vista centralizada para administrar usuarios del sistema"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("index")

    # Obtener lista de usuarios
    usuarios_list = User.objects.all().order_by("-date_joined")

    # Preparar contexto inicial
    context = {
        "usuarios": usuarios_list,
        "total_usuarios": usuarios_list.count(),
        "usuarios_activos": usuarios_list.filter(is_active=True).count(),
        "administradores": usuarios_list.filter(is_superuser=True).count(),
    }

    # === PROCESAMIENTO DE ACCIONES ===
    if request.method == "POST":
        accion = request.POST.get("accion_usuario")

        # --- ACCIÓN: REGISTRAR NUEVO USUARIO ---
        if accion == "registrar":
            return _procesar_registro_usuario(request, context)

        # --- ACCIÓN: MODIFICAR USUARIO EXISTENTE ---
        elif accion == "modificar":
            return _procesar_modificacion_usuario(request, context)

        # --- ACCIÓN: ELIMINAR USUARIO ---
        elif accion == "eliminar":
            return _procesar_eliminacion_usuario(request)

    # GET - mostrar interfaz principal
    return render(request, "home/administrar_usuarios.html", context)


def _procesar_registro_usuario(request, context):
    """Función auxiliar para procesar registro de nuevo usuario"""
    try:
        # Recopilar datos del formulario
        datos_usuario = {
            "username": request.POST.get("username_nuevo"),
            "email": request.POST.get("email_nuevo"),
            "password": request.POST.get("password_nuevo"),
            "confirm_password": request.POST.get("confirmar_password"),
            "first_name": request.POST.get("nombre_usuario", ""),
            "last_name": request.POST.get("apellido_usuario", ""),
        }

        # Configuración de permisos
        permisos_usuario = {
            "is_superuser": request.POST.get("admin_permisos") == "on",
            "is_staff": request.POST.get("staff_permisos") == "on",
            "is_active": request.POST.get("activo_estado") == "on",
        }

        # Validar campos obligatorios
        if not all(
            [
                datos_usuario["username"],
                datos_usuario["email"],
                datos_usuario["password"],
            ]
        ):
            messages.error(request, "❌ Los campos básicos son obligatorios.")
            return render(request, "home/administrar_usuarios.html", context)

        # Validar coincidencia de contraseñas
        if datos_usuario["password"] != datos_usuario["confirm_password"]:
            messages.error(request, "❌ Las contraseñas no son idénticas.")
            return render(request, "home/administrar_usuarios.html", context)

        # Validar longitud de contraseña
        if len(datos_usuario["password"]) < 8:
            messages.error(request, "❌ La contraseña requiere mínimo 8 caracteres.")
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar unicidad del username
        if User.objects.filter(username=datos_usuario["username"]).exists():
            messages.error(request, "❌ Este nombre de usuario ya está registrado.")
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar unicidad del email
        if User.objects.filter(email=datos_usuario["email"]).exists():
            messages.error(request, "❌ Este correo electrónico ya está en uso.")
            return render(request, "home/administrar_usuarios.html", context)

        # Crear nuevo usuario
        nuevo_usuario = User.objects.create_user(
            username=datos_usuario["username"],
            email=datos_usuario["email"],
            password=datos_usuario["password"],
            first_name=datos_usuario["first_name"],
            last_name=datos_usuario["last_name"],
            **permisos_usuario,
        )

        # Generar descripción de tipo de usuario
        tipos_asignados = []
        if permisos_usuario["is_superuser"]:
            tipos_asignados.append("Administrador")
        if permisos_usuario["is_staff"]:
            tipos_asignados.append("Personal")
        if not permisos_usuario["is_active"]:
            tipos_asignados.append("Desactivado")

        descripcion_tipo = (
            " - ".join(tipos_asignados) if tipos_asignados else "Usuario básico"
        )

        messages.success(
            request,
            f"✅ Usuario '{datos_usuario['username']}' registrado correctamente.\n"
            f"📧 Correo: {datos_usuario['email']}\n"
            f"🔐 Tipo: {descripcion_tipo}",
        )

        return redirect("administrar_usuarios")

    except Exception as e:
        messages.error(request, f"❌ Error durante el registro: {str(e)}")
        return render(request, "home/administrar_usuarios.html", context)


def _procesar_modificacion_usuario(request, context):
    """Función auxiliar para procesar modificación de usuario"""
    try:
        user_id = request.POST.get("usuario_id")
        usuario_objetivo = get_object_or_404(User, id=user_id)

        # Datos de modificación
        nuevo_username = request.POST.get("username_modificar")
        nuevo_email = request.POST.get("email_modificar")
        nuevo_nombre = request.POST.get("nombre_modificar", "")
        nuevo_apellido = request.POST.get("apellido_modificar", "")

        # Nuevos permisos
        nuevo_admin = request.POST.get("admin_modificar") == "on"
        nuevo_staff = request.POST.get("staff_modificar") == "on"
        nuevo_activo = request.POST.get("activo_modificar") == "on"

        # Contraseña nueva (opcional)
        nueva_password = request.POST.get("nueva_password_modificar", "")
        confirmar_nueva = request.POST.get("confirmar_nueva_modificar", "")

        # Validaciones básicas
        if not nuevo_username or not nuevo_email:
            messages.error(request, "❌ Username y email son campos requeridos.")
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar username único (excluyendo usuario actual)
        if User.objects.filter(username=nuevo_username).exclude(id=user_id).exists():
            messages.error(
                request, "❌ Este username ya está ocupado por otro usuario."
            )
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar email único (excluyendo usuario actual)
        if User.objects.filter(email=nuevo_email).exclude(id=user_id).exists():
            messages.error(request, "❌ Este email ya está usado por otro usuario.")
            return render(request, "home/administrar_usuarios.html", context)

        # Validar nueva contraseña si se proporcionó
        if nueva_password:
            if nueva_password != confirmar_nueva:
                messages.error(request, "❌ Las nuevas contraseñas no coinciden.")
                return render(request, "home/administrar_usuarios.html", context)

            if len(nueva_password) < 8:
                messages.error(
                    request, "❌ La nueva contraseña debe tener mínimo 8 caracteres."
                )
                return render(request, "home/administrar_usuarios.html", context)

        # Aplicar modificaciones
        usuario_objetivo.username = nuevo_username
        usuario_objetivo.email = nuevo_email
        usuario_objetivo.first_name = nuevo_nombre
        usuario_objetivo.last_name = nuevo_apellido
        usuario_objetivo.is_superuser = nuevo_admin
        usuario_objetivo.is_staff = nuevo_staff
        usuario_objetivo.is_active = nuevo_activo

        # Cambiar contraseña si se proporcionó
        if nueva_password:
            usuario_objetivo.set_password(nueva_password)

        usuario_objetivo.save()

        messages.success(
            request, f"✅ Usuario '{nuevo_username}' modificado correctamente."
        )
        return redirect("administrar_usuarios")

    except Exception as e:
        messages.error(request, f"❌ Error durante la modificación: {str(e)}")
        return render(request, "home/administrar_usuarios.html", context)


def _procesar_eliminacion_usuario(request):
    """Función auxiliar para procesar eliminación de usuario"""
    try:
        user_id = request.POST.get("usuario_id")
        usuario_objetivo = get_object_or_404(User, id=user_id)

        # Prevenir auto-eliminación
        if usuario_objetivo.id == request.user.id:
            messages.error(request, "❌ No es posible eliminar tu propia cuenta.")
            return redirect("administrar_usuarios")

        username_eliminado = usuario_objetivo.username
        usuario_objetivo.delete()

        messages.success(
            request, f"✅ Usuario '{username_eliminado}' eliminado del sistema."
        )

    except Exception as e:
        messages.error(request, f"❌ Error durante la eliminación: {str(e)}")

    return redirect("administrar_usuarios")


# dashboard
@login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}
    html_template = loader.get_template("home/index.html")
    return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def atenea_estadisticas(request):
    context = {"segment": "atenea_estadisticas"}

    proyectos_a_buscar = [
        ("Anosognosia", "Anosognosia"),
        ("Proyecto Sueño", "Proyecto Sueño"),
        ("Envejecimiento", "Envejecimiento"),
    ]

    proyectos_info = []

    for term, label in proyectos_a_buscar:
        qs = Proyecto.objects.filter(nombre__icontains=term)

        participantes_count = 0
        exams_completed = 0
        clinical_stats = []
        genero_stats = []
        escolaridad_stats = []

        if qs.exists():
            # Participantes únicos
            patient_ids = qs.values_list("pacientes", flat=True)
            unique_patients = DatosDemograficos.objects.filter(id__in=patient_ids)

            participantes_count = unique_patients.count()

            # Distribución género
            if participantes_count > 0:
                hombres = unique_patients.filter(genero__iexact="M").count()
                mujeres = unique_patients.filter(genero__iexact="F").count()

                genero_stats = [
                    {
                        "label": "Género: Masculino",
                        "count": hombres,
                        "percent": round((hombres / participantes_count) * 100, 2),
                        "color": "primary",
                    },
                    {
                        "label": "Género: Femenino",
                        "count": mujeres,
                        "percent": round((mujeres / participantes_count) * 100, 2),
                        "color": "info",
                    },
                ]

            # Distribución escolaridad
            if participantes_count > 0:
                for nivel, color in [
                    ("primario", "warning"),
                    ("bachiller", "warning"),
                    ("universidad", "success"),
                    ("maestria", "danger"),
                    ("doctorado", "danger"),
                    ("especializacion", "danger"),
                ]:
                    count = unique_patients.filter(escolaridad__iexact=nivel).count()
                    escolaridad_stats.append(
                        {
                            "label": f"Escolaridad: {nivel}",
                            "count": count,
                            "percent": round((count / participantes_count) * 100, 2),
                            "color": color,
                        }
                    )

            # Exámenes completados
            exams_qs = VisitaExamen.objects.filter(
                visita__Tipo_visita__proyecto__in=qs,
                estado="completado",
            )
            exams_completed = exams_qs.count()

            # --- Distribución por rangos de edad ---
            rangos = [
                (18, 30, "18-30 años"),
                (31, 45, "31-45 años"),
                (46, 60, "46-60 años"),
                (61, 200, "60+ años"),  # límite alto grande
            ]

            for min_age, max_age, label_rango in rangos:
                count = unique_patients.filter(
                    edad__gte=min_age, edad__lte=max_age
                ).count()
                clinical_stats.append(
                    {
                        "rango": label_rango,
                        "count": count,
                    }
                )

        proyectos_info.append(
            {
                "term": term,
                "label": label,
                "participants": participantes_count,
                "exams_completed": exams_completed,
                "clinical_stats": clinical_stats,
                "demografia": genero_stats + escolaridad_stats,
            }
        )

    context["proyectos_info"] = proyectos_info
    return render(request, "home/statistics_atenea.html", context)


# pacientes
@login_required
def lista_pacientes(request):
    pacientes = DatosDemograficos.objects.all()
    return render(request, "home/tables.html", {"pacientes": pacientes})


@login_required
def registro_demografico(request):
    if request.method == "POST":
        try:
            datos = DatosDemograficos(
                # Datos obligatorios
                primer_nombre=request.POST["primer_nombre"],
                primer_apellido=request.POST["primer_apellido"],
                numero_documento=request.POST["numero_documento"],
                fecha_nacimiento=request.POST["fecha_nacimiento"],
                edad=request.POST["edad"],
                correo=request.POST["correo"],
                celular=request.POST["celular"],
                regimen=request.POST["regimen"],
                tipo_documento=request.POST["tipo_documento"],
                # Datos opcionales (se usa `.get()` para evitar errores si faltan)
                segundo_nombre=request.POST.get("segundo_nombre", ""),
                segundo_apellido=request.POST.get("segundo_apellido", ""),
                genero=request.POST.get("genero", ""),
                escolaridad=request.POST.get("escolaridad", ""),
                lateralidad=request.POST.get("lateralidad", ""),
                estado_civil=request.POST.get("estado_civil", ""),
                ocupacion=request.POST.get("ocupacion", ""),
                eps=request.POST.get("eps", ""),
                direccion=request.POST.get("direccion", ""),
                municipio_residencia=request.POST.get("municipio_residencia", ""),
                departamento_residencia=request.POST.get("departamento_residencia", ""),
                pais_residencia=request.POST.get("pais_residencia", ""),
                municipio_nacimiento=request.POST.get("municipio_nacimiento", ""),
                departamento_nacimiento=request.POST.get("departamento_nacimiento", ""),
                pais_nacimiento=request.POST.get("pais_nacimiento", ""),
                grupo_sanguineo=request.POST.get("grupo_sanguineo", ""),
                religion=request.POST.get("religion", ""),
            )
            datos.save()
            messages.success(request, "Datos demográficos guardados exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al guardar los datos: {str(e)}")

        return redirect("tables.html")

    if request.method == "GET":
        return render(request, "info_paciente/pacientForm.html")


@login_required
def eliminar_paciente(request, numero_documento):
    if request.method == "POST":
        paciente = get_object_or_404(
            DatosDemograficos, numero_documento=numero_documento
        )
        paciente.delete()
        messages.success(
            request, f"El paciente con documento {numero_documento} ha sido eliminado."
        )
        return redirect("tables.html")
    else:
        messages.error(request, "Método no permitido.")
        return redirect("tables.html")


@login_required
def editar_paciente(request, numero_documento):
    paciente = get_object_or_404(
        DatosDemograficos, numero_documento=numero_documento
    )  # Obtener el paciente por su ID

    if request.method == "POST":
        form = RegistroDemograficoForm(
            request.POST, instance=paciente
        )  # Cargar los datos del paciente
        if form.is_valid():
            form.save()  # Guardar los cambios
            pacientes = DatosDemograficos.objects.all()
            messages.success(request, "Datos demográficos editados exitosamente.")

            return render(request, "home/tables.html", {"pacientes": pacientes})

        else:
            messages.error(
                request,
                f"❌ Error en el formulario. Verifica los campos. {str(form.errors)}",
            )
            return render(request, "info_paciente/editPacientForm.html", {"form": form})
            # Para depuración en la consola

    # Redirigir a una página de detalle del paciente
    if request.method == "GET":
        form = RegistroDemograficoForm(
            instance=paciente
        )  # Cargar el formulario con los datos del paciente
        return render(request, "info_paciente/editPacientForm.html", {"form": form})


@login_required
def detalle_paciente(request, paciente_id):
    proyectos = Proyecto.objects.all()
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    # Obtener los proyectos en los que el paciente ya está asignado
    proyectos_asociados = paciente.proyectos.all()
    # Obtener proyectos disponibles para asignación (excluye los que ya tiene)
    proyectos_disponibles = Proyecto.objects.exclude(
        id__in=proyectos_asociados.values_list("id", flat=True)
    )

    # Obtener las visitas con sus exámenes relacionados (optimización)
    visitas_paciente = Visita.objects.filter(paciente=paciente).prefetch_related(
        "visita_examenes__examen"
    )

    if request.method == "POST":
        proyecto_id = request.POST.get("proyecto_id")
        pacientes_ids = request.POST.get("paciente_id")
        paciente = DatosDemograficos.objects.get(id=pacientes_ids)
        proyecto = Proyecto.objects.get(id=proyecto_id)
        proyecto.pacientes.add(paciente)
        proyecto.save()

    return render(
        request,
        "info_paciente/pacient.html",
        {
            "paciente": paciente,
            "proyectos": proyectos,
            "proyectos_asociados": proyectos_asociados,
            "proyectos_disponibles": proyectos_disponibles,
            "visitas_paciente": visitas_paciente,
        },
    )


#######################################################
# registro externo datos demograficos


def formulario_demografico_externo(request):
    """Permite el registro de datos demográficos desde enlace público"""
    if request.method == "POST":
        try:
            # Validar campos obligatorios
            campos_requeridos = [
                "primer_nombre",
                "primer_apellido",
                "numero_documento",
                "fecha_nacimiento",
                "edad",
                "correo",
                "celular",
                "tipo_documento",
            ]

            for campo in campos_requeridos:
                if not request.POST.get(campo):
                    raise ValueError(
                        f"El campo {campo.replace('_', ' ')} es obligatorio"
                    )

            # Verificar si ya existe un paciente con el mismo documento
            if DatosDemograficos.objects.filter(
                numero_documento=request.POST["numero_documento"]
            ).exists():
                messages.warning(
                    request, "Ya existe un registro con este número de documento."
                )
                return render(request, "info_paciente/formulario_externo.html")

            # Crear registro
            paciente_nuevo = DatosDemograficos(
                primer_nombre=request.POST["primer_nombre"].strip(),
                primer_apellido=request.POST["primer_apellido"].strip(),
                numero_documento=request.POST["numero_documento"].strip(),
                fecha_nacimiento=request.POST["fecha_nacimiento"],
                edad=request.POST["edad"],
                correo=request.POST["correo"].strip().lower(),
                celular=request.POST["celular"].strip(),
                regimen=request.POST.get("regimen", "Contributivo"),
                tipo_documento=request.POST["tipo_documento"],
                # Campos opcionales
                segundo_nombre=request.POST.get("segundo_nombre", "").strip(),
                segundo_apellido=request.POST.get("segundo_apellido", "").strip(),
                genero=request.POST.get("genero", ""),
                escolaridad=request.POST.get("escolaridad", ""),
                lateralidad=request.POST.get("lateralidad", ""),
                estado_civil=request.POST.get("estado_civil", ""),
                ocupacion=request.POST.get("ocupacion", "").strip(),
                eps=request.POST.get("eps", "").strip(),
                direccion=request.POST.get("direccion", "").strip(),
                municipio_residencia=request.POST.get(
                    "municipio_residencia", ""
                ).strip(),
                departamento_residencia=request.POST.get(
                    "departamento_residencia", ""
                ).strip(),
                pais_residencia=request.POST.get("pais_residencia", "Colombia"),
                municipio_nacimiento=request.POST.get(
                    "municipio_nacimiento", ""
                ).strip(),
                departamento_nacimiento=request.POST.get(
                    "departamento_nacimiento", ""
                ).strip(),
                pais_nacimiento=request.POST.get("pais_nacimiento", "Colombia"),
                grupo_sanguineo=request.POST.get("grupo_sanguineo", ""),
                religion=request.POST.get("religion", "").strip(),
            )

            paciente_nuevo.save()

            # ===== NUEVA FUNCIONALIDAD: VINCULAR AL PROYECTO ID 8 =====
            try:
                proyecto_automatico = Proyecto.objects.get(id=8)
                proyecto_automatico.pacientes.add(paciente_nuevo)
                proyecto_automatico.save()

            except Proyecto.DoesNotExist:
                print(
                    f"⚠️ El proyecto con ID 8 no existe. Paciente {paciente_nuevo.id} registrado sin vinculación automática."
                )
            except Exception as e:
                print(
                    f"❌ Error al vincular paciente {paciente_nuevo.id} al proyecto ID 8: {str(e)}"
                )

            # ===== NUEVA FUNCIONALIDAD: CREAR VISITA AUTOMÁTICA =====
            try:
                tipo_visita_automatico = TipoVisita.objects.get(id=7)

                # Crear visita automática
                visita_automatica = Visita.objects.create(
                    paciente=paciente_nuevo,
                    nombre="VISITA EPWORTH/MEW",
                    Tipo_visita=tipo_visita_automatico,
                    fecha=timezone.now().date(),
                )

                # Crear los exámenes asociados automáticamente según el tipo de visita
                if (
                    hasattr(tipo_visita_automatico, "examenes")
                    and tipo_visita_automatico.examenes
                ):
                    examenes_tipo_visita = tipo_visita_automatico.examenes

                    for examen_data in examenes_tipo_visita:
                        try:
                            examen = Examen.objects.get(id=examen_data["id"])
                            VisitaExamen.objects.create(
                                visita=visita_automatica,
                                examen=examen,
                                estado="pendiente",
                            )

                        except Examen.DoesNotExist:
                            print(f"⚠️ Examen con ID {examen_data['id']} no existe")
                        except Exception as e:
                            print(
                                f"❌ Error al asociar examen {examen_data['id']}: {str(e)}"
                            )

            except TipoVisita.DoesNotExist:
                print(
                    f"⚠️ El tipo de visita con ID 7 no existe. No se creó visita automática para el paciente {paciente_nuevo.id}."
                )
            except Exception as e:
                print(
                    f"❌ Error al crear visita automática para el paciente {paciente_nuevo.id}: {str(e)}"
                )
            # ===== FIN NUEVA FUNCIONALIDAD =====

            # Generar código de confirmación único
            from datetime import datetime

            codigo_confirmacion = (
                f"ATG-{paciente_nuevo.id:05d}-{datetime.now().strftime('%Y%m')}"
            )

            # Almacenar datos para la confirmación
            request.session["registro_completado"] = {
                "codigo": codigo_confirmacion,
                "nombre": f"{paciente_nuevo.primer_nombre} {paciente_nuevo.primer_apellido}",
                "documento": paciente_nuevo.numero_documento,
                "correo": paciente_nuevo.correo,
                "paciente_id": paciente_nuevo.id,
            }

            return redirect("confirmacion_registro_externo")

        except ValueError as ve:
            messages.error(request, str(ve))
        except Exception as e:
            messages.error(
                request, f"Ocurrió un error al procesar su registro: {str(e)}"
            )

        return render(request, "registro_publico/sleepFormRegister.html")

    # Método GET - mostrar formulario
    return render(request, "registro_publico/sleepFormRegister.html")


def consulta_examenes(request):
    documento = request.GET.get("documento")

    # 1. Verificar si existe un paciente con ese documento
    paciente = DatosDemograficos.objects.filter(numero_documento=documento).first()

    if not paciente:
        return JsonResponse({"demograficos_completos": False, "examenes": []})

    # 2. Buscar su visita más reciente
    visita = Visita.objects.filter(paciente=paciente).order_by("-id").first()

    if not visita:
        return JsonResponse({"demograficos_completos": True, "examenes": []})

    # 3. Buscar exámenes pendientes Y exámenes en proceso
    examenes = VisitaExamen.objects.filter(
        visita=visita, estado__in=["pendiente", "en_progreso"]
    )

    examenes_data = []

    for ve in examenes:
        # Detectar el estado para enviarlo al frontend
        estado = ve.estado  # pendiente | en_proceso

        # ======================
        # EPWORTH (id = 14)
        # ======================
        if ve.examen_id == 14:
            examenes_data.append(
                {
                    "nombre": ve.examen.nombre,
                    "estado": estado,
                    "url": f"/guardar-examen-publico-epworth/?paciente_id={paciente.id}",
                }
            )
            continue

        # ======================
        # MEW (id = 16)
        # ======================
        if ve.examen_id == 16:
            examenes_data.append(
                {
                    "nombre": ve.examen.nombre,
                    "estado": estado,
                    "url": f"/guardar-examen-publico-mew/?paciente_id={paciente.id}",
                }
            )
            continue

        # ======================
        # PITTSBURGH (id = 13)
        # ======================
        if ve.examen_id == 13:
            examenes_data.append(
                {
                    "nombre": ve.examen.nombre,
                    "estado": estado,
                    "url": f"/guardar-examen-publico-pitsburg/?paciente_id={paciente.id}",
                }
            )
            continue

        # ======================
        # OTROS
        # ======================
        examenes_data.append(
            {
                "nombre": ve.examen.nombre,
                "estado": estado,
                "url": f"/examen/{ve.id}/",
            }
        )

    return JsonResponse({"demograficos_completos": True, "examenes": examenes_data})


# ===== EXÁMENES PÚBLICOS =====


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
    """Muestra la confirmación del registro exitoso"""
    datos_sesion = request.session.get("registro_completado")
    if not datos_sesion:
        return redirect("formulario_demografico_externo")

    context = {"datos": datos_sesion}

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
@login_required
def crear_visita(request, paciente_id):
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    proyectos_asociados = paciente.proyectos.all()

    # Obtener los proyectos en los que el paciente ya está asignado
    proyectos_disponibles = Proyecto.objects.exclude(
        id__in=proyectos_asociados.values_list("id", flat=True)
    )

    # Obtener los tipos de visita disponibles para estos proyectos
    tipo_visitas = TipoVisita.objects.filter(proyecto__in=proyectos_asociados)

    if request.method == "POST":
        tipo_visita_id = request.POST.get("tipo_visita")
        fecha = request.POST.get("fecha")
        evaluador = request.user
        nombre = request.POST.get("nombre")

        # Capturar datos del acompañante
        acompanante_nombre = request.POST.get("acompanante_nombre")
        acompanante_relacion = request.POST.get("acompanante_relacion")
        acompanante_correo = request.POST.get("acompanante_correo")
        acompanante_telefono = request.POST.get("acompanante_telefono")

        tipo_visita = get_object_or_404(TipoVisita, id=tipo_visita_id)

        # Crear la visita y asignarla al paciente
        nueva_visita = Visita.objects.create(
            paciente=paciente,
            nombre=nombre,
            Tipo_visita=tipo_visita,
            fecha=fecha,
            evaluador=evaluador,
            acompanante_nombre=acompanante_nombre,
            acompanante_relacion=acompanante_relacion,
            acompanante_correo=acompanante_correo,
            acompanante_telefono=acompanante_telefono,
        )

        # Procesar los exámenes seleccionados
        examenes_seleccionados = request.POST.get("examenes_seleccionados")
        if examenes_seleccionados:
            try:
                lista_ids_examenes = json.loads(examenes_seleccionados)

                # Crear un registro VisitaExamen para cada examen seleccionado
                for examen_id in lista_ids_examenes:
                    examen = Examen.objects.get(id=examen_id)
                    VisitaExamen.objects.create(
                        visita=nueva_visita,
                        examen=examen,
                        # El campo resultado quedará como NULL
                        # Los resultados se agregarán en otra función
                    )

                # Mensaje de éxito
                messages.success(
                    request,
                    f"Visita creada con éxito con {len(lista_ids_examenes)} exámenes asociados.",
                )

            except json.JSONDecodeError as e:
                messages.error(request, "Error al procesar los exámenes seleccionados.")

            # Mensaje de éxito
            messages.success(
                request,
                f"Visita  creada con éxito con {len(lista_ids_examenes)} exámenes asociados.",
            )

        return redirect(
            "detalle_paciente", paciente_id=paciente.id
        )  # Redirige después de crear

    return render(
        request,
        "info_paciente/pacient.html",
        {
            "paciente": paciente,
            "proyectos_asociados": proyectos_asociados,
            "proyectos_disponibles": proyectos_disponibles,
            "tipo_visitas": tipo_visitas,
        },
    )


@login_required
def eliminar_v(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    paciente_id = visita.paciente.id  # Para redirigir después de eliminar

    visita.delete()
    messages.success(request, "Visita eliminada correctamente.")

    return redirect("detalle_paciente", paciente_id=paciente_id)


@login_required
def editar_v(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    paciente = visita.paciente
    tipo_visita = visita.Tipo_visita  # Tipo de visita actual
    # Obtener exámenes disponibles según el tipo de visita (vienen en JSONField)
    examenes_tipo_visita = [
        int(examen["id"]) for examen in tipo_visita.examenes
    ]  # Este es un JSONField con los exámenes permitidos

    examenes_actuales = VisitaExamen.objects.filter(visita=visita).values_list(
        "examen_id", flat=True
    )
    # Exámenes ya asociados
    examenes_disponibles = Examen.objects.filter(id__in=examenes_tipo_visita).exclude(
        id__in=examenes_actuales
    )

    if request.method == "POST":
        # Obtener datos del formulario
        visita.nombre = request.POST.get("nombre", visita.nombre)
        visita.fecha = request.POST.get("fecha", visita.fecha)
        visita.evaluador = request.POST.get("evaluador", visita.evaluador)

        # Datos del acompañante
        visita.acompanante_nombre = request.POST.get(
            "acompanante_nombre", visita.acompanante_nombre
        )
        visita.acompanante_relacion = request.POST.get(
            "acompanante_relacion", visita.acompanante_relacion
        )
        visita.acompanante_correo = request.POST.get(
            "acompanante_correo", visita.acompanante_correo
        )
        visita.acompanante_telefono = request.POST.get(
            "acompanante_telefono", visita.acompanante_telefono
        )

        # Guardar cambios en la visita
        visita.save()

        # Procesar los exámenes seleccionados
        examenes_seleccionados = request.POST.getlist("examenes_seleccionados")

        for examen_id in examenes_seleccionados:
            examen = Examen.objects.get(id=int(examen_id))  # Convertimos ID a entero
            if not VisitaExamen.objects.filter(visita=visita, examen=examen).exists():
                VisitaExamen.objects.create(visita=visita, examen=examen)

                messages.success(
                    request,
                    f"Visita actualizada con éxito con {len(examenes_seleccionados)} exámenes.",
                )
            else:
                messages.warning(request, "No se seleccionaron exámenes.")

        return redirect("detalle_paciente", paciente_id=paciente.id)
    return render(
        request,
        "info_paciente/editar_visita.html",
        {
            "visita": visita,
            "paciente": paciente,
            "examenes_actuales": examenes_actuales,
            "examenes_disponibles": examenes_disponibles,
        },
    )


# proyectos ############################################################
@login_required
@user_passes_test(is_superuser, login_url="/login/")
def proyectos(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect(
            "index"
        )  # Cambia 'home' por la vista a la que quieras redirigir

    proyectos = Proyecto.objects.all()
    examenes = Examen.objects.all()
    visitas = TipoVisita.objects.all()

    # Crear un diccionario para almacenar las visitas y exámenes por proyecto
    proyecto_data = {}
    for proyecto in proyectos:
        visitas_proyecto = visitas.filter(proyecto=proyecto)
        visitas_info = []
        for visita in visitas_proyecto:
            # Asegurar que los datos sean una lista de diccionarios
            examenes_data = (
                visita.examenes
                if isinstance(visita.examenes, list)
                else json.loads(visita.examenes)
            )

            # Extraer solo los IDs de los exámenes y convertirlos a enteros
            examenes_ids = [int(examen["id"]) for examen in examenes_data]

            # Buscar los nombres de los exámenes en la base de datos
            examenes_nombres = Examen.objects.filter(id__in=examenes_ids).values_list(
                "nombre", flat=True
            )

            visitas_info.append(
                {
                    "id": visita.id,
                    "nombre": visita.nombre,
                    "observaciones": visita.observaciones,
                    "examenes": examenes_nombres,
                }
            )
        proyecto_data[proyecto.id] = visitas_info

    context = {
        "proyectos": proyectos,
        "examenes": examenes,
        "visitas": visitas,
        "proyecto_data": proyecto_data,
    }

    if request.method == "POST":
        proyecto_form = ProyectoForm(request.POST)
        if proyecto_form.is_valid():
            proyecto_form.save()
            messages.success(request, "Proyecto creado correctamente.")

        return redirect("proyectos")

    return render(request, "home/proyectos.html", context)


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def eliminar_proyecto(request, id):
    if request.method == "POST":
        proyecto = get_object_or_404(
            Proyecto, id=id
        )  # Asegúrate de que Proyecto es el nombre del modelo de tus proyectos
        proyecto.delete()
        messages.success(request, f"El proyecto con ID {id} ha sido eliminado.")
        return redirect("proyectos")  # Redirige a la lista de proyectos, por ejemplo
    else:
        messages.error(request, "Método no permitido.")
        return redirect(
            "proyectos"
        )  # Redirige a la lista de proyectos si no es un POST


@login_required
@user_passes_test(is_superuser, login_url="/login/")
# tipos de visita visitas
def agregar_visita(request):
    proyectos = Proyecto.objects.all()
    examenes = Examen.objects.all()
    visitas = TipoVisita.objects.all()

    # Crear un diccionario para almacenar las visitas y exámenes por proyecto
    proyecto_data = {}
    for proyecto in proyectos:
        visitas_proyecto = visitas.filter(proyecto=proyecto)
        visitas_info = []
        for visita in visitas_proyecto:
            # Asegurar que los datos sean una lista de diccionarios
            examenes_data = (
                visita.examenes
                if isinstance(visita.examenes, list)
                else json.loads(visita.examenes)
            )

            # Extraer solo los IDs de los exámenes y convertirlos a enteros
            examenes_ids = [int(examen["id"]) for examen in examenes_data]

            # Buscar los nombres de los exámenes en la base de datos
            examenes_nombres = Examen.objects.filter(id__in=examenes_ids).values_list(
                "nombre", flat=True
            )
            visitas_info.append(
                {
                    "id": visita.id,
                    "nombre": visita.nombre,
                    "observaciones": visita.observaciones,
                    "examenes": examenes_nombres,
                }
            )
        proyecto_data[proyecto.id] = visitas_info

    context = {
        "proyectos": proyectos,
        "examenes": examenes,
        "visitas": visitas,
        "proyecto_data": proyecto_data,
    }

    if request.method == "POST":
        proyecto_id = request.POST.get("proyecto_id")
        nombres = request.POST.getlist("nombre_visita[]")  # Varias visitas
        observaciones_list = request.POST.getlist("observaciones[]")

        # Recibir el JSON desde el formulario y decodificarlo
        examenes_json = request.POST.get("examenes_json", "[]")
        examenes_lista = json.loads(examenes_json)  # Convertir a lista de diccionarios

        for i in range(len(nombres)):  # Crear una visita por cada nombre recibido
            TipoVisita.objects.create(
                proyecto_id=proyecto_id,
                nombre=nombres[i],
                observaciones=observaciones_list[i],
                examenes=examenes_lista,  # Guardar la lista completa de exámenes como JSON
            )

        return redirect("proyectos")

    return render(request, "home/proyectos.html", context)


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def eliminar_visita(request, id):
    # Obtener la visita o devolver un error 404 si no existe
    visita = get_object_or_404(TipoVisita, id=id)

    if request.method == "POST":
        # Luego, eliminar la visita
        visita.delete()

        # Mensaje de confirmación
        messages.success(request, "La visita ha sido eliminada correctamente.")

        return redirect(
            "proyectos"
        )  # Redirigir a la lista de proyectos o donde corresponda

    return redirect("proyectos")


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def editar_visita(request, visita_id):
    visita = get_object_or_404(TipoVisita, id=visita_id)

    if request.method == "POST":
        # Procesar el formulario de edición
        proyecto_id = request.POST.get("proyecto_id")
        nombre_visita = request.POST.get("nombre_visita")
        observaciones = request.POST.get("observaciones")
        examenes_seleccionados_ids = request.POST.getlist("examenes")

        # Actualizar los datos básicos de la visita
        visita.proyecto_id = proyecto_id
        visita.nombre = nombre_visita
        visita.observaciones = observaciones

        # Obtener los exámenes existentes (si los hay)
        examenes_existentes = visita.examenes if visita.examenes else []

        # Obtener los exámenes seleccionados por sus IDs
        examenes_seleccionados = Examen.objects.filter(
            id__in=examenes_seleccionados_ids
        )

        # Crear un diccionario de exámenes existentes para evitar duplicados
        examenes_dict = {examen["id"]: examen for examen in examenes_existentes}

        # Agregar los nuevos exámenes seleccionados
        for examen in examenes_seleccionados:
            if str(examen.id) not in examenes_dict:
                examenes_dict[str(examen.id)] = {
                    "id": examen.id,
                    "nombre": examen.nombre,
                }

        # Convertir el diccionario de vuelta a lista
        examenes_actualizados = list(examenes_dict.values())

        # Guardar los exámenes como JSON
        visita.examenes = examenes_actualizados
        visita.save()

        messages.success(request, "Visita actualizada correctamente.")
        return redirect("proyectos")


# exámenes #######################
@login_required
def realizar_examen(request, visita_id, examen_id, paciente_id):
    # Diccionario de configuración de exámenes
    exam_config = {
        3: {
            "template": "examenes_general/General_ExamenFísico.html",
            "model": ExamenFisicoResult,
        },
        4: {
            "template": "examenes_general/General_RevisiónSistemas.html",
            "model": RevisionSistemasResult,
        },
        5: {
            "template": "examenes_general/General_Antecedentes.html",
            "model": AntecedentesResult,
        },
        7: {
            "template": "examenes_general/General_Análisis.html",
            "model": AnalisisGeneralResult,
        },
        8: {
            "template": "examenes_general/General_Medicamentos.html",
            "model": MedicamentosResult,
        },
        9: {
            "template": "examenes_general/General_ExamenNeurológico.html",
            "model": ExamenNeurologicoResult,
        },
        10: {
            "template": "examenes_sueno/Sueno_anamnesis.html",
            "model": SuenoAnamnesisResult,
        },
        11: {"template": "examenes_sueno/Sueño_Cuestionarios.html", "model": None},
        12: {
            "template": "examenes_sueno/Sueño_ExamenFisico.html",
            "model": SuenoFisicoResult,
        },
        13: {
            "template": "examenes_sueno/sueno_Pitsburg.html",
            "model": PittsburghResult,
        },
        14: {"template": "examenes_sueno/sueno_Epworth.html", "model": EpworthResult},
        15: {
            "template": "examenes_sueno/sueno_Stop_Bang.html",
            "model": StopBangResult,
        },
        16: {"template": "examenes_sueno/sueno_MEW.html", "model": MEWResult},
        17: {"template": "examenes_sueno/sueno_Berlín.html", "model": BerlinResult},
        18: {"template": "examenes_sueno/sueno_atenas.html", "model": AtenasResult},
        19: {"template": "examenes_sueno/sueno_ISI.html", "model": ISIResult},
        20: {
            "template": "examenes_general/cognitivo_Anamnesis.html",
            "model": CognitivoAnamnesisResult,
        },
        21: {
            "template": "examenes_anosognosia/Anosognosia_Participante_EuroQoL.html",
            "model": EuroQol5D5LResult,
        },
        22: {
            "template": "examenes_anosognosia/Anosognosia_Participante_EVA_EuroQoL.html",
            "model": EuroQolEVASaludResult,
        },
        23: {
            "template": "examenes_anosognosia/Anosognosia_Participante_Yesavage.html",
            "model": ParticipanteYesavageResult,
        },
        24: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_NPI.html",
            "model": CuidadorNPIResult,
        },
        25: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_LawtonBrody.html",
            "model": LawtonBrodyResult,
        },
        26: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_CalidadVida_BettyFerrel.html",
            "model": BettyFerrelResult,
        },
        27: {
            "template": "examenes_anosognosia/Anosognosia_Participante_MoCA.html",
            "model": MoCAResult,
        },
        28: {
            "template": "examenes_anosognosia/Anosognosia_Participante_AdherenciaTerapeutica.html",
            "model": AdherenciaTerapeuticaResult,
        },
        29: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_EscalaZarit.html",
            "model": ZaritResult,
        },
        30: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_AQD.html",
            "model": AQDCuidadorResult,
        },
        31: {
            "template": "examenes_anosognosia/Anosognosia_Participante_AQD.html",
            "model": AQDParticipanteResult,
        },
        32: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_RedLatSpanish.html",
            "model": RedLatSpanishResult,
        },
        33: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_CDR.html",
            "model": CDRCuidadorResult,
        },
        34: {
            "template": "examenes_anosognosia/Anosognosia_Participante_CDR.html",
            "model": CDRParticipanteResult,
        },
        35: {
            "template": "examenes_anosognosia/CDR_Evaluacion_Clinica.html",
            "model": PuntajeCDRResult,
        },
        36: {
            "template": "examenes_anosognosia/Consentimiento_Informado_Participante.html",
            "model": ConsentimientoInformadoParticipanteResult,
        },
        37: {
            "template": "examenes_anosognosia/Consentimiento_Informado_Cuidador.html",
            "model": ConsentimientoInformadoCuidadorResult,
        },
        38: {
            "template": "examenes_anosognosia/Anamnesis_Cuidador_ANG.html",
            "model": AnamnesisCuidadorResult,
        },
        39: {
            "template": "examenes_anosognosia/Anamnesis_Participante_ANG.html",
            "model": AnamnesisParticipanteResult,
        },
        40: {
            "template": "examenes_anosognosia/SeguimientoIntervenciones_ANG.html",
            "model": SeguimientoIntervencionesResult,
        },
    }

    config = exam_config.get(int(examen_id))
    if not config:
        messages.error(request, "Examen no encontrado")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    # Obtener datos existentes
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    datos_examen = None
    visita_examen_obj = None
    modo_edicion = False

    try:
        visita_examen_obj = VisitaExamen.objects.get(
            visita_id=visita_id, examen_id=examen_id
        )

        if config["model"] and visita_examen_obj.esta_realizado:
            resultado = visita_examen_obj.get_resultado_instance()
            if resultado and isinstance(resultado, config["model"]):
                # ===================================================
                # CASO ESPECIAL: ANAMNESIS DE SUEÑO (ID 10)
                # ===================================================
                if int(examen_id) == 10 and isinstance(resultado, SuenoAnamnesisResult):
                    # Obtener datos básicos del modelo principal
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)

                    # Obtener relaciones hijas con prefetch para optimización
                    anamnesis = SuenoAnamnesisResult.objects.prefetch_related(
                        "sustancias",
                        "medicamentos",
                        "pantallas",
                        "actividades_en_cama",
                        "actividades_fisicas",
                        "sintomas_suenos",
                        "sintomas_diurno",
                        "tipos_queja_detalle",
                    ).get(id=resultado.id)

                    # Agregar las relaciones al diccionario de datos
                    datos_examen["sustancias"] = list(
                        anamnesis.sustancias.values(
                            "tipo", "cantidad", "frecuencia", "tiempo", "observaciones"
                        )
                    )

                    datos_examen["medicamentos"] = list(
                        anamnesis.medicamentos.values(
                            "nombre",
                            "dosis",
                            "presentacion",
                            "veces_dia",
                            "frecuencia",
                            "tiempo",
                            "observaciones",
                        )
                    )

                    datos_examen["pantallas"] = list(
                        anamnesis.pantallas.values(
                            "tipo", "frecuencia", "tiempo_antes_dormir"
                        )
                    )

                    datos_examen["actividades_en_cama"] = list(
                        anamnesis.actividades_en_cama.values(
                            "tipo", "frecuencia", "observaciones"
                        )
                    )

                    datos_examen["actividades_fisicas"] = list(
                        anamnesis.actividades_fisicas.values(
                            "tipo",
                            "otro_texto",
                            "intensidad",
                            "frecuencia",
                            "observaciones",
                        )
                    )

                    datos_examen["sintomas_suenos"] = list(
                        anamnesis.sintomas_suenos.values(
                            "tipo",
                            "cuando_inicio",
                            "evolucion",
                            "frecuencia",
                            "gravedad",
                            "observaciones",
                        )
                    )

                    datos_examen["sintomas_diurnos"] = list(
                        anamnesis.sintomas_diurno.values(
                            "tipo",
                            "cuando_inicio",
                            "evolucion",
                            "frecuencia",
                            "gravedad",
                            "observaciones",
                        )
                    )

                    datos_examen["tipos_queja"] = list(
                        anamnesis.tipos_queja_detalle.values(
                            "nombre", "inicio", "evolucion", "frecuencia", "gravedad"
                        )
                    )

                    # AGREGAR ESTAS LÍNEAS PARA PASAR AL CONTEXTO DEL TEMPLATE:
                    tipos_queja = datos_examen["tipos_queja"]
                    sustancias = datos_examen["sustancias"]
                    medicamentos = datos_examen["medicamentos"]
                    pantallas = datos_examen["pantallas"]
                    actividades_en_cama = datos_examen["actividades_en_cama"]
                    actividades_fisicas = datos_examen["actividades_fisicas"]
                    sintomas_suenos = datos_examen["sintomas_suenos"]
                    sintomas_diurnos = datos_examen["sintomas_diurnos"]

                    modo_edicion = True

                # ===================================================
                # CASO ESPECIAL: ANÁLISIS GENERAL (ID 7)
                # ===================================================
                elif int(examen_id) == 7 and isinstance(
                    resultado, AnalisisGeneralResult
                ):
                    # Obtener datos básicos del modelo principal
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)

                    # Obtener relaciones hijas con prefetch para optimización
                    analisis = AnalisisGeneralResult.objects.prefetch_related(
                        "diagnosticos_cie10",
                        "diagnosticos_dsmv",
                        "diagnosticos_icsd3",
                        "diagnosticos_no_clasificados",
                    ).get(id=resultado.id)

                    # Agregar las relaciones al diccionario de datos
                    datos_examen["diagnosticos_cie10"] = list(
                        analisis.diagnosticos_cie10.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    datos_examen["diagnosticos_dsmv"] = list(
                        analisis.diagnosticos_dsmv.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    datos_examen["diagnosticos_icsd3"] = list(
                        analisis.diagnosticos_icsd3.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    datos_examen["diagnosticos_no_clasificados"] = list(
                        analisis.diagnosticos_no_clasificados.values(
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    modo_edicion = True

                else:
                    # ===================================================
                    # CASO GENERAL: OTROS EXÁMENES
                    # ===================================================
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)
                    modo_edicion = True

            # CASO ESPECIAL: ANTECEDENTES (ID 5) - FUERA DEL IF ANTERIOR
            # ===================================================
            elif int(examen_id) == 5:
                # Para antecedentes, verificar si existe un AntecedentesVisitaLink
                try:
                    antecedentes_link = AntecedentesVisitaLink.objects.get(
                        visita_examen=visita_examen_obj
                    )
                    antecedentes_result = antecedentes_link.antecedentes_result

                    if antecedentes_result:
                        # Obtener datos básicos del modelo principal
                        datos_examen = model_to_dict(antecedentes_result)
                        datos_examen.pop("id", None)
                        datos_examen.pop("paciente", None)

                        # Obtener relaciones hijas con prefetch para optimización
                        antecedentes = AntecedentesResult.objects.prefetch_related(
                            "antecedentes_patologicos",
                            "antecedentes_quirurgicos",
                            "antecedentes_farmacologicos",
                            "antecedentes_toxicos",
                            "antecedentes_familiares",
                            "antecedentes_alergicos",
                            "antecedentes_traumaticos",
                            "antecedentes_gineco",
                            "antecedentes_epidemiologicos",
                            "antecedentes_ets",
                            "antecedentes_hospitalizaciones",
                            "antecedentes_inmunizaciones",
                            "antecedentes_transfusionales",
                        ).get(id=antecedentes_result.id)

                        # Agregar las relaciones al diccionario de datos
                        datos_examen["patologicos"] = list(
                            antecedentes.antecedentes_patologicos.values(
                                "tipo_patologia",
                                "descripcion_otros",
                                "fecha_inicio",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["quirurgicos"] = list(
                            antecedentes.antecedentes_quirurgicos.values(
                                "descripcion",
                                "fecha_intervencion",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["farmacologicos"] = list(
                            antecedentes.antecedentes_farmacologicos.values(
                                "descripcion",
                                "fecha_inicio",
                                "recibio_tratamiento",
                                "detalle_tratamiento",
                                "tuvo_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["toxicos"] = list(
                            antecedentes.antecedentes_toxicos.values(
                                "tipos_toxico",
                                "descripcion_otros",
                                "fecha_inicio",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["familiares"] = list(
                            antecedentes.antecedentes_familiares.values(
                                "tipo_antecedente", "parentesco", "observaciones"
                            )
                        )

                        datos_examen["alergicos"] = list(
                            antecedentes.antecedentes_alergicos.values(
                                "descripcion",
                                "fecha_inicio",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["traumaticos"] = list(
                            antecedentes.antecedentes_traumaticos.values(
                                "descripcion",
                                "fecha_inicio",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        # Gineco-obstétricos (OneToOne)
                        if (
                            hasattr(antecedentes, "antecedentes_gineco")
                            and antecedentes.antecedentes_gineco
                        ):
                            gineco_data = model_to_dict(
                                antecedentes.antecedentes_gineco
                            )
                            gineco_data.pop("id", None)
                            gineco_data.pop("antecedente_result", None)
                            datos_examen["gineco_obstetricos"] = gineco_data
                        else:
                            datos_examen["gineco_obstetricos"] = {}

                        datos_examen["epidemiologicos"] = list(
                            antecedentes.antecedentes_epidemiologicos.values(
                                "tipo_antecedente",
                                "fecha_inicio",
                                "tratamiento_detalle",
                                "complicaciones_asociadas",
                                "detallar_complicaciones",
                                "activo_actualmente",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["ets"] = list(
                            antecedentes.antecedentes_ets.values(
                                "tipo_ets",
                                "fecha_diagnostico",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "detalle_complicaciones",
                                "curado",
                                "fecha_curacion",
                                "observaciones",
                            )
                        )

                        datos_examen["hospitalizaciones"] = list(
                            antecedentes.antecedentes_hospitalizaciones.values(
                                "motivo_hospitalizacion",
                                "fecha_ingreso",
                                "fecha_egreso",
                                "duracion",
                                "institucion",
                                "observaciones",
                            )
                        )

                        datos_examen["inmunizaciones"] = list(
                            antecedentes.antecedentes_inmunizaciones.values(
                                "nombre_vacuna",
                                "fecha_aplicacion",
                                "dosis_numero",
                                "observaciones",
                            )
                        )

                        datos_examen["transfusionales"] = list(
                            antecedentes.antecedentes_transfusionales.values(
                                "motivo_transfusion",
                                "fecha_transfusion",
                                "tipo_componente",
                                "cantidad_unidades",
                                "tuvo_reacciones",
                                "detalle_reacciones",
                                "observaciones",
                            )
                        )

                        modo_edicion = True

                except AntecedentesVisitaLink.DoesNotExist:
                    # No hay antecedentes previos para esta visita
                    pass

            # ===================================================
            # CASO ESPECIAL: REVISIÓN POR SISTEMAS (ID 4)
            # ===================================================
            elif int(examen_id) == 4 and isinstance(resultado, RevisionSistemasResult):
                # Obtener datos básicos del modelo principal
                datos_examen = model_to_dict(resultado)
                datos_examen.pop("id", None)
                datos_examen.pop("visita_examen", None)

                # Obtener los detalles de síntomas relacionados
                detalles = DetalleRevisionSistemas.objects.filter(
                    revision_sistemas_result=resultado
                ).order_by("sistema", "sintoma")

                # Organizar detalles por sistema para el template
                sistemas_detalles = {}
                for detalle in detalles:
                    if detalle.sistema not in sistemas_detalles:
                        sistemas_detalles[detalle.sistema] = []

                    sistemas_detalles[detalle.sistema].append(
                        {
                            "sintoma": detalle.sintoma,
                            "tiempo": detalle.tiempo,
                            "caracteristicas": detalle.caracteristicas,
                        }
                    )

                datos_examen["sistemas_detalles"] = sistemas_detalles

                modo_edicion = True

            # En la vista realizar_examen, agregar después de los otros casos especiales:

            # ===================================================
            # CASO ESPECIAL: EXAMEN NEUROLÓGICO (ID 5)
            # ===================================================
            elif int(examen_id) == 5 and isinstance(resultado, ExamenNeurologicoResult):
                # Obtener datos básicos del modelo
                datos_examen = model_to_dict(resultado)
                datos_examen.pop("id", None)
                datos_examen.pop("visita_examen", None)

                # Formatear campos None como cadenas vacías para el template
                for field_name, field_value in datos_examen.items():
                    if field_value is None:
                        datos_examen[field_name] = ""
                    elif isinstance(field_value, bool):
                        datos_examen[field_name] = field_value
                    elif hasattr(field_value, "strftime"):  # Es una fecha
                        datos_examen[field_name] = field_value.strftime("%Y-%m-%d")

                # Generar resumen para debug
                resumen = resultado.get_resumen_examen()
                alteraciones_pares = resultado.get_alteraciones_pares_craneales()
                alteraciones_sensibilidad = resultado.get_alteraciones_sensibilidad()
                reflejos_alterados = resultado.get_reflejos_alterados()

                modo_edicion = True

    except VisitaExamen.DoesNotExist:
        messages.error(request, "Visita-examen no encontrada")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    context = {
        "visita_examen": visita_id,
        "paciente_id": paciente_id,
        "examen_id": examen_id,
        "datos_examen": datos_examen,
        "modo_edicion": modo_edicion,
        "visita_examen_obj": visita_examen_obj,
        "paciente": paciente,
    }

    # Si es anamnesis de sueño, agregar datos adicionales
    if int(examen_id) == 10 and datos_examen and "tipos_queja" in datos_examen:
        context.update(
            {
                "tipos_queja": datos_examen["tipos_queja"],
                "sustancias": datos_examen["sustancias"],
                "medicamentos": datos_examen["medicamentos"],
                "pantallas": datos_examen["pantallas"],
                "actividades_en_cama": datos_examen["actividades_en_cama"],
                "actividades_fisicas": datos_examen["actividades_fisicas"],
                "sintomas_suenos": datos_examen["sintomas_suenos"],
                "sintomas_diurnos": datos_examen["sintomas_diurnos"],
            }
        )

    return render(request, config["template"], context)


@login_required
def ver_resultado_examen(request, visita_examen_id):
    visita_examen = get_object_or_404(VisitaExamen, id=visita_examen_id)

    if not visita_examen.esta_realizado:
        messages.error(request, "Este examen aún no ha sido completado.")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )

    # SeguimientoIntervenciones - es diferente al resto
    if visita_examen.examen.nombre == "SeguimientoIntervencionesParticipantes_ANG":
        sesiones = SeguimientoIntervencionesResult.objects.filter(
            visita_examen=visita_examen
        ).order_by("numero_sesion")

        paciente = visita_examen.visita.paciente

        context = {
            "visita_examen": visita_examen,
            "sesiones": sesiones,
            "paciente": paciente,
        }
        return render(
            request,
            "examenes_resultados/resultado_seguimientointervenciones.html",
            context,
        )

    # Obtener resultado usando el método get_resultado_instance
    resultado = visita_examen.get_resultado_instance()

    # 4. Verificar relaciones ManyToMany posibles
    for field in [
        "actitudes",
        "atenciones",
        "errores_lenguaje",
        "actividades_vida_diaria",
        "actividades_complejas",
    ]:
        try:
            rel = getattr(resultado, field)
        except AttributeError:
            pass
        except Exception as e:
            pass

    if not resultado:
        messages.error(request, "No se encontraron resultados para este examen.")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )

    # ===== CASOS ESPECIALES CON RELACIONES =====

    # CASO: ANAMNESIS DE SUEÑO (ID 10)
    if visita_examen.examen.id == 10 and isinstance(resultado, SuenoAnamnesisResult):
        # Para anamnesis de sueño, mostrar template específico con relaciones
        anamnesis = SuenoAnamnesisResult.objects.prefetch_related(
            "sustancias",
            "medicamentos",
            "pantallas",
            "actividades_en_cama",
            "actividades_fisicas",
            "sintomas_suenos",
            "sintomas_diurno",
            "tipos_queja_detalle",
        ).get(id=resultado.id)

        context = {
            "visita_examen": visita_examen,
            "resultado": anamnesis,
            "paciente": visita_examen.visita.paciente,
            # Incluir relaciones específicas
            "sustancias": anamnesis.sustancias.all(),
            "medicamentos": anamnesis.medicamentos.all(),
            "pantallas": anamnesis.pantallas.all(),
            "actividades_en_cama": anamnesis.actividades_en_cama.all(),
            "actividades_fisicas": anamnesis.actividades_fisicas.all(),
            "sintomas_suenos": anamnesis.sintomas_suenos.all(),
            "sintomas_diurnos": anamnesis.sintomas_diurno.all(),
            "tipos_queja": anamnesis.tipos_queja_detalle.all(),
        }
        return render(
            request, "examenes_resultados/resultado_sueno_anamnesis.html", context
        )

    # CASO: COGNITIVO ANAMNESIS (ID 20) - CORRECCIÓN PRINCIPAL
    elif visita_examen.examen.id == 20:  # ✅ QUITA el isinstance(), solo verifica ID
        try:
            # Obtener el resultado directamente desde la relación
            cognitivo_anamnesis = visita_examen.cognitivo_anamnesis_resultado

            if cognitivo_anamnesis:
                # Pre-cargar las relaciones
                cognitivo_anamnesis = CognitivoAnamnesisResult.objects.prefetch_related(
                    "actitudes",
                    "atenciones",
                    "errores_lenguaje",
                    "actividades_vida_diaria",
                    "actividades_complejas",
                ).get(id=cognitivo_anamnesis.id)

                context = {
                    "visita_examen": visita_examen,
                    "resultado": cognitivo_anamnesis,
                    "paciente": visita_examen.visita.paciente,
                    "actitudes": cognitivo_anamnesis.actitudes.all(),
                    "atenciones": cognitivo_anamnesis.atenciones.all(),
                    "errores_lenguaje": cognitivo_anamnesis.errores_lenguaje.all(),
                    "actividades_vida_diaria": cognitivo_anamnesis.actividades_vida_diaria.all(),
                    "actividades_complejas": cognitivo_anamnesis.actividades_complejas.all(),
                }

                return render(
                    request,
                    "examenes_resultados/resultado_cognitivo_Anamnesis.html",
                    context,
                )
            else:
                messages.error(
                    request,
                    "No se encontraron resultados del examen cognitivo para esta visita.",
                )
                return redirect(
                    "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
                )

        except CognitivoAnamnesisResult.DoesNotExist:
            messages.error(
                request,
                "No se encontraron resultados del examen cognitivo para esta visita.",
            )
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

        except Exception as e:
            messages.error(request, f"Error al cargar el examen cognitivo: {str(e)}")
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

    # CASO: ANÁLISIS GENERAL (ID 7)
    elif visita_examen.examen.id == 7:
        # 🔧 CORRECCIÓN: Obtener la instancia correcta del modelo
        try:
            # Buscar directamente el resultado por visita_examen
            analisis_result = AnalisisGeneralResult.objects.get(
                visita_examen=visita_examen
            )

            # Obtener los diagnósticos relacionados con prefetch para optimización
            analisis = AnalisisGeneralResult.objects.prefetch_related(
                "diagnosticos_cie10",
                "diagnosticos_dsmv",
                "diagnosticos_icsd3",
                "diagnosticos_no_clasificados",
            ).get(id=analisis_result.id)

            context = {
                "visita_examen": visita_examen,
                "resultado": analisis,  # 🔧 Usar la instancia correcta
                "paciente": visita_examen.visita.paciente,
                # Incluir diagnósticos específicos
                "diagnosticos_cie10": analisis.diagnosticos_cie10.all(),
                "diagnosticos_dsmv": analisis.diagnosticos_dsmv.all(),
                "diagnosticos_icsd3": analisis.diagnosticos_icsd3.all(),
                "diagnosticos_no_clasificados": analisis.diagnosticos_no_clasificados.all(),
            }
            return render(
                request, "examenes_resultados/resultado_analisis_general.html", context
            )

        except AnalisisGeneralResult.DoesNotExist:
            messages.error(
                request,
                "No se encontraron resultados de análisis general para esta visita.",
            )
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

        except Exception as e:
            messages.error(request, f"Error al cargar el análisis general: {str(e)}")
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

    # CASO: ANTECEDENTES (ID 5)
    elif visita_examen.examen.id == 5:
        try:
            antecedentes_link = AntecedentesVisitaLink.objects.get(
                visita_examen=visita_examen
            )
            antecedentes_result = antecedentes_link.antecedentes_result

            if antecedentes_result:
                # Cargar antecedentes con todas sus relaciones
                antecedentes = AntecedentesResult.objects.prefetch_related(
                    "antecedentes_patologicos",
                    "antecedentes_quirurgicos",
                    "antecedentes_farmacologicos",
                    "antecedentes_toxicos",
                    "antecedentes_familiares",
                    "antecedentes_alergicos",
                    "antecedentes_traumaticos",
                    "antecedentes_gineco",
                    "antecedentes_epidemiologicos",
                    "antecedentes_ets",
                    "antecedentes_hospitalizaciones",
                    "antecedentes_inmunizaciones",
                    "antecedentes_transfusionales",
                ).get(id=antecedentes_result.id)

                context = {
                    "visita_examen": visita_examen,
                    "resultado": antecedentes,
                    "paciente": visita_examen.visita.paciente,
                    # Incluir todas las relaciones de antecedentes
                    "patologicos": antecedentes.antecedentes_patologicos.all(),
                    "quirurgicos": antecedentes.antecedentes_quirurgicos.all(),
                    "farmacologicos": antecedentes.antecedentes_farmacologicos.all(),
                    "toxicos": antecedentes.antecedentes_toxicos.all(),
                    "familiares": antecedentes.antecedentes_familiares.all(),
                    "alergicos": antecedentes.antecedentes_alergicos.all(),
                    "traumaticos": antecedentes.antecedentes_traumaticos.all(),
                    "gineco_obstetricos": antecedentes.antecedentes_gineco
                    if hasattr(antecedentes, "antecedentes_gineco")
                    else None,
                    "epidemiologicos": antecedentes.antecedentes_epidemiologicos.all(),
                    "ets": antecedentes.antecedentes_ets.all(),
                    "hospitalizaciones": antecedentes.antecedentes_hospitalizaciones.all(),
                    "inmunizaciones": antecedentes.antecedentes_inmunizaciones.all(),
                    "transfusionales": antecedentes.antecedentes_transfusionales.all(),
                }
                return render(
                    request, "examenes_resultados/resultado_antecedentes.html", context
                )
            else:
                messages.error(
                    request, "No se encontraron antecedentes para esta visita."
                )
                return redirect(
                    "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
                )

        except AntecedentesVisitaLink.DoesNotExist:
            messages.error(request, "No se encontraron antecedentes para esta visita.")
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

    # CASO: REVISIÓN POR SISTEMAS (ID 4)
    elif visita_examen.examen.id == 4:
        # 🔧 CORRECCIÓN: Obtener la instancia correcta del modelo
        try:
            # Buscar directamente el resultado por visita_examen
            revision_result = RevisionSistemasResult.objects.get(
                visita_examen=visita_examen
            )

            # Obtener los detalles de síntomas relacionados
            detalles = DetalleRevisionSistemas.objects.filter(
                revision_sistemas_result=revision_result
            ).order_by("sistema", "sintoma")

            # Organizar detalles por sistema
            sistemas_detalles = {}
            for detalle in detalles:
                if detalle.sistema not in sistemas_detalles:
                    sistemas_detalles[detalle.sistema] = []
                sistemas_detalles[detalle.sistema].append(detalle)

            context = {
                "visita_examen": visita_examen,
                "resultado": revision_result,  # 🔧 Usar la instancia correcta
                "paciente": visita_examen.visita.paciente,
                "sistemas_detalles": sistemas_detalles,
            }
            return render(
                request, "examenes_resultados/resultado_revision_sistemas.html", context
            )

        except RevisionSistemasResult.DoesNotExist:
            messages.error(
                request,
                "No se encontraron resultados de revisión por sistemas para esta visita.",
            )
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

        except Exception as e:
            messages.error(request, f"Error al cargar los resultados: {str(e)}")
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

    # En la función ver_resultado_examen, reemplaza el caso de MEDICAMENTOS (ID 8):

    # CASO: MEDICAMENTOS (ID 8)
    elif visita_examen.examen.id == 8:
        # 🔧 CORRECCIÓN: Obtener la instancia correcta del modelo
        try:
            # Buscar directamente el resultado por visita_examen
            medicamentos_result = MedicamentosResult.objects.get(
                visita_examen=visita_examen
            )

            # Obtener los medicamentos relacionados
            medicamentos = medicamentos_result.medicamentos.all().order_by(
                "nombre_comercial"
            )

            context = {
                "visita_examen": visita_examen,
                "resultado": medicamentos_result,  # 🔧 Usar la instancia correcta
                "paciente": visita_examen.visita.paciente,
                "medicamentos": medicamentos,
            }
            return render(
                request, "examenes_resultados/resultado_medicamentos.html", context
            )

        except MedicamentosResult.DoesNotExist:
            messages.error(
                request,
                "No se encontraron resultados de medicamentos para esta visita.",
            )
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )

        except Exception as e:
            messages.error(request, f"Error al cargar los medicamentos: {str(e)}")
            return redirect(
                "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
            )
    # ===== CASO GENÉRICO PARA OTROS EXÁMENES =====
    else:
        # Para exámenes sin relaciones complejas, usar el caso genérico
        datos_resultado = {}

        # Iterar sobre los campos del modelo (no sobre RelatedManager)
        for field in resultado._meta.fields:
            if field.name != "visita_examen":
                valor = getattr(resultado, field.name)
                datos_resultado[field.verbose_name or field.name] = valor

        context = {
            "visita_examen": visita_examen,
            "resultado": resultado,
            "datos_resultado": datos_resultado,
            "paciente": visita_examen.visita.paciente,
        }
        return render(request, "examenes_resultados/resultado_generico.html", context)


@login_required
def guardar_examen_cognitivo_anamnesis(request):
    """Vista específica para guardar el examen cognitivo anamnesis"""
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
            cognitivo_anamnesis, created = (
                CognitivoAnamnesisResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults={
                        # ========== ANAMNESIS ==========
                        "motivo_consulta": request.POST.get("motivo_consulta", ""),
                        "descripcion_general": request.POST.get(
                            "descripcion_general", ""
                        ),
                        # ========== APARIENCIA/ACTITUD ==========
                        "apariencia_descripcion": request.POST.get(
                            "apariencia_descripcion", ""
                        ),
                        "apariencia_estado": request.POST.get("apariencia_estado", ""),
                        "actitud_descripcion": request.POST.get(
                            "actitud_descripcion", ""
                        ),
                        # ========== ESTADO DE ALERTA/ORIENTACIÓN ==========
                        "estado_alerta_descripcion": request.POST.get(
                            "estado_alerta_descripcion", ""
                        ),
                        "estado_alerta_seleccion": request.POST.get(
                            "estado_alerta_seleccion", ""
                        ),
                        "orientacion_descripcion": request.POST.get(
                            "orientacion_descripcion", ""
                        ),
                        "orientacion_seleccion": request.POST.get(
                            "orientacion_seleccion", ""
                        ),
                        # ========== ATENCIÓN ==========
                        "atencion_descripcion": request.POST.get(
                            "atencion_descripcion", ""
                        ),
                        # ========== MEMORIA ==========
                        "memoria_descripcion": request.POST.get(
                            "memoria_descripcion", ""
                        ),
                        "memoria_lopera_vida": safe_int_optional(
                            request.POST.get("memoria_lopera_vida")
                        ),
                        "memoria_lopera_actual": safe_int_optional(
                            request.POST.get("memoria_lopera_actual")
                        ),
                        "memoria_quejas": request.POST.get("memoria_quejas", ""),
                        "memoria_edad_inicio": safe_int_optional(
                            request.POST.get("memoria_edad_inicio")
                        ),
                        "memoria_progresivas": request.POST.get(
                            "memoria_progresivas", ""
                        ),
                        "memoria_cambio_previo": request.POST.get(
                            "memoria_cambio_previo", ""
                        ),
                        "memoria_compromete_basicas": request.POST.get(
                            "memoria_compromete_basicas", ""
                        ),
                        "memoria_compromete_complejas": request.POST.get(
                            "memoria_compromete_complejas", ""
                        ),
                        "memoria_compromete_cotidiana": request.POST.get(
                            "memoria_compromete_cotidiana", ""
                        ),
                        # ========== LENGUAJE ==========
                        "lenguaje_descripcion": request.POST.get(
                            "lenguaje_descripcion", ""
                        ),
                        "lenguaje_cantidad": request.POST.get("lenguaje_cantidad", ""),
                        "lenguaje_fluido": request.POST.get("lenguaje_fluido", ""),
                        "lenguaje_tono": request.POST.get("lenguaje_tono", ""),
                        "lenguaje_articulacion": request.POST.get(
                            "lenguaje_articulacion", ""
                        ),
                        "lenguaje_comprension": request.POST.get(
                            "lenguaje_comprension", ""
                        ),
                        "lenguaje_escritura": request.POST.get(
                            "lenguaje_escritura", ""
                        ),
                        "lenguaje_lectura": request.POST.get("lenguaje_lectura", ""),
                        "lenguaje_repeticion": request.POST.get(
                            "lenguaje_repeticion", ""
                        ),
                        # ========== PENSAMIENTO ==========
                        "pensamiento_descripcion": request.POST.get(
                            "pensamiento_descripcion", ""
                        ),
                        "pensamiento_forma": request.POST.get("pensamiento_forma", ""),
                        "pensamiento_contenido": request.POST.get(
                            "pensamiento_contenido", ""
                        ),
                        "pensamiento_juicio": request.POST.get(
                            "pensamiento_juicio", ""
                        ),
                        "pensamiento_introspeccion": request.POST.get(
                            "pensamiento_introspeccion", ""
                        ),
                        "pensamiento_prospeccion": request.POST.get(
                            "pensamiento_prospeccion", ""
                        ),
                        # ========== SENSOPERCEPCIÓN ==========
                        "sensopercepcion_descripcion": request.POST.get(
                            "sensopercepcion_descripcion", ""
                        ),
                        "sensopercepcion_alteraciones": request.POST.get(
                            "sensopercepcion_alteraciones", ""
                        ),
                        # ========== FUNCIÓN EJECUTIVA ==========
                        "funcion_ejecutiva_descripcion": request.POST.get(
                            "funcion_ejecutiva_descripcion", ""
                        ),
                        "funcion_ejecutiva_comportamientos": request.POST.get(
                            "funcion_ejecutiva_comportamientos", ""
                        ),
                        "comportamiento_edad_inicio": request.POST.get(
                            "comportamiento_edad_inicio", ""
                        ),
                        "comportamiento_caracteristicas": request.POST.get(
                            "comportamiento_caracteristicas", ""
                        ),
                        "funcion_ejecutiva_sintomas": request.POST.get(
                            "funcion_ejecutiva_sintomas", ""
                        ),
                        "sintomas_edad_inicio": request.POST.get(
                            "sintomas_edad_inicio", ""
                        ),
                        "sintomas_caracteristicas": request.POST.get(
                            "sintomas_caracteristicas", ""
                        ),
                        # ========== ESTADO DE ÁNIMO/AFECTO ==========
                        "estado_animo_descripcion": request.POST.get(
                            "estado_animo_descripcion", ""
                        ),
                        "estado_animo_cualidades": request.POST.get(
                            "estado_animo_cualidades", ""
                        ),
                        "estado_animo_expresiones": request.POST.get(
                            "estado_animo_expresiones", ""
                        ),
                        # ========== APETITO ==========
                        "apetito_descripcion": request.POST.get(
                            "apetito_descripcion", ""
                        ),
                        "apetito_cambios": request.POST.get("apetito_cambios", ""),
                        "apetito_edad_inicio": request.POST.get(
                            "apetito_edad_inicio", ""
                        ),
                        "apetito_caracteristicas": request.POST.get(
                            "apetito_caracteristicas", ""
                        ),
                        # ========== FUNCIONALIDAD ==========
                        "funcionalidad_descripcion": request.POST.get(
                            "funcionalidad_descripcion", ""
                        ),
                        "independencia_vida_diaria": request.POST.get(
                            "independencia_vida_diaria", "no"
                        ),
                        "independencia_actividades_complejas": request.POST.get(
                            "independencia_actividades_complejas", "no"
                        ),
                        # ========== CONDUCTA MOTORA ==========
                        "conducta_motora_descripcion": request.POST.get(
                            "conducta_motora_descripcion", ""
                        ),
                        "trastornos_cuantitativos": request.POST.get(
                            "trastornos_cuantitativos", ""
                        ),
                        "trastornos_cualitativos": request.POST.get(
                            "trastornos_cualitativos", ""
                        ),
                    },
                )
            )

            # ==============================
            # Procesar relaciones hijas
            # ==============================

            # Limpiar relaciones existentes
            cognitivo_anamnesis.actitudes.all().delete()
            cognitivo_anamnesis.atenciones.all().delete()
            cognitivo_anamnesis.errores_lenguaje.all().delete()
            cognitivo_anamnesis.actividades_vida_diaria.all().delete()
            cognitivo_anamnesis.actividades_complejas.all().delete()

            # Procesar actitudes
            actitudes_seleccionadas = request.POST.getlist("actitud_tipo[]")
            for actitud in actitudes_seleccionadas:
                if actitud:
                    ActitudCognitiva.objects.create(
                        anamnesis=cognitivo_anamnesis, tipo=actitud
                    )

            # Procesar problemas de atención
            atencion_tipos = request.POST.getlist("atencion_tipo[]")
            atencion_edades = request.POST.getlist("atencion_edad_inicio[]")
            atencion_caracteristicas = request.POST.getlist(
                "atencion_caracteristicas[]"
            )

            for i, tipo in enumerate(atencion_tipos):
                if tipo:
                    AtencionCognitiva.objects.create(
                        anamnesis=cognitivo_anamnesis,
                        tipo=tipo,
                        edad_inicio=atencion_edades[i]
                        if i < len(atencion_edades)
                        else "",
                        caracteristicas=atencion_caracteristicas[i]
                        if i < len(atencion_caracteristicas)
                        else "",
                    )

            # Procesar errores de lenguaje
            errores_lenguaje = request.POST.getlist("error_lenguaje[]")
            for error in errores_lenguaje:
                if error:
                    ErrorLenguajeCognitivo.objects.create(
                        anamnesis=cognitivo_anamnesis, tipo=error
                    )

            # Procesar actividades de vida diaria
            actividades_vida_diaria = request.POST.getlist("actividad_vida_diaria[]")
            for actividad in actividades_vida_diaria:
                if actividad:
                    ActividadVidaDiaria.objects.create(
                        anamnesis=cognitivo_anamnesis, tipo=actividad
                    )

            # Procesar actividades complejas
            actividades_complejas = request.POST.getlist("actividad_compleja[]")
            for actividad in actividades_complejas:
                if actividad:
                    ActividadCompleja.objects.create(
                        anamnesis=cognitivo_anamnesis, tipo=actividad
                    )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Contar elementos guardados
            total_actitudes = cognitivo_anamnesis.actitudes.count()
            total_atencion = cognitivo_anamnesis.atenciones.count()
            total_errores = cognitivo_anamnesis.errores_lenguaje.count()
            total_vida_diaria = cognitivo_anamnesis.actividades_vida_diaria.count()
            total_complejas = cognitivo_anamnesis.actividades_complejas.count()

            messages.success(
                request,
                f"✅ Examen Cognitivo Anamnesis guardado exitosamente.\n"
                f"📋 Actitudes: {total_actitudes}, Atención: {total_atencion}, "
                f"Errores lenguaje: {total_errores}, Actividades: {total_vida_diaria + total_complejas}",
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


# examenes sueno
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
                setattr(anamnesis, campo, request.POST.get(campo, ""))

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

            # Obtener los campos EXACTOS del modelo MoCAResult
            alternancia = int(request.POST.get("alternancia", 0))
            cubo = int(request.POST.get("cubo", 0))
            reloj = int(request.POST.get("reloj", 0))
            denominacion = int(request.POST.get("denominacion", 0))
            atencion = int(request.POST.get("atencion", 0))
            repeticion = int(request.POST.get("repeticion", 0))
            fluidez = int(request.POST.get("fluidez", 0))
            abstraccion = int(request.POST.get("abstraccion", 0))
            diferido = int(request.POST.get("diferido", 0))
            orientacion = int(request.POST.get("orientacion", 0))
            educacion_baja = (
                True if request.POST.get("educacion_baja") == "on" else False
            )

            # Calcular puntaje total
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

            # Determinar interpretación
            if puntaje_total >= 26:
                interpretacion = "Puntaje normal (función cognitiva preservada)"
            else:
                interpretacion = "Posible deterioro cognitivo. Se recomienda evaluación clínica adicional."

            # Crear o actualizar el resultado
            moca, created = MoCAResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "alternancia": alternancia,
                    "cubo": cubo,
                    "reloj": reloj,
                    "denominacion": denominacion,
                    "atencion": atencion,
                    "repeticion": repeticion,
                    "fluidez": fluidez,
                    "abstraccion": abstraccion,
                    "diferido": diferido,
                    "orientacion": orientacion,
                    "educacion_baja": educacion_baja,
                    "puntaje_total": puntaje_total,
                    "interpretacion": interpretacion,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala MoCA guardada exitosamente.\n"
                f"📊 Puntaje: {puntaje_total}/30\n"
                f"🔍 Interpretación: {interpretacion}",
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

            messages.error(request, f"❌ Error al guardar la escala MoCA: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


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


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def estadisticas(request):
    url_query = (
        f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
    )
    headers = {
        "Authorization": f"Bearer {settings.POSTHOG_PERSONAL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # --------- 1. DAU (TrendsQuery) ---------
        query_dau = {
            "kind": "TrendsQuery",
            "series": [
                {
                    "kind": "EventsNode",
                    "event": "$pageview",
                    "name": "$pageview",
                    "math": "dau",
                }
            ],
            "interval": "day",
            "dateRange": {"date_from": "-30d", "explicitDate": False},
        }

        r1 = requests.post(url_query, headers=headers, json={"query": query_dau})
        r1.raise_for_status()
        data_dau = r1.json()

        dau_labels, dau_values = [], []
        results_dau = data_dau.get("results", [])
        if results_dau:
            dau_labels = results_dau[0].get("labels", [])
            dau_values = results_dau[0].get("data", [])

        # --------- 2. Growth Accounting (LifecycleQuery) ---------
        query_growth = {
            "kind": "LifecycleQuery",
            "series": [
                {"event": "$pageview"}
            ],  # puedes cambiar el evento si quieres otro
            "dateRange": {"date_from": "-30d"},
            "interval": "day",
        }

        r2 = requests.post(url_query, headers=headers, json={"query": query_growth})
        r2.raise_for_status()
        data_growth = r2.json()

        growth_labels, growth_datasets = [], []
        results_growth = data_growth.get("results", [])
        if results_growth:
            # Todas las series comparten las mismas fechas
            growth_labels = results_growth[0].get("days", [])
            for serie in results_growth:
                raw_label = serie.get("label", "")
                clean_label = raw_label.split(" - ")[-1].capitalize()

                # Dejamos los datos tal cual, incluso negativos
                data = serie.get("data", [])

                growth_datasets.append(
                    {
                        "label": clean_label,
                        "data": data,
                    }
                )

        # --------- 3. Device Type (Insight) ---------
        device_labels, device_values = [], []

        # 1. Obtener el insight ya configurado
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_DEVICE_TYPE_INSIGHT_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        # 2. Ejecutar la query del insight
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        results = data.get("results") or data.get("result") or []

        device_translation = {
            "Desktop": "Computador",
            "Mobile": "Celular",
            "Tablet": "Tablet",
        }

        if results:
            for serie in results:
                # label / breakdown del dispositivo
                device = (
                    serie.get("breakdown_value")
                    or serie.get("breakdown")
                    or serie.get("label")
                    or "Otro"
                )
                if isinstance(device, list):
                    device = device[0] if device else "Otro"

                # normalizar al español
                device_name = device_translation.get(device, device)

                # sacar valores → PostHog los devuelve en "data", "result" o "count"
                total = None
                if (
                    "aggregated_value" in serie
                    and serie["aggregated_value"] is not None
                ):
                    total = serie["aggregated_value"]
                elif "count" in serie and serie["count"] is not None:
                    total = serie["count"]
                elif "data" in serie:
                    total = sum(serie.get("data", []))
                elif "result" in serie:
                    vals = serie.get("result", [])
                    if isinstance(vals, list):
                        total = sum(v for v in vals if isinstance(v, (int, float)))

                total = int(total or 0)

                device_labels.append(device_name)
                device_values.append(total)

        # --------- 6. Conteo de vistas por página ---------

        views_labels, views_values = [], []

        # 1. Traer el insight
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_VIEWS_PER_PAGE}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        # 2. Ejecutar la query del insight
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        results = []

        if isinstance(data, dict):
            if "results" in data and isinstance(data["results"], list):
                results = data["results"]
            elif "result" in data and isinstance(data["result"], list):
                results = data["result"]
            elif "data" in data and isinstance(data["data"], list):
                results = data["data"]
        elif isinstance(data, list):
            results = data

        if results:
            for idx, serie in enumerate(results):
                # Nombre de la sección
                section = serie.get("order")

                # Total de vistas
                total = None
                if (
                    "aggregated_value" in serie
                    and serie["aggregated_value"] is not None
                ):
                    total = serie["aggregated_value"]

                total = int(total or 0)

                views_labels.append(section)
                views_values.append(total)

        # Construir dataset en formato Chart.js
        views_dataset = [
            {
                "label": views_labels,
                "data": views_values,
            }
        ]

        # 5. Renderizar template
        return render(
            request,
            "home/statistics_recuerdame.html",
            {
                "labels": dau_labels,
                "values": dau_values,
                "growth_labels": growth_labels,
                "growth_datasets": growth_datasets,
                "device_labels": device_labels,
                "device_values": device_values,
                "views_labels": views_labels,
                "views_dataset": views_dataset,
            },
        )

    except requests.exceptions.RequestException as e:
        return HttpResponseServerError(f"Error al obtener datos: {e}")


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def listado_usuarios_recuerdame(request):
    """
    Lista los usuarios (emails) obtenidos desde PostHog.
    """
    url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_IDENTIFY_COUNT_INSIGHT_ID}/"
    headers = {
        "Authorization": f"Bearer {settings.POSTHOG_PERSONAL_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        # Ejecutar query
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        results = data.get("results") or data.get("result") or []
        user_emails = []

        for serie in results:
            email_field = (
                serie.get("breakdown_value")
                or serie.get("breakdown")
                or serie.get("label")
                or "Sin email"
            )
            if isinstance(email_field, list):
                email = email_field[0] if email_field else "Sin email"
            else:
                email = email_field

            if isinstance(email, str) and "@" in email:
                user_emails.append(email)

        return render(
            request,
            "home/users_recuerdame.html",
            {"user_emails": sorted(user_emails)},
        )
    except requests.exceptions.RequestException as e:
        return HttpResponseServerError(f"Error al obtener datos: {e}")


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def estadisticas_usuario_detalle(request, email):
    """
    Muestra las métricas de PostHog para un usuario específico (email).
    """
    url_query = (
        f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
    )
    headers = {
        "Authorization": f"Bearer {settings.POSTHOG_PERSONAL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # --------- 4. Ingresos por usuario (Login) ---------
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_IDENTIFY_COUNT_INSIGHT_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        # Ejecutar query
        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        user_labels, user_values = [], []

        results = data.get("results") or data.get("result") or []
        if results:
            for serie in results:
                # Identificar el email
                email_field = (
                    serie.get("breakdown_value")
                    or serie.get("breakdown")
                    or serie.get("label")
                    or "Sin email"
                )
                if isinstance(email_field, list):
                    email_value = email_field[0] if email_field else "Sin email"
                else:
                    email_value = email_field

                # Filtrar SOLO el email solicitado
                if str(email_value).lower() != str(email).lower():
                    continue

                total_sum = serie.get("aggregated_value") or serie.get("count") or 0
                try:
                    total_sum = int(total_sum)
                except Exception:
                    total_sum = 0

                user_labels.append(email_value)
                user_values.append(total_sum)

        # --------- 5. Sesiones (Pageview -> Pageleave) ---------
        session_rows = []
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_SESION_TIME_INSIGHT_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        results = data.get("steps") or data.get("results") or data.get("result") or []
        if results:
            for serie in results:
                last = serie[-1] if isinstance(serie, list) else serie
                first = serie[0] if isinstance(serie, list) else serie

                email_field = (
                    last.get("breakdown_value")
                    or last.get("breakdown")
                    or last.get("label")
                    or "Sin dato"
                )
                if isinstance(email_field, list):
                    email_value = email_field[0] if email_field else "Sin dato"
                else:
                    email_value = email_field

                if str(email_value).lower() != str(email).lower():
                    continue

                entered = int(first.get("count") or 0)
                converted = int(last.get("count") or 0)
                dropped = max(entered - converted, 0)

                def format_seconds(seconds):
                    if not seconds:
                        return "–"
                    minutes, sec = divmod(int(seconds), 60)
                    hours, minutes = divmod(minutes, 60)
                    if hours:
                        return f"{hours}h {minutes}m {sec}s"
                    elif minutes:
                        return f"{minutes}m {sec}s"
                    else:
                        return f"{sec}s"

                session_rows.append(
                    {
                        "email": email_value,
                        "entered": entered,
                        "converted": converted,
                        "dropped_off": dropped,
                        "conversion_rate": round((converted / entered) * 100, 2)
                        if entered > 0
                        else 0,
                        # "avg_time": last.get("average_conversion_time"),
                        # "median_time": last.get("median_conversion_time"),
                        "avg_time": format_seconds(last.get("average_conversion_time")),
                        "median_time": format_seconds(
                            last.get("median_conversion_time")
                        ),
                    }
                )

        # --------- 7. Vistas por página con breakdown por email ---------
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_PAGES_VIEWS_PER_USER}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        results = data.get("results") or data.get("result") or []
        user_page_views = {}

        if results:
            for serie in results:
                email_field = (
                    serie.get("breakdown_value")
                    or serie.get("breakdown")
                    or serie.get("label")
                    or "Sin email"
                )
                if isinstance(email_field, list):
                    email_value = email_field[0] if email_field else "Sin email"
                else:
                    email_value = email_field

                if str(email_value).lower() != str(email).lower():
                    continue

                page = serie.get("order") or 0
                try:
                    page = int(page)
                except Exception:
                    pass

                total = int(serie.get("aggregated_value") or 0)
                if email_value not in user_page_views:
                    user_page_views[email_value] = {}
                user_page_views[email_value][page] = total

        # Mapear páginas
        label_map = {
            0: "Sección: Información en Salud",
            1: "Sección: Pasatiempos",
            2: "Sección: Encuentros",
            3: "Sección: Fortalece tu mente",
            4: "Sección: Hazlo consciente",
            5: "Hazlo Consciente - Módulo 2",
            6: "Hazlo Consciente - Módulo 3",
            7: "Hazlo Consciente - Módulo 4",
            8: "Pasatiempos - Plantas",
            9: "Pasatiempos - Mascotas",
            10: "Pasatiempos - Recetas",
            11: "Pasatiempos - Ejercicio",
            12: "Polijuego",
        }

        all_pages = list(range(0, 13))
        user_views_labels = [label_map[p] for p in all_pages]

        views_matrix = []
        row = {"email": email}
        for page in all_pages:
            row[label_map[page]] = user_page_views.get(email, {}).get(page, 0)
        views_matrix.append(row)

        # --------- DAU por usuario (Insight con breakdown) ---------
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_DAU_PER_USER_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        dau_user_labels, dau_user_values = [], []

        results = data.get("results") or data.get("result") or []
        if results:
            for serie in results:
                email_field = (
                    serie.get("breakdown_value")
                    or serie.get("breakdown")
                    or serie.get("label")
                    or "Sin email"
                )
                if isinstance(email_field, list):
                    email_value = email_field[0] if email_field else "Sin email"
                else:
                    email_value = email_field

                # 👇 Filtramos SOLO el email solicitado
                if str(email_value).lower() != str(email).lower():
                    continue

                dau_user_labels = serie.get("labels", [])
                dau_user_values = serie.get("data", [])
                break

        # --------- Autocapture por usuario ---------
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_AUTOCAPTURE_PER_USER_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        autocapture_rows = []

        results = data.get("results") or data.get("result") or []
        if results:
            for serie in results:
                email_field = (
                    serie.get("breakdown_value")
                    or serie.get("breakdown")
                    or serie.get("label")
                    or "Sin email"
                )
                if isinstance(email_field, list):
                    email_value = email_field[0] if email_field else "Sin email"
                else:
                    email_value = email_field

                # 👇 Filtramos SOLO el email solicitado
                if str(email_value).lower() != str(email).lower():
                    continue

                count = int(serie.get("aggregated_value") or serie.get("count") or 0)

                autocapture_rows.append(
                    {
                        "email": email_value,
                        "count": count,
                    }
                )

        if session_rows:
            campos = {
                "email": email,
                "ingresos": user_values[0] if user_values else 0,
                "sesiones_ingresadas": session_rows[0]["entered"],
                "sesiones_convertidas": session_rows[0]["converted"],
                "sesiones_abandonadas": session_rows[0]["dropped_off"],
                "conversion_rate": session_rows[0]["conversion_rate"],
                "tiempo_promedio": session_rows[0]["avg_time"],
                "tiempo_mediano": session_rows[0]["median_time"],
                "total_clicks": autocapture_rows[0]["count"] if autocapture_rows else 0,
            }

            EstadisticasUsuarioResult.objects.update_or_create(
                email=email,
                defaults=campos,
            )

        # Render
        return render(
            request,
            "home/statistics_per_user_recuerdame.html",
            {
                "email": email,
                "user_labels": user_labels,
                "user_values": user_values,
                "session_rows": session_rows,
                "views_labels_breakdown": user_views_labels,
                "views_matrix": views_matrix,
                "dau_user_labels": dau_user_labels,
                "dau_user_values": dau_user_values,
                "autocapture_rows": autocapture_rows,
            },
        )

    except requests.exceptions.RequestException as e:
        return HttpResponseServerError(f"Error al obtener datos: {e}")


#######################################################################################


@login_required
def guardar_examen_analisis(request):
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

            # Obtener datos principales
            analisis_historia = request.POST.get("analisis_historia", "")
            plan_tratamiento = request.POST.get("plan_tratamiento", "")

            # Crear o actualizar resultado principal
            analisis_result, created = AnalisisGeneralResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "analisis_historia": analisis_historia,
                    "plan_tratamiento": plan_tratamiento,
                },
            )

            # Limpiar diagnósticos existentes
            analisis_result.diagnosticos_cie10.all().delete()
            analisis_result.diagnosticos_dsmv.all().delete()
            analisis_result.diagnosticos_icsd3.all().delete()
            analisis_result.diagnosticos_no_clasificados.all().delete()

            # Procesar diagnósticos CIE-10
            cie10_codigos = request.POST.getlist("cie10_codigo[]")
            cie10_diagnosticos = request.POST.getlist("cie10_diagnostico[]")
            cie10_estados = request.POST.getlist("cie10_estado[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(cie10_codigos, cie10_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    # Crear el diagnóstico
                    diag_cie10 = DiagnosticoCIE10.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    # Marcar estados correspondientes basados en los checkboxes
                    if "confirmado_nuevo" in cie10_estados:
                        diag_cie10.confirmado_nuevo = True
                    if "confirmado_antiguo" in cie10_estados:
                        diag_cie10.confirmado_antiguo = True
                    if "en_estudio" in cie10_estados:
                        diag_cie10.en_estudio = True

                    diag_cie10.save()

            # Procesar diagnósticos DSM-V (similar estructura)
            dsmv_codigos = request.POST.getlist("dsmv_codigo[]")
            dsmv_diagnosticos = request.POST.getlist("dsmv_diagnostico[]")
            dsmv_estados = request.POST.getlist("dsmv_estado[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(dsmv_codigos, dsmv_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    diag_dsmv = DiagnosticoDSMV.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if "confirmado_nuevo" in dsmv_estados:
                        diag_dsmv.confirmado_nuevo = True
                    if "confirmado_antiguo" in dsmv_estados:
                        diag_dsmv.confirmado_antiguo = True
                    if "en_estudio" in dsmv_estados:
                        diag_dsmv.en_estudio = True

                    diag_dsmv.save()

            # Procesar diagnósticos ICSD-3 (similar estructura)
            icsd3_codigos = request.POST.getlist("icsd3_codigo[]")
            icsd3_diagnosticos = request.POST.getlist("icsd3_diagnostico[]")
            icsd3_estados = request.POST.getlist("icsd3_estado[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(icsd3_codigos, icsd3_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    diag_icsd3 = DiagnosticoICSD3.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if "confirmado_nuevo" in icsd3_estados:
                        diag_icsd3.confirmado_nuevo = True
                    if "confirmado_antiguo" in icsd3_estados:
                        diag_icsd3.confirmado_antiguo = True
                    if "en_estudio" in icsd3_estados:
                        diag_icsd3.en_estudio = True

                    diag_icsd3.save()

            # Procesar diagnósticos no clasificados
            noclasi_diagnosticos = request.POST.getlist("noclasi_diagnostico[]")
            noclasi_estados = request.POST.getlist("noclasi_estado[]")

            for i, diagnostico in enumerate(noclasi_diagnosticos):
                if diagnostico.strip():
                    diag_noclasi = DiagnosticoNoClasificado.objects.create(
                        analisis_result=analisis_result,
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if "confirmado_nuevo" in noclasi_estados:
                        diag_noclasi.confirmado_nuevo = True
                    if "confirmado_antiguo" in noclasi_estados:
                        diag_noclasi.confirmado_antiguo = True
                    if "en_estudio" in noclasi_estados:
                        diag_noclasi.en_estudio = True

                    diag_noclasi.save()

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Contar diagnósticos guardados
            total_diagnosticos = (
                analisis_result.diagnosticos_cie10.count()
                + analisis_result.diagnosticos_dsmv.count()
                + analisis_result.diagnosticos_icsd3.count()
                + analisis_result.diagnosticos_no_clasificados.count()
            )

            messages.success(
                request,
                f"✅ Análisis y diagnósticos guardados exitosamente.\n"
                f"📋 Total de diagnósticos: {total_diagnosticos}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"❌ Error al guardar el análisis: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_antecedentes(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Obtener el paciente
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # NUEVO: Obtener o crear antecedentes únicos por paciente
            antecedentes_result, created = AntecedentesResult.get_or_create_for_patient(
                paciente=paciente, visita_examen=visita_examen, usuario=request.user
            )

            # Actualizar observaciones generales
            antecedentes_result.observaciones_generales = request.POST.get(
                "observaciones_generales", ""
            )

            # Crear o actualizar el link de la visita
            visita_link, link_created = AntecedentesVisitaLink.objects.get_or_create(
                visita_examen=visita_examen,
                defaults={"antecedentes_result": antecedentes_result},
            )
            visita_link.fue_revisado = True
            visita_link.fue_actualizado = True
            visita_link.revisado_por = request.user.username
            visita_link.save()

            # Variable para controlar si hay algún antecedente
            tiene_antecedentes = False
            antecedentes_guardados = []

            # ===== PROCESAR ANTECEDENTES DINÁMICOS =====
            # Obtener datos de antecedentes dinámicos (desde JavaScript)
            patologicos_data = request.POST.get("patologicos_data")
            quirurgicos_data = request.POST.get("quirurgicos_data")
            farmacologicos_data = request.POST.get("farmacologicos_data")
            toxicos_data = request.POST.get("toxicos_data")
            familiares_data = request.POST.get("familiares_data")
            alergicos_data = request.POST.get("alergicos_data")
            traumaticos_data = request.POST.get("traumaticos_data")
            gineco_data = request.POST.get("gineco_data")
            epidemiologicos_data = request.POST.get("epidemiologicos_data")
            ets_data = request.POST.get("ets_data")
            hospitalizaciones_data = request.POST.get("hospitalizaciones_data")
            inmunizaciones_data = request.POST.get("inmunizaciones_data")
            transfusionales_data = request.POST.get("transfusionales_data")

            # ===== PROCESAR PATOLÓGICOS =====
            if patologicos_data:
                patologicos_list = json.loads(patologicos_data)
                # Limpiar existentes
                antecedentes_result.antecedentes_patologicos.all().delete()

                for item in patologicos_list:
                    if item.get("tipo_patologia"):
                        tiene_antecedentes = True
                        AntecedentePatologico.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_patologia=item.get("tipo_patologia", "otros"),
                            descripcion_otros=item.get("descripcion_otros")
                            if item.get("tipo_patologia") == "otros"
                            else None,
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            ha_recibido_tratamiento=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tiene_complicaciones=item.get(
                                "tiene_complicaciones", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if patologicos_list:
                    antecedentes_guardados.append("Patológicos")

            # ===== PROCESAR QUIRÚRGICOS =====
            if quirurgicos_data:
                quirurgicos_list = json.loads(quirurgicos_data)
                antecedentes_result.antecedentes_quirurgicos.all().delete()
                for item in quirurgicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteQuirurgico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_intervencion=datetime.strptime(
                                item.get("fecha_intervencion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_intervencion")
                            else None,
                            ha_recibido_tratamiento=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tiene_complicaciones=item.get(
                                "tiene_complicaciones", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if quirurgicos_list:
                    antecedentes_guardados.append("Quirúrgicos")

            # ===== PROCESAR FARMACOLÓGICOS =====
            if farmacologicos_data:
                farmacologicos_list = json.loads(farmacologicos_data)
                antecedentes_result.antecedentes_farmacologicos.all().delete()

                for item in farmacologicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteFarmacologico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            recibio_tratamiento=item.get("recibio_tratamiento", False),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tuvo_complicaciones=item.get("tuvo_complicaciones", False),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if farmacologicos_list:
                    antecedentes_guardados.append("Farmacológicos")

            # ===== PROCESAR TÓXICOS =====
            if toxicos_data:
                toxicos_list = json.loads(toxicos_data)
                antecedentes_result.antecedentes_toxicos.all().delete()

                for item in toxicos_list:
                    if item.get("tipos_toxico"):
                        tiene_antecedentes = True
                        AntecedenteToxico.objects.create(
                            antecedente_result=antecedentes_result,
                            tipos_toxico=item.get("tipos_toxico", []),
                            descripcion_otros=item.get("descripcion_otros", ""),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            ha_recibido_tratamiento=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tiene_complicaciones=item.get(
                                "tiene_complicaciones", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if toxicos_list:
                    antecedentes_guardados.append("Tóxicos")

            # ===== PROCESAR FAMILIARES =====
            if familiares_data:
                familiares_list = json.loads(familiares_data)
                antecedentes_result.antecedentes_familiares.all().delete()

                for item in familiares_list:
                    if item.get("tipo_antecedente") and item.get("parentesco"):
                        tiene_antecedentes = True
                        AntecedenteFamiliar.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_antecedente=item.get("tipo_antecedente"),
                            parentesco=item.get("parentesco"),
                            observaciones=item.get("observaciones", ""),
                        )
                if familiares_list:
                    antecedentes_guardados.append("Familiares")

            # ===== PROCESAR ALÉRGICOS =====
            if alergicos_data:
                alergicos_list = json.loads(alergicos_data)
                antecedentes_result.antecedentes_alergicos.all().delete()

                for item in alergicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteAlergico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_recibido=item.get("tratamiento_recibido", ""),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            complicaciones=item.get("complicaciones", ""),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if alergicos_list:
                    antecedentes_guardados.append("Alérgicos")

            # ===== PROCESAR TRAUMÁTICOS =====
            if traumaticos_data:
                traumaticos_list = json.loads(traumaticos_data)
                antecedentes_result.antecedentes_traumaticos.all().delete()

                for item in traumaticos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteTraumatico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_recibido=item.get("tratamiento_recibido", ""),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            complicaciones=item.get("complicaciones", ""),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if traumaticos_list:
                    antecedentes_guardados.append("Traumáticos")

            # ===== PROCESAR GINECO-OBSTÉTRICOS =====
            if gineco_data:
                gineco_dict = json.loads(gineco_data)
                # Eliminar existente (OneToOne)
                if hasattr(antecedentes_result, "antecedentes_gineco"):
                    antecedentes_result.antecedentes_gineco.delete()

                if gineco_dict:
                    tiene_antecedentes = True
                    AntecedenteGinecoObstetrico.objects.create(
                        antecedente_result=antecedentes_result,
                        tiene_menarquia=gineco_dict.get("tiene_menarquia", False),
                        edad_menarquia=gineco_dict.get("edad_menarquia"),
                        tiene_menopausia=gineco_dict.get("tiene_menopausia", False),
                        edad_menopausia=gineco_dict.get("edad_menopausia"),
                        gravidez=gineco_dict.get("gravidez", 0),
                        abortos=gineco_dict.get("abortos", 0),
                        hijos_vivos=gineco_dict.get("hijos_vivos", 0),
                        usa_metodo_planificacion=gineco_dict.get(
                            "usa_metodo_planificacion", False
                        ),
                        metodo_detalle=gineco_dict.get("metodo_detalle", ""),
                        dosis_planificacion=gineco_dict.get("dosis_planificacion", ""),
                        adherencia_planificacion=gineco_dict.get(
                            "adherencia_planificacion", ""
                        ),
                        tolerancia_planificacion=gineco_dict.get(
                            "tolerancia_planificacion", ""
                        ),
                        observaciones=gineco_dict.get("observaciones", ""),
                    )
                    antecedentes_guardados.append("Gineco-Obstétricos")

            # ===== PROCESAR EPIDEMIOLÓGICOS (NUEVO) =====
            if epidemiologicos_data:
                epidemiologicos_list = json.loads(epidemiologicos_data)
                antecedentes_result.antecedentes_epidemiologicos.all().delete()

                for item in epidemiologicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteEpidemiologico.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_antecedente=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_detalle=item.get("tratamiento_detalle", ""),
                            complicaciones_asociadas=item.get(
                                "complicaciones_asociadas", False
                            ),
                            detallar_complicaciones=item.get(
                                "detallar_complicaciones", ""
                            ),
                            activo_actualmente=item.get("activo_actualmente", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if epidemiologicos_list:
                    antecedentes_guardados.append("Epidemiológicos")

            # ===== PROCESAR ETS (NUEVO) =====
            if ets_data:
                ets_list = json.loads(ets_data)
                antecedentes_result.antecedentes_ets.all().delete()

                for item in ets_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteETS.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_ets=item.get("descripcion"),
                            fecha_diagnostico=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_recibido=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("tratamiento_detalle", ""),
                            complicaciones=item.get("complicaciones_asociadas", False),
                            detalle_complicaciones=item.get(
                                "detallar_complicaciones", ""
                            ),
                            curado=not item.get("activo_actualmente", True),
                            fecha_curacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if ets_list:
                    antecedentes_guardados.append("ETS")

            # ===== PROCESAR HOSPITALIZACIONES (NUEVO) =====
            # ...existing code...
            if hospitalizaciones_data:
                hospitalizaciones_list = json.loads(hospitalizaciones_data)
                antecedentes_result.antecedentes_hospitalizaciones.all().delete()

                for item in hospitalizaciones_list:
                    if item.get(
                        "motivo_hospitalizacion"
                    ):  # Cambio: usar el nombre correcto del campo
                        tiene_antecedentes = True

                        # Manejar fecha_egreso de forma segura
                        fecha_egreso = None
                        if item.get("fecha_egreso"):
                            try:
                                fecha_egreso = datetime.strptime(
                                    item.get("fecha_egreso"), "%Y-%m-%d"
                                ).date()
                            except (ValueError, TypeError):
                                fecha_egreso = None

                        # Manejar fecha_ingreso de forma segura
                        fecha_ingreso = None
                        if item.get("fecha_ingreso"):
                            try:
                                fecha_ingreso = datetime.strptime(
                                    item.get("fecha_ingreso"), "%Y-%m-%d"
                                ).date()
                            except (ValueError, TypeError):
                                fecha_ingreso = None

                        # Convertir días_hospitalizacion a entero de forma segura
                        dias_hospitalizacion = None
                        if item.get("dias_hospitalizacion"):
                            try:
                                dias_hospitalizacion = int(
                                    item.get("dias_hospitalizacion")
                                )
                            except (ValueError, TypeError):
                                dias_hospitalizacion = None

                        AntecedenteHospitalizacion.objects.create(
                            antecedente_result=antecedentes_result,
                            motivo_hospitalizacion=item.get("motivo_hospitalizacion"),
                            fecha_ingreso=fecha_ingreso,
                            fecha_egreso=fecha_egreso,
                            institucion=item.get("institucion", ""),
                            dias_hospitalizacion=dias_hospitalizacion,
                            complicaciones_durante=item.get(
                                "complicaciones_durante", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            secuelas=item.get("secuelas", False),
                            detalle_secuelas=item.get("detalle_secuelas", ""),
                            observaciones=item.get("observaciones", ""),
                        )
                if hospitalizaciones_list:
                    antecedentes_guardados.append("Hospitalizaciones")
            # ===== PROCESAR INMUNIZACIONES (NUEVO) =====
            if inmunizaciones_data:
                inmunizaciones_list = json.loads(inmunizaciones_data)
                antecedentes_result.antecedentes_inmunizaciones.all().delete()

                for item in inmunizaciones_list:
                    if item.get("vacuna_inmunizacion"):
                        tiene_antecedentes = True
                        AntecedenteInmunizacion.objects.create(
                            antecedente_result=antecedentes_result,
                            nombre_vacuna=item.get("vacuna_inmunizacion"),
                            fecha_aplicacion=datetime.strptime(
                                item.get("fecha_ultima_dosis"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_ultima_dosis")
                            else None,
                            dosis_numero=item.get("numero_dosis", 1),
                            observaciones=item.get("observaciones", ""),
                        )
                if inmunizaciones_list:
                    antecedentes_guardados.append("Inmunizaciones")

            # ===== PROCESAR TRANSFUSIONALES (NUEVO) =====
            if transfusionales_data:
                transfusionales_list = json.loads(transfusionales_data)
                antecedentes_result.antecedentes_transfusionales.all().delete()

                for item in transfusionales_list:
                    if item.get("motivo_transfusion"):
                        tiene_antecedentes = True
                        AntecedenteTransfusional.objects.create(
                            antecedente_result=antecedentes_result,
                            motivo_transfusion=item.get("motivo_transfusion"),
                            fecha_transfusion=datetime.strptime(
                                item.get("fecha_ultima_transfusion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_ultima_transfusion")
                            else None,
                            tipo_componente=item.get("tipo_componente", "sangre_total"),
                            cantidad_unidades=item.get("numero_unidades", 1),
                            tuvo_reacciones=item.get("tuvo_reacciones", False),
                            detalle_reacciones=item.get("detalle_reacciones", ""),
                            observaciones=item.get("observaciones", ""),
                        )
                if transfusionales_list:
                    antecedentes_guardados.append("Transfusionales")

            # Actualizar el campo principal
            antecedentes_result.tiene_antecedentes = tiene_antecedentes
            antecedentes_result.save()

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Mensaje de éxito personalizado
            if antecedentes_guardados:
                tipos_guardados = ", ".join(antecedentes_guardados)
                messages.success(
                    request,
                    f"✅ Antecedentes médicos guardados exitosamente.\n"
                    f"📋 Tipos registrados: {tipos_guardados}",
                )
            else:
                messages.success(
                    request,
                    "✅ Antecedentes médicos guardados exitosamente.\n"
                    "📋 Sin antecedentes registrados.",
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
                request, f"❌ Error al guardar los antecedentes médicos: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_medicamentos(request):
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

            # 🔧 CORRECCIÓN: Obtener o crear MedicamentosResult de forma correcta
            try:
                medicamentos_result = MedicamentosResult.objects.get(
                    visita_examen=visita_examen
                )
            except MedicamentosResult.DoesNotExist:
                medicamentos_result = MedicamentosResult.objects.create(
                    visita_examen=visita_examen
                )

            # Actualizar observaciones generales
            observaciones_generales = request.POST.get("observaciones_generales", "")
            medicamentos_result.observaciones_generales = observaciones_generales
            medicamentos_result.save()

            # Obtener arrays de datos de medicamentos
            nombres_comerciales = request.POST.getlist("nombre_comercial[]")
            nombres_genericos = request.POST.getlist("nombre_generico[]")
            presentaciones = request.POST.getlist("presentacion[]")
            concentraciones = request.POST.getlist("concentracion[]")
            unidades = request.POST.getlist("unidad[]")
            vias_administracion = request.POST.getlist("via_administracion[]")
            cantidades = request.POST.getlist("cantidad[]")
            frecuencias = request.POST.getlist("frecuencia[]")
            fechas_inicio = request.POST.getlist("fecha_inicio[]")
            fechas_finalizacion = request.POST.getlist("fecha_finalizacion[]")
            indicaciones = request.POST.getlist("indicacion[]")

            # Campos adicionales
            adherencias = request.POST.getlist("adherencia[]")
            efectos_adversos = request.POST.getlist("efectos_adversos[]")
            descripciones_efectos = request.POST.getlist(
                "descripcion_efectos_adversos[]"
            )
            observaciones_medicamentos = request.POST.getlist("observaciones[]")

            # 🔧 CORRECCIÓN: Eliminar medicamentos existentes antes de crear nuevos
            medicamentos_existentes = medicamentos_result.medicamentos.all()
            count_eliminados = medicamentos_existentes.count()
            medicamentos_existentes.delete()

            medicamentos_guardados = 0

            # Procesar cada medicamento
            for i in range(len(nombres_comerciales)):
                nombre_comercial = (
                    nombres_comerciales[i].strip()
                    if i < len(nombres_comerciales)
                    else ""
                )

                # Validar que al menos el nombre comercial esté presente
                if nombre_comercial:
                    # Manejar fechas de forma segura
                    fecha_inicio = None
                    if i < len(fechas_inicio) and fechas_inicio[i]:
                        try:
                            fecha_inicio = datetime.strptime(
                                fechas_inicio[i], "%Y-%m-%d"
                            ).date()
                        except (ValueError, TypeError) as e:
                            fecha_inicio = None

                    fecha_finalizacion = None
                    if i < len(fechas_finalizacion) and fechas_finalizacion[i]:
                        try:
                            fecha_finalizacion = datetime.strptime(
                                fechas_finalizacion[i], "%Y-%m-%d"
                            ).date()
                        except (ValueError, TypeError) as e:
                            fecha_finalizacion = None

                    # Manejar efectos adversos
                    tiene_efectos_adversos = False
                    if i < len(efectos_adversos):
                        tiene_efectos_adversos = efectos_adversos[i] == "true"

                    # 🔧 CORRECCIÓN: Verificar que el campo 'presentacion' es obligatorio
                    presentacion = (
                        presentaciones[i]
                        if i < len(presentaciones) and presentaciones[i]
                        else "tableta"
                    )
                    concentracion = (
                        concentraciones[i]
                        if i < len(concentraciones) and concentraciones[i]
                        else "No especificada"
                    )
                    unidad = (
                        unidades[i]
                        if i < len(unidades) and unidades[i]
                        else "miligramos"
                    )
                    via_administracion = (
                        vias_administracion[i]
                        if i < len(vias_administracion) and vias_administracion[i]
                        else "oral"
                    )
                    cantidad = (
                        cantidades[i] if i < len(cantidades) and cantidades[i] else "1"
                    )
                    frecuencia = (
                        frecuencias[i]
                        if i < len(frecuencias) and frecuencias[i]
                        else "No especificada"
                    )
                    indicacion = (
                        indicaciones[i]
                        if i < len(indicaciones) and indicaciones[i]
                        else "No especificada"
                    )

                    # Crear el medicamento
                    try:
                        medicamento = Medicamento.objects.create(
                            medicamentos_result=medicamentos_result,
                            nombre_comercial=nombre_comercial,
                            nombre_generico=nombres_genericos[i].strip()
                            if i < len(nombres_genericos)
                            else "",
                            presentacion=presentacion,
                            concentracion=concentracion,
                            unidad=unidad,
                            via_administracion=via_administracion,
                            cantidad=cantidad,
                            frecuencia=frecuencia,
                            fecha_inicio=fecha_inicio,
                            fecha_finalizacion=fecha_finalizacion,
                            indicacion=indicacion,
                            adherencia=adherencias[i]
                            if i < len(adherencias)
                            else "no_evaluada",
                            efectos_adversos=tiene_efectos_adversos,
                            descripcion_efectos_adversos=descripciones_efectos[i]
                            if i < len(descripciones_efectos)
                            else "",
                            observaciones=observaciones_medicamentos[i]
                            if i < len(observaciones_medicamentos)
                            else "",
                            activo=True,  # Por defecto activo
                        )
                        medicamentos_guardados += 1

                    except Exception as e:
                        # Continuar con el siguiente medicamento
                        continue
                else:
                    print(f"⚠️ Medicamento {i + 1} omitido - sin nombre comercial")

            # Marcar el examen como completado solo si se guardó al menos un medicamento
            if medicamentos_guardados > 0:
                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(
                    request,
                    f"✅ Se guardaron {medicamentos_guardados} medicamento(s) correctamente.",
                )
            else:
                # Revertir el estado si no se guardó nada
                visita_examen.estado = "pendiente"
                visita_examen.save()
                messages.warning(request, "⚠️ No se guardó ningún medicamento válido.")

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar los medicamentos: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_fisico(request):
    """
    Vista para guardar el examen físico general basada en el template
    General_ExamenFísico.html y siguiendo el patrón del examen de sueño
    """
    if request.method == "POST":
        try:
            # Obtener IDs del formulario
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Validar datos requeridos
            if not visita_id or not paciente_id or not examen_id:
                raise ValueError("Faltan datos requeridos")

            # Convertir a enteros
            visita_id = int(visita_id)
            paciente_id = int(paciente_id)
            examen_id = int(examen_id)

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Crear o actualizar el resultado del examen físico
            examen_fisico, created = ExamenFisicoResult.objects.get_or_create(
                visita_examen=visita_examen,
                defaults={
                    # === SIGNOS VITALES ===
                    "talla": safe_float_required(request.POST.get("talla"), 0.0),
                    "peso": safe_float_required(request.POST.get("peso"), 0.0),
                    "temperatura": safe_float_required(
                        request.POST.get("temperatura"), 36.5
                    ),
                    "frecuencia_cardiaca": safe_int_required(
                        request.POST.get("frecuencia_cardiaca"), 70
                    ),
                    "frecuencia_respiratoria": safe_int_required(
                        request.POST.get("frecuencia_respiratoria"), 16
                    ),
                    "presion_arterial_sistolica": safe_int_required(
                        request.POST.get("presion_arterial_sistolica"), 120
                    ),
                    "presion_arterial_diastolica": safe_int_required(
                        request.POST.get("presion_arterial_diastolica"), 80
                    ),
                    "perimetro_cefalico": safe_float_optional(
                        request.POST.get("perimetro_cefalico")
                    ),
                    # === CABEZA Y CUELLO ===
                    "cuero_cabelludo_normal": "normal"
                    in request.POST.getlist("cuero_cabelludo"),
                    "cuero_cabelludo_anormal": "anormal"
                    in request.POST.getlist("cuero_cabelludo"),
                    "observaciones_cuero_cabelludo": request.POST.get(
                        "observaciones_cuero_cabelludo", ""
                    ),
                    "oidos_normal": "normal" in request.POST.getlist("oidos"),
                    "oidos_anormal": "anormal" in request.POST.getlist("oidos"),
                    "observaciones_oidos": request.POST.get("observaciones_oidos", ""),
                    "nariz_normal": "normal" in request.POST.getlist("nariz"),
                    "nariz_anormal": "anormal" in request.POST.getlist("nariz"),
                    "observaciones_nariz": request.POST.get("observaciones_nariz", ""),
                    "cuello_normal": "normal" in request.POST.getlist("cuello"),
                    "cuello_anormal": "anormal" in request.POST.getlist("cuello"),
                    "observaciones_cuello": request.POST.get(
                        "observaciones_cuello", ""
                    ),
                    "otros_hallazgos_importantes": request.POST.get(
                        "otros_hallazgos_importantes", ""
                    ),
                    # === TÓRAX / CARDIORESPIRATORIO ===
                    "forma_torax": request.POST.get("forma_torax", "normal"),
                    "observaciones_forma_torax": request.POST.get(
                        "observaciones_forma_torax", ""
                    ),
                    "murmullo_vesicular": request.POST.get(
                        "murmullo_vesicular", "conservado"
                    ),
                    "observaciones_murmullo_vesicular": request.POST.get(
                        "observaciones_murmullo_vesicular", ""
                    ),
                    "ruidos_sobreagregados": bool(
                        request.POST.get("ruidos_sobreagregados")
                    ),
                    "observaciones_ruidos_sobreagregados": request.POST.get(
                        "observaciones_ruidos_sobreagregados", ""
                    ),
                    "ruidos_cardiacos": request.POST.get(
                        "ruidos_cardiacos", "ritmicos"
                    ),
                    "observaciones_ruidos_cardiacos": request.POST.get(
                        "observaciones_ruidos_cardiacos", ""
                    ),
                    # === ABDOMEN ===
                    "peristaltismo": request.POST.get("peristaltismo", "presente"),
                    "pared_abdominal_normal": "normal"
                    in request.POST.getlist("pared_abdominal"),
                    "pared_abdominal_anormal": "anormal"
                    in request.POST.getlist("pared_abdominal"),
                    "masas": bool(request.POST.get("masas")),
                    "megalias": bool(request.POST.get("megalias")),
                    "observaciones_abdomen": request.POST.get(
                        "observaciones_abdomen", ""
                    ),
                    # === OSTEOMUSCULAR ===
                    "curvatura_cervical_normal": "normal"
                    in request.POST.getlist("curvatura_cervical"),
                    "curvatura_cervical_anormal": "anormal"
                    in request.POST.getlist("curvatura_cervical"),
                    "curvatura_toracica_normal": "normal"
                    in request.POST.getlist("curvatura_toracica"),
                    "curvatura_toracica_anormal": "anormal"
                    in request.POST.getlist("curvatura_toracica"),
                    "curvatura_lumbar_normal": "normal"
                    in request.POST.getlist("curvatura_lumbar"),
                    "curvatura_lumbar_anormal": "anormal"
                    in request.POST.getlist("curvatura_lumbar"),
                    "arcos_movimiento_superiores_normal": "normal"
                    in request.POST.getlist("arcos_movimiento_superiores"),
                    "arcos_movimiento_superiores_anormal": "anormal"
                    in request.POST.getlist("arcos_movimiento_superiores"),
                    "arcos_movimiento_inferiores_normal": "normal"
                    in request.POST.getlist("arcos_movimiento_inferiores"),
                    "arcos_movimiento_inferiores_anormal": "anormal"
                    in request.POST.getlist("arcos_movimiento_inferiores"),
                    "asimetrias_inferiores_normal": "normal"
                    in request.POST.getlist("asimetrias_inferiores"),
                    "asimetrias_inferiores_anormal": "anormal"
                    in request.POST.getlist("asimetrias_inferiores"),
                    "asimetrias_superiores_normal": "normal"
                    in request.POST.getlist("asimetrias_superiores"),
                    "asimetrias_superiores_anormal": "anormal"
                    in request.POST.getlist("asimetrias_superiores"),
                    "observaciones_osteomuscular": request.POST.get(
                        "observaciones_osteomuscular", ""
                    ),
                    # === PIEL Y ANEXOS ===
                    "maculas": bool(request.POST.get("maculas")),
                    "papulas": bool(request.POST.get("papulas")),
                    "vesiculas": bool(request.POST.get("vesiculas")),
                    "pustulas": bool(request.POST.get("pustulas")),
                    "fisuras": bool(request.POST.get("fisuras")),
                    "escaras": bool(request.POST.get("escaras")),
                    "petequias": bool(request.POST.get("petequias")),
                    "equimosis": bool(request.POST.get("equimosis")),
                    "ulceras": bool(request.POST.get("ulceras")),
                    "observaciones_piel_anexos": request.POST.get(
                        "observaciones_piel_anexos", ""
                    ),
                },
            )

            # Si no es nuevo, actualizar los campos
            if not created:
                # === SIGNOS VITALES ===
                examen_fisico.talla = safe_float_required(
                    request.POST.get("talla"), 0.0
                )
                examen_fisico.peso = safe_float_required(request.POST.get("peso"), 0.0)
                examen_fisico.temperatura = safe_float_required(
                    request.POST.get("temperatura"), 36.5
                )
                examen_fisico.frecuencia_cardiaca = safe_int_required(
                    request.POST.get("frecuencia_cardiaca"), 70
                )
                examen_fisico.frecuencia_respiratoria = safe_int_required(
                    request.POST.get("frecuencia_respiratoria"), 16
                )
                examen_fisico.presion_arterial_sistolica = safe_int_required(
                    request.POST.get("presion_arterial_sistolica"), 120
                )
                examen_fisico.presion_arterial_diastolica = safe_int_required(
                    request.POST.get("presion_arterial_diastolica"), 80
                )
                examen_fisico.perimetro_cefalico = safe_float_optional(
                    request.POST.get("perimetro_cefalico")
                )

                # === CABEZA Y CUELLO ===
                examen_fisico.cuero_cabelludo_normal = "normal" in request.POST.getlist(
                    "cuero_cabelludo"
                )
                examen_fisico.cuero_cabelludo_anormal = (
                    "anormal" in request.POST.getlist("cuero_cabelludo")
                )
                examen_fisico.observaciones_cuero_cabelludo = request.POST.get(
                    "observaciones_cuero_cabelludo", ""
                )

                examen_fisico.oidos_normal = "normal" in request.POST.getlist("oidos")
                examen_fisico.oidos_anormal = "anormal" in request.POST.getlist("oidos")
                examen_fisico.observaciones_oidos = request.POST.get(
                    "observaciones_oidos", ""
                )

                examen_fisico.nariz_normal = "normal" in request.POST.getlist("nariz")
                examen_fisico.nariz_anormal = "anormal" in request.POST.getlist("nariz")
                examen_fisico.observaciones_nariz = request.POST.get(
                    "observaciones_nariz", ""
                )

                examen_fisico.cuello_normal = "normal" in request.POST.getlist("cuello")
                examen_fisico.cuello_anormal = "anormal" in request.POST.getlist(
                    "cuello"
                )
                examen_fisico.observaciones_cuello = request.POST.get(
                    "observaciones_cuello", ""
                )

                examen_fisico.otros_hallazgos_importantes = request.POST.get(
                    "otros_hallazgos_importantes", ""
                )

                # === TÓRAX / CARDIORESPIRATORIO ===
                examen_fisico.forma_torax = request.POST.get("forma_torax", "normal")
                examen_fisico.observaciones_forma_torax = request.POST.get(
                    "observaciones_forma_torax", ""
                )
                examen_fisico.murmullo_vesicular = request.POST.get(
                    "murmullo_vesicular", "conservado"
                )
                examen_fisico.observaciones_murmullo_vesicular = request.POST.get(
                    "observaciones_murmullo_vesicular", ""
                )
                examen_fisico.ruidos_sobreagregados = bool(
                    request.POST.get("ruidos_sobreagregados")
                )
                examen_fisico.observaciones_ruidos_sobreagregados = request.POST.get(
                    "observaciones_ruidos_sobreagregados", ""
                )
                examen_fisico.ruidos_cardiacos = request.POST.get(
                    "ruidos_cardiacos", "ritmicos"
                )
                examen_fisico.observaciones_ruidos_cardiacos = request.POST.get(
                    "observaciones_ruidos_cardiacos", ""
                )

                # === ABDOMEN ===
                examen_fisico.peristaltismo = request.POST.get(
                    "peristaltismo", "presente"
                )
                examen_fisico.pared_abdominal_normal = "normal" in request.POST.getlist(
                    "pared_abdominal"
                )
                examen_fisico.pared_abdominal_anormal = (
                    "anormal" in request.POST.getlist("pared_abdominal")
                )
                examen_fisico.masas = bool(request.POST.get("masas"))
                examen_fisico.megalias = bool(request.POST.get("megalias"))
                examen_fisico.observaciones_abdomen = request.POST.get(
                    "observaciones_abdomen", ""
                )

                # === OSTEOMUSCULAR ===
                examen_fisico.curvatura_cervical_normal = (
                    "normal" in request.POST.getlist("curvatura_cervical")
                )
                examen_fisico.curvatura_cervical_anormal = (
                    "anormal" in request.POST.getlist("curvatura_cervical")
                )
                examen_fisico.curvatura_toracica_normal = (
                    "normal" in request.POST.getlist("curvatura_toracica")
                )
                examen_fisico.curvatura_toracica_anormal = (
                    "anormal" in request.POST.getlist("curvatura_toracica")
                )
                examen_fisico.curvatura_lumbar_normal = (
                    "normal" in request.POST.getlist("curvatura_lumbar")
                )
                examen_fisico.curvatura_lumbar_anormal = (
                    "anormal" in request.POST.getlist("curvatura_lumbar")
                )
                examen_fisico.arcos_movimiento_superiores_normal = (
                    "normal" in request.POST.getlist("arcos_movimiento_superiores")
                )
                examen_fisico.arcos_movimiento_superiores_anormal = (
                    "anormal" in request.POST.getlist("arcos_movimiento_superiores")
                )
                examen_fisico.arcos_movimiento_inferiores_normal = (
                    "normal" in request.POST.getlist("arcos_movimiento_inferiores")
                )
                examen_fisico.arcos_movimiento_inferiores_anormal = (
                    "anormal" in request.POST.getlist("arcos_movimiento_inferiores")
                )
                examen_fisico.asimetrias_inferiores_normal = (
                    "normal" in request.POST.getlist("asimetrias_inferiores")
                )
                examen_fisico.asimetrias_inferiores_anormal = (
                    "anormal" in request.POST.getlist("asimetrias_inferiores")
                )
                examen_fisico.asimetrias_superiores_normal = (
                    "normal" in request.POST.getlist("asimetrias_superiores")
                )
                examen_fisico.asimetrias_superiores_anormal = (
                    "anormal" in request.POST.getlist("asimetrias_superiores")
                )
                examen_fisico.observaciones_osteomuscular = request.POST.get(
                    "observaciones_osteomuscular", ""
                )

                # === PIEL Y ANEXOS ===
                examen_fisico.maculas = bool(request.POST.get("maculas"))
                examen_fisico.papulas = bool(request.POST.get("papulas"))
                examen_fisico.vesiculas = bool(request.POST.get("vesiculas"))
                examen_fisico.pustulas = bool(request.POST.get("pustulas"))
                examen_fisico.fisuras = bool(request.POST.get("fisuras"))
                examen_fisico.escaras = bool(request.POST.get("escaras"))
                examen_fisico.petequias = bool(request.POST.get("petequias"))
                examen_fisico.equimosis = bool(request.POST.get("equimosis"))
                examen_fisico.ulceras = bool(request.POST.get("ulceras"))
                examen_fisico.observaciones_piel_anexos = request.POST.get(
                    "observaciones_piel_anexos", ""
                )

            # Calcular IMC si tenemos talla y peso
            if examen_fisico.talla > 0 and examen_fisico.peso > 0:
                talla_metros = examen_fisico.talla / 100
                examen_fisico.imc = round(examen_fisico.peso / (talla_metros**2), 2)
            else:
                examen_fisico.imc = 0.0

            # Guardar los cambios
            try:
                examen_fisico.save()
            except Exception as save_error:
                raise save_error

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Examen físico general guardado correctamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except ValueError as ve:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error de datos: {str(ve)}")
            return redirect(
                "detalle_paciente", paciente_id=paciente_id if paciente_id else 1
            )

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar el examen físico: {str(e)}")
            return redirect(
                "detalle_paciente", paciente_id=paciente_id if paciente_id else 1
            )

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


# === FUNCIONES AUXILIARES ===
def safe_float_required(value, default=0.0):
    """Convierte a float con valor por defecto obligatorio"""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_required(value, default=0):
    """Convierte a int con valor por defecto obligatorio"""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float_optional(value):
    """Convierte a float o retorna None si no hay valor"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


@login_required
def guardar_revision_sistemas(request):
    """Vista específica para guardar el examen de Revisión por Sistemas"""
    if request.method == "POST":
        visita_id = request.POST.get("visita_id")
        paciente_id = request.POST.get("paciente_id")
        examen_id = request.POST.get("examen_id")

        try:
            # ===================================================
            # 1. OBTENER OBJETOS PRINCIPALES
            # ===================================================
            visita = get_object_or_404(Visita, id=visita_id)
            examen = get_object_or_404(Examen, id=examen_id)
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)

            # Obtener o crear VisitaExamen
            visita_examen, created = VisitaExamen.objects.get_or_create(
                visita=visita, examen=examen, defaults={"estado": "pendiente"}
            )

            # ===================================================
            # 2. OBTENER O CREAR EL RESULTADO PRINCIPAL
            # ===================================================
            resultado, resultado_created = RevisionSistemasResult.objects.get_or_create(
                visita_examen=visita_examen, defaults={}
            )

            accion = "creado" if resultado_created else "actualizado"

            # ===================================================
            # 3. ACTUALIZAR CAMPOS DE CONTROL DE SISTEMAS
            # ===================================================
            sistemas = [
                "general",
                "cabeza_cuello",
                "cardiopulmonar",
                "gastrointestinal",
                "genitourinario",
                "vascular_periferico",
                "osteomuscular",
                "piel_faneras",
                "otros",
            ]

            sistemas_activados = []
            for sistema in sistemas:
                campo_sintoma = f"sintoma_{sistema}"
                valor_sintoma = request.POST.get(campo_sintoma, "no")

                # Actualizar campo en el modelo principal
                setattr(resultado, campo_sintoma, valor_sintoma)

                if valor_sintoma == "si":
                    sistemas_activados.append(sistema)

            resultado.save()

            # ===================================================
            # 4. PROCESAR SÍNTOMAS DETALLADOS
            # ===================================================
            # Eliminar detalles existentes para actualización completa
            DetalleRevisionSistemas.objects.filter(
                revision_sistemas_result=resultado
            ).delete()

            total_sintomas_guardados = 0

            for sistema in sistemas_activados:
                # Obtener arrays del formulario
                sintomas = request.POST.getlist(f"{sistema}_sintoma[]")
                tiempos = request.POST.getlist(f"{sistema}_tiempo[]")
                caracteristicas_list = request.POST.getlist(
                    f"{sistema}_caracteristicas[]"
                )

                # Crear detalles para cada síntoma del sistema
                for i in range(len(sintomas)):
                    sintoma = sintomas[i].strip() if i < len(sintomas) else ""
                    tiempo = tiempos[i].strip() if i < len(tiempos) else ""
                    caracteristica = (
                        caracteristicas_list[i].strip()
                        if i < len(caracteristicas_list)
                        else ""
                    )

                    # Solo guardar si hay contenido en el síntoma
                    if sintoma:
                        detalle = DetalleRevisionSistemas.objects.create(
                            revision_sistemas_result=resultado,
                            sistema=sistema,
                            sintoma=sintoma,
                            tiempo=tiempo,
                            caracteristicas=caracteristica,
                        )
                        total_sintomas_guardados += 1

            # ===================================================
            # 5. ACTUALIZAR ESTADO DE LA VISITA-EXAMEN
            # ===================================================
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # ===================================================
            # 6. MENSAJE DE ÉXITO Y REDIRECCIÓN
            # ===================================================
            mensaje_resumen = (
                f"Revisión por Sistemas {accion} correctamente. "
                f"Sistemas evaluados: {len(sistemas_activados)}, "
                f"Síntomas registrados: {total_sintomas_guardados}"
            )

            messages.success(request, mensaje_resumen)

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(
                request, f"Error al procesar Revisión por Sistemas: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

    # Si no es POST, redirigir al home
    return redirect("home")


@login_required
def guardar_examen_neurologico(request):
    """Vista específica para guardar el examen neurológico"""
    if request.method == "POST":
        visita_id = request.POST.get("visita_examen")
        paciente_id = request.POST.get("paciente_id")
        examen_id = request.POST.get("examen_id")

        try:
            # ===================================================
            # 1. OBTENER OBJETOS PRINCIPALES
            # ===================================================
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)

            # ===================================================
            # 2. OBTENER O CREAR EL RESULTADO
            # ===================================================
            resultado, created = ExamenNeurologicoResult.objects.get_or_create(
                visita_examen=visita_examen, defaults={}
            )

            accion = "creado" if created else "actualizado"

            # ===================================================
            # 3. PROCESAR CAMPOS I PAR CRANEAL (OLFATORIO)
            # ===================================================
            resultado.clavos_izquierdo = request.POST.get("clavos_izquierdo") == "on"
            resultado.clavos_derecho = request.POST.get("clavos_derecho") == "on"
            resultado.pimienta_izquierdo = (
                request.POST.get("pimienta_izquierdo") == "on"
            )
            resultado.pimienta_derecho = request.POST.get("pimienta_derecho") == "on"
            resultado.cafe_izquierdo = request.POST.get("cafe_izquierdo") == "on"
            resultado.cafe_derecho = request.POST.get("cafe_derecho") == "on"
            resultado.canela_izquierdo = request.POST.get("canela_izquierdo") == "on"
            resultado.canela_derecho = request.POST.get("canela_derecho") == "on"
            resultado.alcohol_izquierdo = request.POST.get("alcohol_izquierdo") == "on"
            resultado.alcohol_derecho = request.POST.get("alcohol_derecho") == "on"

            # ===================================================
            # 4. PROCESAR CAMPOS II PAR CRANEAL (ÓPTICO)
            # ===================================================
            # Síntomas visuales
            resultado.amaurosis = request.POST.get("amaurosis") == "on"
            resultado.oscurecimientos = request.POST.get("oscurecimientos") == "on"
            resultado.fotopsias = request.POST.get("fotopsias") == "on"
            resultado.escotomas = request.POST.get("escotomas") == "on"
            resultado.agudeza_visual = request.POST.get("agudeza_visual") == "on"

            # Fundoscopia
            resultado.hemorragias = request.POST.get("hemorragias") == "on"
            resultado.exudados = request.POST.get("exudados") == "on"
            resultado.fundoscopia = request.POST.get("fundoscopia") or None

            # Evaluación detallada
            resultado.color_disco = request.POST.get("color_disco") or None
            resultado.bordes = request.POST.get("bordes") or None

            # Pupilas y reflejos
            resultado.pupilas = request.POST.get("pupilas") or None
            resultado.reflejo_fotomotor = request.POST.get("reflejo_fotomotor") or None
            resultado.vision_colores = request.POST.get("vision_colores") or None

            # Campimetría
            resultado.campimetria = request.POST.get("campimetria") or None

            # Observaciones II Par
            resultado.observaciones_ii_par = request.POST.get(
                "observaciones_ii_par", ""
            ).strip()

            # ===================================================
            # 5. PROCESAR CAMPOS III, IV, VI PAR (OCULOMOTORES)
            # ===================================================
            # Síntomas
            resultado.diplopia = request.POST.get("diplopia") == "on"
            resultado.ptosis_palpebral = request.POST.get("ptosis_palpebral") == "on"
            resultado.desviaciones_oculares = (
                request.POST.get("desviaciones_oculares") == "on"
            )

            # Funciones motoras
            resultado.elevacion_parpado = request.POST.get("elevacion_parpado") or None
            resultado.movimientos_oculares = (
                request.POST.get("movimientos_oculares") or None
            )

            # Coordinación
            resultado.mirada_conjugada = request.POST.get("mirada_conjugada") or None
            resultado.movimientos_seguimiento = (
                request.POST.get("movimientos_seguimiento") or None
            )

            # Observaciones Oculomotores
            resultado.observaciones_oculomotores = request.POST.get(
                "observaciones_oculomotores", ""
            ).strip()

            # ===================================================
            # 6. PROCESAR CAMPOS V PAR CRANEAL (TRIGÉMINO)
            # ===================================================
            # Tacto superficial
            resultado.tacto_frente_globo = (
                request.POST.get("tacto_frente_globo") == "on"
            )
            resultado.tacto_parpado_labio_sup = (
                request.POST.get("tacto_parpado_labio_sup") == "on"
            )
            resultado.tacto_labio_inf_menton = (
                request.POST.get("tacto_labio_inf_menton") == "on"
            )

            # Dolor
            resultado.dolor_frente_globo = (
                request.POST.get("dolor_frente_globo") == "on"
            )
            resultado.dolor_parpado_labio_sup = (
                request.POST.get("dolor_parpado_labio_sup") == "on"
            )
            resultado.dolor_labio_inf_menton = (
                request.POST.get("dolor_labio_inf_menton") == "on"
            )

            # Temperatura
            resultado.temp_frente_globo = request.POST.get("temp_frente_globo") == "on"
            resultado.temp_parpado_labio_sup = (
                request.POST.get("temp_parpado_labio_sup") == "on"
            )
            resultado.temp_labio_inf_menton = (
                request.POST.get("temp_labio_inf_menton") == "on"
            )

            # Fuerza muscular
            resultado.fuerza_maseteros = request.POST.get("fuerza_maseteros") == "on"
            resultado.fuerza_temporales = request.POST.get("fuerza_temporales") == "on"
            resultado.fuerza_pterigoideos = (
                request.POST.get("fuerza_pterigoideos") == "on"
            )

            # Trofismo
            resultado.trofismo_maseteros = (
                request.POST.get("trofismo_maseteros") == "on"
            )
            resultado.trofismo_temporales = (
                request.POST.get("trofismo_temporales") == "on"
            )
            resultado.trofismo_pterigoideos = (
                request.POST.get("trofismo_pterigoideos") == "on"
            )

            # Observaciones V Par
            resultado.observaciones_v_par = request.POST.get(
                "observaciones_v_par", ""
            ).strip()

            # ===================================================
            # 7. PROCESAR CAMPOS VII PAR CRANEAL (FACIAL)
            # ===================================================
            # Mímica facial
            resultado.mimica_frente = request.POST.get("mimica_frente") == "on"
            resultado.mimica_parpados = request.POST.get("mimica_parpados") == "on"
            resultado.mimica_elevacion_nasal = (
                request.POST.get("mimica_elevacion_nasal") == "on"
            )
            resultado.mimica_buccinadores = (
                request.POST.get("mimica_buccinadores") == "on"
            )
            resultado.mimica_orbicular_labios = (
                request.POST.get("mimica_orbicular_labios") == "on"
            )

            # Gusto
            resultado.gusto_anterior = request.POST.get("gusto_anterior") or None

            # ===================================================
            # 8. PROCESAR CAMPOS VIII PAR CRANEAL (AUDITIVO)
            # ===================================================
            # Síntomas auditivos
            resultado.hipoacusia = request.POST.get("hipoacusia") == "on"
            resultado.tinitus = request.POST.get("tinitus") == "on"
            resultado.acufenos = request.POST.get("acufenos") == "on"

            # Pruebas auditivas
            resultado.weber = request.POST.get("weber") or None
            resultado.rinne = request.POST.get("rinne") or None

            # Síntomas vestibulares
            resultado.vertigo = request.POST.get("vertigo") == "on"
            resultado.mareo = request.POST.get("mareo") == "on"
            resultado.nistagmus = request.POST.get("nistagmus") == "on"

            # Observaciones VIII Par
            resultado.observaciones_viii_par = request.POST.get(
                "observaciones_viii_par", ""
            ).strip()

            # ===================================================
            # 9. PROCESAR CAMPOS IX Y X PAR (GLOSOFARÍNGEO Y VAGO)
            # ===================================================
            # Síntomas vocales
            resultado.disfonia = request.POST.get("disfonia") == "on"
            resultado.afonia = request.POST.get("afonia") == "on"
            resultado.voz_nasal = request.POST.get("voz_nasal") == "on"

            # Síntomas deglutorios
            resultado.disfagia = request.POST.get("disfagia") == "on"
            resultado.sialorrea = request.POST.get("sialorrea") == "on"
            resultado.dolor_faringe = request.POST.get("dolor_faringe") == "on"

            # Exploración física
            resultado.reflejo_nauseoso = request.POST.get("reflejo_nauseoso") or None
            resultado.uvula = request.POST.get("uvula") or None
            resultado.paladar = request.POST.get("paladar") or None
            resultado.gusto_posterior = request.POST.get("gusto_posterior") or None

            # ===================================================
            # 10. PROCESAR CAMPOS XI PAR (ESPINAL ACCESORIO)
            # ===================================================
            resultado.movimientos_cuello = (
                request.POST.get("movimientos_cuello") or None
            )
            resultado.elevacion_hombros = request.POST.get("elevacion_hombros") or None
            resultado.atrofia_lingual = request.POST.get("atrofia_lingual") == "on"

            # Observaciones XI Par
            resultado.observaciones_xi_par = request.POST.get(
                "observaciones_xi_par", ""
            ).strip()

            # ===================================================
            # 11. PROCESAR CAMPOS XII PAR (HIPOGLOSO)
            # ===================================================
            resultado.fasciculaciones_linguales = (
                request.POST.get("fasciculaciones_linguales") == "on"
            )
            resultado.movimientos_lengua = (
                request.POST.get("movimientos_lengua") or None
            )

            # Observaciones XII Par
            resultado.observaciones_xii_par = request.POST.get(
                "observaciones_xii_par", ""
            ).strip()

            # ===================================================
            # 12. PROCESAR SENSIBILIDAD
            # ===================================================
            # Dolor al pinchazo
            resultado.dolor_cuello = request.POST.get("dolor_cuello") == "on"
            resultado.dolor_torax = request.POST.get("dolor_torax") == "on"
            resultado.dolor_miembros_superiores = (
                request.POST.get("dolor_miembros_superiores") == "on"
            )
            resultado.dolor_abdomen = request.POST.get("dolor_abdomen") == "on"
            resultado.dolor_miembros_inferiores = (
                request.POST.get("dolor_miembros_inferiores") == "on"
            )

            # Táctil superficial
            resultado.tactil_cuello = request.POST.get("tactil_cuello") == "on"
            resultado.tactil_torax = request.POST.get("tactil_torax") == "on"
            resultado.tactil_miembros_superiores = (
                request.POST.get("tactil_miembros_superiores") == "on"
            )
            resultado.tactil_abdomen = request.POST.get("tactil_abdomen") == "on"
            resultado.tactil_miembros_inferiores = (
                request.POST.get("tactil_miembros_inferiores") == "on"
            )

            # Discriminación térmica
            resultado.termica_cuello = request.POST.get("termica_cuello") == "on"
            resultado.termica_torax = request.POST.get("termica_torax") == "on"
            resultado.termica_miembros_superiores = (
                request.POST.get("termica_miembros_superiores") == "on"
            )
            resultado.termica_abdomen = request.POST.get("termica_abdomen") == "on"
            resultado.termica_miembros_inferiores = (
                request.POST.get("termica_miembros_inferiores") == "on"
            )

            # Sensibilidad especializada
            resultado.vibratoria = request.POST.get("vibratoria") or None
            resultado.propiocepcion_superiores = (
                request.POST.get("propiocepcion_superiores") or None
            )
            resultado.propiocepcion_inferiores = (
                request.POST.get("propiocepcion_inferiores") or None
            )
            resultado.reconocimiento_objetos = (
                request.POST.get("reconocimiento_objetos") or None
            )
            resultado.discriminacion_dos_puntos = (
                request.POST.get("discriminacion_dos_puntos") or None
            )

            # Observaciones Sensibilidad
            resultado.observaciones_sensibilidad = request.POST.get(
                "observaciones_sensibilidad", ""
            ).strip()

            # ===================================================
            # 13. PROCESAR REFLEJOS
            # ===================================================
            # Reflejos osteotendinosos
            resultado.maseteriano_izquierdo = (
                request.POST.get("maseteriano_izquierdo") or None
            )
            resultado.maseteriano_derecho = (
                request.POST.get("maseteriano_derecho") or None
            )

            # Miembros superiores
            resultado.tricipital_izquierdo = (
                request.POST.get("tricipital_izquierdo") or None
            )
            resultado.tricipital_derecho = (
                request.POST.get("tricipital_derecho") or None
            )
            resultado.bicipital_izquierdo = (
                request.POST.get("bicipital_izquierdo") or None
            )
            resultado.bicipital_derecho = request.POST.get("bicipital_derecho") or None
            resultado.estilorradial_izquierdo = (
                request.POST.get("estilorradial_izquierdo") or None
            )
            resultado.estilorradial_derecho = (
                request.POST.get("estilorradial_derecho") or None
            )
            resultado.cubitopronador_izquierdo = (
                request.POST.get("cubitopronador_izquierdo") or None
            )
            resultado.cubitopronador_derecho = (
                request.POST.get("cubitopronador_derecho") or None
            )

            # Reflejos cutáneos
            resultado.cutaneo_abdominal_izquierdo = (
                request.POST.get("cutaneo_abdominal_izquierdo") or None
            )
            resultado.cutaneo_abdominal_derecho = (
                request.POST.get("cutaneo_abdominal_derecho") or None
            )

            # Miembros inferiores
            resultado.rotuliano_izquierdo = (
                request.POST.get("rotuliano_izquierdo") or None
            )
            resultado.rotuliano_derecho = request.POST.get("rotuliano_derecho") or None
            resultado.aquiliano_izquierdo = (
                request.POST.get("aquiliano_izquierdo") or None
            )
            resultado.aquiliano_derecho = request.POST.get("aquiliano_derecho") or None

            # Reflejos patológicos
            resultado.glabela = request.POST.get("glabela") or None
            resultado.succion = request.POST.get("succion") or None
            resultado.palmomentoniano = request.POST.get("palmomentoniano") or None
            resultado.hoffman = request.POST.get("hoffman") or None
            resultado.palmar = request.POST.get("palmar") or None
            resultado.marinesco = request.POST.get("marinesco") or None
            resultado.prension = request.POST.get("prension") or None

            # Observaciones Reflejos
            resultado.observaciones_reflejos = request.POST.get(
                "observaciones_reflejos", ""
            ).strip()

            # ===================================================
            # 14. PROCESAR FUERZA MUSCULAR
            # ===================================================
            # Miembro Superior - Brazo
            resultado.brazo_abduccion_izq = (
                request.POST.get("brazo_abduccion_izq") or None
            )
            resultado.brazo_abduccion_der = (
                request.POST.get("brazo_abduccion_der") or None
            )
            resultado.brazo_antepulsion_izq = (
                request.POST.get("brazo_antepulsion_izq") or None
            )
            resultado.brazo_antepulsion_der = (
                request.POST.get("brazo_antepulsion_der") or None
            )
            resultado.brazo_rotacion_interna_izq = (
                request.POST.get("brazo_rotacion_interna_izq") or None
            )
            resultado.brazo_rotacion_interna_der = (
                request.POST.get("brazo_rotacion_interna_der") or None
            )
            resultado.brazo_rotacion_externa_izq = (
                request.POST.get("brazo_rotacion_externa_izq") or None
            )
            resultado.brazo_rotacion_externa_der = (
                request.POST.get("brazo_rotacion_externa_der") or None
            )

            # Miembro Superior - Antebrazo
            resultado.antebrazo_flexion_izq = (
                request.POST.get("antebrazo_flexion_izq") or None
            )
            resultado.antebrazo_flexion_der = (
                request.POST.get("antebrazo_flexion_der") or None
            )
            resultado.antebrazo_extension_izq = (
                request.POST.get("antebrazo_extension_izq") or None
            )
            resultado.antebrazo_extension_der = (
                request.POST.get("antebrazo_extension_der") or None
            )

            # Miembro Superior - Mano
            resultado.mano_flexion_izq = request.POST.get("mano_flexion_izq") or None
            resultado.mano_flexion_der = request.POST.get("mano_flexion_der") or None
            resultado.mano_extension_izq = (
                request.POST.get("mano_extension_izq") or None
            )
            resultado.mano_extension_der = (
                request.POST.get("mano_extension_der") or None
            )
            resultado.mano_prension_izq = request.POST.get("mano_prension_izq") or None
            resultado.mano_prension_der = request.POST.get("mano_prension_der") or None

            # Miembro Inferior - Muslo
            resultado.muslo_flexion_izq = request.POST.get("muslo_flexion_izq") or None
            resultado.muslo_flexion_der = request.POST.get("muslo_flexion_der") or None
            resultado.muslo_abduccion_izq = (
                request.POST.get("muslo_abduccion_izq") or None
            )
            resultado.muslo_abduccion_der = (
                request.POST.get("muslo_abduccion_der") or None
            )
            resultado.muslo_aduccion_izq = (
                request.POST.get("muslo_aduccion_izq") or None
            )
            resultado.muslo_aduccion_der = (
                request.POST.get("muslo_aduccion_der") or None
            )

            # Miembro Inferior - Pierna
            resultado.pierna_flexion_izq = (
                request.POST.get("pierna_flexion_izq") or None
            )
            resultado.pierna_flexion_der = (
                request.POST.get("pierna_flexion_der") or None
            )
            resultado.pierna_extension_izq = (
                request.POST.get("pierna_extension_izq") or None
            )
            resultado.pierna_extension_der = (
                request.POST.get("pierna_extension_der") or None
            )

            # Miembro Inferior - Pie
            resultado.pie_flexion_izq = request.POST.get("pie_flexion_izq") or None
            resultado.pie_flexion_der = request.POST.get("pie_flexion_der") or None
            resultado.pie_extension_izq = request.POST.get("pie_extension_izq") or None
            resultado.pie_extension_der = request.POST.get("pie_extension_der") or None
            resultado.pie_eversion_izq = request.POST.get("pie_eversion_izq") or None
            resultado.pie_eversion_der = request.POST.get("pie_eversion_der") or None
            resultado.pie_inversion_izq = request.POST.get("pie_inversion_izq") or None
            resultado.pie_inversion_der = request.POST.get("pie_inversion_der") or None

            # Observaciones Fuerza
            resultado.observaciones_fuerza = request.POST.get(
                "observaciones_fuerza", ""
            ).strip()

            # ===================================================
            # 15. PROCESAR COORDINACIÓN
            # ===================================================
            resultado.coordinacion_dedo_nariz = (
                request.POST.get("coordinacion_dedo_nariz") or None
            )
            resultado.romberg = request.POST.get("romberg") or None
            resultado.talon_rodilla = request.POST.get("talon_rodilla") or None
            resultado.pronacion_supinacion = (
                request.POST.get("pronacion_supinacion") or None
            )

            # ===================================================
            # 16. PROCESAR MARCHA
            # ===================================================
            # Evaluación básica
            resultado.postura = request.POST.get("postura") or None
            resultado.marcha_lineal = request.POST.get("marcha_lineal") or None
            resultado.marcha_puntillas = request.POST.get("marcha_puntillas") or None

            # Patrones patológicos
            resultado.marcha_hemiplejica = (
                request.POST.get("marcha_hemiplejica") == "on"
            )
            resultado.marcha_parkinsoniana = (
                request.POST.get("marcha_parkinsoniana") == "on"
            )
            resultado.marcha_espastica = request.POST.get("marcha_espastica") == "on"
            resultado.marcha_polineuritica = (
                request.POST.get("marcha_polineuritica") == "on"
            )
            resultado.marcha_ataxica = request.POST.get("marcha_ataxica") == "on"
            resultado.marcha_miopatica = request.POST.get("marcha_miopatica") == "on"
            resultado.marcha_steppage = request.POST.get("marcha_steppage") == "on"

            # Observaciones Marcha
            resultado.observaciones_marcha = request.POST.get(
                "observaciones_marcha", ""
            ).strip()

            # ===================================================
            # 17. PROCESAR MOVIMIENTOS ANORMALES
            # ===================================================
            resultado.convulsiones = request.POST.get("convulsiones") == "on"
            resultado.fasciculaciones = request.POST.get("fasciculaciones") == "on"
            resultado.mioclonias = request.POST.get("mioclonias") == "on"
            resultado.temblores = request.POST.get("temblores") == "on"
            resultado.corea = request.POST.get("corea") == "on"
            resultado.espasmos = request.POST.get("espasmos") == "on"
            resultado.balismos = request.POST.get("balismos") == "on"
            resultado.calambres = request.POST.get("calambres") == "on"
            resultado.tics = request.POST.get("tics") == "on"
            resultado.distonias = request.POST.get("distonias") == "on"

            # ===================================================
            # 18. GUARDAR RESULTADO
            # ===================================================
            resultado.save()

            # ===================================================
            # 19. ACTUALIZAR ESTADO DE LA VISITA-EXAMEN
            # ===================================================
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # ===================================================
            # 20. GENERAR RESUMEN PARA EL MENSAJE
            # ===================================================
            # Contar campos completados
            campos_completados = 0
            total_campos = 0

            # Contar pares craneales
            if any(
                [
                    resultado.clavos_izquierdo,
                    resultado.clavos_derecho,
                    resultado.pimienta_izquierdo,
                    resultado.pimienta_derecho,
                    resultado.cafe_izquierdo,
                    resultado.cafe_derecho,
                ]
            ):
                campos_completados += 1
            total_campos += 1

            if any(
                [resultado.amaurosis, resultado.agudeza_visual, resultado.fundoscopia]
            ):
                campos_completados += 1
            total_campos += 1

            if any(
                [
                    resultado.diplopia,
                    resultado.ptosis_palpebral,
                    resultado.movimientos_oculares,
                ]
            ):
                campos_completados += 1
            total_campos += 1

            # Contar sensibilidad
            sensibilidad_count = 0
            if any(
                [
                    resultado.dolor_cuello,
                    resultado.dolor_torax,
                    resultado.dolor_miembros_superiores,
                    resultado.dolor_abdomen,
                    resultado.dolor_miembros_inferiores,
                ]
            ):
                sensibilidad_count += 1
            if any(
                [
                    resultado.tactil_cuello,
                    resultado.tactil_torax,
                    resultado.tactil_miembros_superiores,
                    resultado.tactil_abdomen,
                    resultado.tactil_miembros_inferiores,
                ]
            ):
                sensibilidad_count += 1
            if any(
                [
                    resultado.termica_cuello,
                    resultado.termica_torax,
                    resultado.termica_miembros_superiores,
                    resultado.termica_abdomen,
                    resultado.termica_miembros_inferiores,
                ]
            ):
                sensibilidad_count += 1

            # Contar reflejos evaluados
            reflejos_evaluados = 0
            reflejos_campos = [
                resultado.maseteriano_izquierdo,
                resultado.maseteriano_derecho,
                resultado.bicipital_izquierdo,
                resultado.bicipital_derecho,
                resultado.tricipital_izquierdo,
                resultado.tricipital_derecho,
                resultado.rotuliano_izquierdo,
                resultado.rotuliano_derecho,
                resultado.aquiliano_izquierdo,
                resultado.aquiliano_derecho,
            ]
            reflejos_evaluados = sum(1 for r in reflejos_campos if r is not None)

            # Contar fuerza evaluada
            fuerza_evaluada = 0
            fuerza_campos = [
                resultado.brazo_abduccion_izq,
                resultado.brazo_abduccion_der,
                resultado.antebrazo_flexion_izq,
                resultado.antebrazo_flexion_der,
                resultado.mano_flexion_izq,
                resultado.mano_flexion_der,
                resultado.muslo_flexion_izq,
                resultado.muslo_flexion_der,
                resultado.pierna_flexion_izq,
                resultado.pierna_flexion_der,
                resultado.pie_flexion_izq,
                resultado.pie_flexion_der,
            ]
            fuerza_evaluada = sum(1 for f in fuerza_campos if f is not None)

            mensaje_resumen = (
                f"✅ Examen Neurológico {accion} correctamente.\n"
                f"📊 Pares craneales: {campos_completados}/{total_campos} evaluados\n"
                f"🧠 Sensibilidad: {sensibilidad_count} tipos evaluados\n"
                f"🔨 Reflejos: {reflejos_evaluados} evaluados\n"
                f"💪 Fuerza muscular: {fuerza_evaluada} movimientos evaluados"
            )

            messages.success(request, mensaje_resumen)

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback

            messages.error(request, f"Error al procesar Examen Neurológico: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id)

    # Si no es POST, redirigir al home
    return redirect("home")
