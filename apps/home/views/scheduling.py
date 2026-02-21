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
                "proyectos": Proyecto.objects.all(),
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
            proyecto_id = data.get("proyecto_id", None)

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

            # Obtener proyecto asociado (opcional)
            proyecto_obj = None
            if proyecto_id:
                try:
                    proyecto_obj = Proyecto.objects.get(id=int(proyecto_id))
                except (Proyecto.DoesNotExist, ValueError, TypeError):
                    pass

            # Crear la nueva cita
            nueva_cita = CitaMedica.objects.create(
                disponibilidad=disponibilidad,
                fecha_cita=fecha_cita,
                email_paciente=email_paciente.lower().strip(),
                nombre_paciente=nombre_paciente.strip(),
                telefono_paciente=telefono_paciente.strip(),
                motivo_consulta=motivo_consulta.strip(),
                estado="agendada",
                proyecto=proyecto_obj,
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

        <h3>Si no logró finalizar el diligenciamiento de los formularios, por favor ingrese su número de cédula en el botón “Consultar exámenes pendientes” para continuar con el proceso.</h3>
        
        <h3>📄 CONSENTIMIENTO INFORMADO</h3>
        <p>Adjunto encontrará el consentimiento informado del Proyecto Sueño. Por favor léalo antes de asistir a su cita.</p>

        <h3>📌 RECORDATORIO</h3>
        <p>Duerma de manera habitual la noche anterior y llegue 10 minutos antes de su hora programada.</p>
        <p>Esta cita no requiere dormir durante la sesión.</p>

        <p>Se generará una constancia de asistencia al finalizar la evaluación.
        La constancia no constituye excusa válida para ausencias académicas.</p>

        <p>Para cancelar o reprogramar, comuníquese con anticipación a 
        <strong>veronica.ramirezl@udea.edu.co</strong></p>

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
            "CONSENTIMIENTOINFORMADOESTUDIANTES.pdf",
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
@user_passes_test(lambda u: u.is_superuser, login_url="/login/")
def gestionar_salas(request):
    """Vista para gestionar salas (crear, editar, desactivar)"""
    if request.method == "POST":
        accion = request.POST.get("accion")
        
        if accion == "crear_sala":
            nombre = request.POST.get("nombre", "").strip()
            descripcion = request.POST.get("descripcion", "").strip()
            capacidad = request.POST.get("capacidad", 1)
            
            if not nombre:
                messages.error(request, "El nombre de la sala es obligatorio")
            elif Sala.objects.filter(nombre=nombre).exists():
                messages.error(request, "Ya existe una sala con ese nombre")
            else:
                try:
                    sala = Sala.objects.create(
                        nombre=nombre,
                        descripcion=descripcion,
                        capacidad=int(capacidad),
                        activa=True
                    )
                    messages.success(request, f"Sala '{sala.nombre}' creada exitosamente")
                except Exception as e:
                    messages.error(request, f"Error al crear la sala: {str(e)}")
            
            return redirect("gestionar_salas")
        
        elif accion == "editar_sala":
            sala_id = request.POST.get("sala_id")
            sala = get_object_or_404(Sala, id=sala_id)
            
            sala.nombre = request.POST.get("nombre", sala.nombre).strip()
            sala.descripcion = request.POST.get("descripcion", sala.descripcion).strip()
            sala.capacidad = int(request.POST.get("capacidad", sala.capacidad))
            
            try:
                sala.save()
                messages.success(request, f"Sala '{sala.nombre}' actualizada exitosamente")
            except Exception as e:
                messages.error(request, f"Error al actualizar la sala: {str(e)}")
            
            return redirect("gestionar_salas")
        
        elif accion == "desactivar_sala":
            sala_id = request.POST.get("sala_id")
            sala = get_object_or_404(Sala, id=sala_id)
            sala.activa = False
            sala.save()
            messages.success(request, f"Sala '{sala.nombre}' desactivada exitosamente")
            return redirect("gestionar_salas")
        
        elif accion == "activar_sala":
            sala_id = request.POST.get("sala_id")
            sala = get_object_or_404(Sala, id=sala_id)
            sala.activa = True
            sala.save()
            messages.success(request, f"Sala '{sala.nombre}' activada exitosamente")
            return redirect("gestionar_salas")
    
    # Obtener todas las salas
    salas = Sala.objects.all().order_by("-activa", "nombre")
    salas_activas = salas.filter(activa=True)
    salas_inactivas = salas.filter(activa=False)
    
    context = {
        "salas": salas,
        "salas_activas": salas_activas,
        "salas_inactivas": salas_inactivas,
        "segment": "gestionar_salas",
    }
    
    return render(request, "scheduling/gestionar_salas.html", context)


@login_required
def api_eventos_disponibilidad(request):
    try:
        disponibilidades = DisponibilidadUsuario.objects.filter(
            activa=True
        ).select_related("usuario", "sala")

        eventos = []
        fecha_inicio = timezone.now().date()

        # ================================
        # 1️⃣ OBTENER CITAS PRIMERO
        # ================================
        citas = CitaMedica.objects.filter(
            estado__in=["agendada", "confirmada"]
        ).select_related("disponibilidad", "disponibilidad__sala", "disponibilidad__usuario")

        # Crear set de slots ocupados (disponibilidad_id + fecha)
        slots_ocupados = set()
        for cita in citas:
            slot_key = f"{cita.disponibilidad.id}_{cita.fecha_cita.strftime('%Y%m%d')}"
            slots_ocupados.add(slot_key)

        # ================================
        # 2️⃣ EVENTOS DE DISPONIBILIDAD (excluir ocupados)
        # ================================
        for disp in disponibilidades:
            for semana in range(12):
                fecha_base = fecha_inicio + timedelta(weeks=semana)
                dias_diferencia = (disp.dia_semana - fecha_base.weekday()) % 7
                fecha_evento = fecha_base + timedelta(days=dias_diferencia)

                if fecha_evento >= disp.fecha_inicio:
                    if not disp.fecha_fin or fecha_evento <= disp.fecha_fin:
                        # Verificar si este slot está ocupado
                        slot_key = f"{disp.id}_{fecha_evento.strftime('%Y%m%d')}"
                        if slot_key not in slots_ocupados:
                            eventos.append(
                                {
                                    "id": f"disp_{disp.id}_{fecha_evento.strftime('%Y%m%d')}",
                                    "title": f"Disponible - {disp.sala.nombre}",
                                    "start": f"{fecha_evento}T{disp.hora_inicio}",
                                    "end": f"{fecha_evento}T{disp.hora_fin}",
                                    "backgroundColor": "#28a745",
                                    "borderColor": "#28a745",
                                    "extendedProps": {
                                        "tipo": "disponibilidad",
                                        "sala": disp.sala.nombre,
                                        "usuario": disp.usuario.get_full_name() or disp.usuario.username,
                                        "disponibilidad_id": disp.id,
                                    },
                                }
                            )

        # ================================
        # 3️⃣ EVENTOS DE CITAS (color verde)
        # ================================
        for cita in citas:
            cita_color = "#fd7e14"
            if cita.disponibilidad.usuario_id == 14:
                cita_color = "#b084f5"
            eventos.append(
                {
                    "id": f"cita_{cita.id}",
                    "title": f"Cita: {cita.nombre_paciente}",
                    "start": f"{cita.fecha_cita}T{cita.disponibilidad.hora_inicio}",
                    "end": f"{cita.fecha_cita}T{cita.disponibilidad.hora_fin}",
                    "backgroundColor": cita_color,
                    "borderColor": cita_color,
                    "extendedProps": {
                        "tipo": "cita",
                        "cita_id": cita.id,
                        "paciente": cita.nombre_paciente,
                        "telefono": cita.telefono_paciente,
                        "email": cita.email_paciente,
                        "sala": cita.disponibilidad.sala.nombre,
                        "profesional": cita.disponibilidad.usuario.get_full_name() or cita.disponibilidad.usuario.username,
                        "motivo": cita.motivo_consulta,
                        "estado": cita.get_estado_display(),
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


