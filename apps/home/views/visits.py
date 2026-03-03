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
from django.db.models import Max, F
from datetime import datetime, timedelta
from ..models import *
from ..forms import ProyectoForm, RegistroDemograficoForm
import json
import requests
import logging
import os
from io import BytesIO
from .auth import is_superuser
from .pdf import construir_pdf_visita

logger = logging.getLogger(__name__)

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

        # Procesar los exámenes seleccionados: soportar inputs múltiples o JSON
        try:
            post_list = request.POST.getlist("examenes_seleccionados") or []
            lista_ids_examenes = []

            if post_list:
                # Si viene una sola cadena que es JSON, parsearla
                if len(post_list) == 1:
                    single = post_list[0]
                    try:
                        parsed = json.loads(single)
                        if isinstance(parsed, list):
                            lista_ids_examenes = parsed
                        else:
                            lista_ids_examenes = post_list
                    except Exception:
                        lista_ids_examenes = post_list
                else:
                    lista_ids_examenes = post_list
            else:
                # Fallback: intentar obtener como string JSON
                s = request.POST.get("examenes_seleccionados")
                if s:
                    try:
                        parsed = json.loads(s)
                        if isinstance(parsed, list):
                            lista_ids_examenes = parsed
                        else:
                            lista_ids_examenes = [s]
                    except Exception:
                        lista_ids_examenes = [s]

            # Normalizar a enteros y crear VisitaExamen (ignorar IDs inválidos)
            created_count = 0
            clean_ids = []
            for eid in lista_ids_examenes:
                try:
                    clean_ids.append(int(eid))
                except (TypeError, ValueError):
                    continue

            for examen_id in clean_ids:
                try:
                    examen = Examen.objects.get(id=examen_id)
                    VisitaExamen.objects.create(visita=nueva_visita, examen=examen)
                    created_count += 1
                except Examen.DoesNotExist:
                    continue

            if created_count:
                messages.success(
                    request,
                    f"Visita creada con éxito con {created_count} exámenes asociados.",
                )
        except Exception as e:
            messages.error(request, f"Error al procesar los exámenes seleccionados: {str(e)}")

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
@user_passes_test(is_superuser, login_url="/login/")
def eliminar_v(request, visita_id):
    if request.method != "POST":
        messages.error(request, "Método no permitido.")
        return redirect("index")

    visita = get_object_or_404(Visita, id=visita_id)
    paciente_id = visita.paciente.id  # Para redirigir después de eliminar

    visita.delete()
    messages.success(request, "Visita eliminada correctamente.")

    return redirect("detalle_paciente", paciente_id=paciente_id)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def firmar_visita(request, visita_id):
    """
    Firmar una visita. Solo superusuarios pueden firmar.
    Al firmar: se marca firmado=True, firmado_por=usuario, estado_visita=cerrada
    Además, envía un correo al paciente con el PDF de la historia clínica.
    """
    if request.method == "POST":
        visita = get_object_or_404(Visita, id=visita_id)
        paciente_id = visita.paciente.id
        paciente = visita.paciente

        # Marcar la visita como firmada y cerrada
        visita.firmado = True
        visita.firmado_por = request.user
        visita.estado_visita = "cerrada"
        visita.save()

        # ========== ENVIAR CORREO CON PDF ==========
        try:
            # Verificar si hay fecha de seguimiento en el examen de análisis
            fecha_seguimiento = None
            try:
                visita_examen_analisis = VisitaExamen.objects.filter(
                    visita=visita,
                    examen__nombre__icontains="analisis",
                    estado="completado",
                ).first()
                if visita_examen_analisis:
                    analisis_result = AnalisisGeneralResult.objects.filter(
                        visita_examen=visita_examen_analisis
                    ).first()
                    if analisis_result and analisis_result.fecha_seguimiento:
                        fecha_seguimiento = analisis_result.fecha_seguimiento
            except Exception as e:
                logger.error("Error al buscar fecha de seguimiento: %s", e)

            # Generar PDF con el builder compartido
            buffer = BytesIO()
            construir_pdf_visita(buffer, visita)

            # Construir mensaje del correo
            asunto = f"Historia Clinica - Visita: {visita.nombre}"

            mensaje_cuerpo = (
                f"Estimado(a) {paciente.primer_nombre} {paciente.primer_apellido},\n\n"
                f'La visita "{visita.nombre}" realizada el {visita.fecha} '
                f"ha sido completada y firmada.\n\n"
                f"Adjunto encontrara el PDF con su historia clinica y los "
                f"examenes realizados durante esta visita.\n"
            )

            if fecha_seguimiento:
                mensaje_cuerpo += (
                    f"\nRECORDATORIO DE PROXIMA CITA:\n"
                    f"Su proxima cita de seguimiento esta programada para el "
                    f"{fecha_seguimiento.strftime('%d de %B de %Y')}.\n"
                    f"Por favor, asista puntualmente a su cita.\n"
                )

            mensaje_cuerpo += (
                "\nGracias por confiar en nosotros.\n\n"
                "Atentamente,\nSistema ATENEA\n"
            )

            # Enviar correo
            correo_paciente = paciente.correo

            if correo_paciente:
                email = EmailMessage(
                    asunto,
                    mensaje_cuerpo,
                    settings.EMAIL_HOST_USER,
                    [correo_paciente],
                )
                nombre_archivo = (
                    f"Historia_Clinica_Visita_{visita_id}"
                    f"_{datetime.now().strftime('%Y%m%d')}.pdf"
                )
                email.attach(nombre_archivo, buffer.getvalue(), "application/pdf")
                email.send()

                messages.success(
                    request,
                    f"Visita '{visita.nombre}' firmada y cerrada exitosamente. "
                    f"Se ha enviado un correo a {correo_paciente} con la historia clinica.",
                )
            else:
                messages.warning(
                    request,
                    f"Visita '{visita.nombre}' firmada y cerrada exitosamente. "
                    f"No se pudo enviar el correo porque el paciente no tiene "
                    f"correo electronico registrado.",
                )

        except Exception as e:
            logger.error("Error al enviar correo de visita firmada: %s", e)
            import traceback
            traceback.print_exc()
            messages.warning(
                request,
                f"Visita firmada exitosamente, pero hubo un error al enviar el correo: {e}",
            )

        return redirect("detalle_paciente", paciente_id=paciente_id)

    return redirect("index")


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
        try:
            # Obtener datos del formulario
            visita.nombre = request.POST.get("nombre", visita.nombre)
            visita.fecha = request.POST.get("fecha", visita.fecha)
            # Asignar evaluador correctamente: puede venir como id, email o no enviarse
            evaluador_val = request.POST.get("evaluador", None)
            if evaluador_val:
                try:
                    # intentar como id
                    posible = User.objects.get(id=int(evaluador_val))
                    visita.evaluador = posible
                except (ValueError, TypeError, User.DoesNotExist):
                    try:
                        # intentar buscar por email
                        posible = User.objects.get(email=evaluador_val)
                        visita.evaluador = posible
                    except User.DoesNotExist:
                        # no se encontró: mantener el evaluador previo
                        visita.evaluador = visita.evaluador
            else:
                # Si no se envía evaluador, mantener el existente
                visita.evaluador = visita.evaluador

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

            # Si el frontend envía un único campo con JSON (p. ej. '["1","2"]'), parsearlo
            if len(examenes_seleccionados) == 1:
                single = examenes_seleccionados[0]
                if single and single.strip().startswith("["):
                    try:
                        import json

                        parsed = json.loads(single)
                        # Asegurar que queden como strings simples
                        examenes_seleccionados = [str(x) for x in parsed]
                    except Exception:
                        # Si no es JSON válido, mantener el valor tal cual (fallará más abajo si no válido)
                        pass

            added = 0
            for examen_id in examenes_seleccionados:
                try:
                    examen = Examen.objects.get(id=int(examen_id))  # Convertimos ID a entero
                except (ValueError, Examen.DoesNotExist):
                    continue

                if not VisitaExamen.objects.filter(visita=visita, examen=examen).exists():
                    VisitaExamen.objects.create(visita=visita, examen=examen)
                    added += 1

            if added:
                messages.success(
                    request,
                    f"Visita actualizada con éxito con {added} exámenes.",
                )
            else:
                messages.info(request, "No se agregaron nuevos exámenes.")

            return redirect("detalle_paciente", paciente_id=paciente.id)

        except Exception as e:
            import traceback

            traceback.print_exc()
            messages.error(request, f"Error actualizando visita: {str(e)}")
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


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def visitas_pendientes_firma(request):
    """
    Lista visitas con TODOS los exámenes completados pero pendientes de firma.
    Solo superusuarios.
    """
    from django.db.models import Count, Q

    # Visitas no firmadas que tienen al menos un examen
    visitas_candidatas = (
        Visita.objects.filter(firmado=False)
        .exclude(visita_examenes__isnull=True)
        .annotate(
            total_examenes=Count("visita_examenes"),
            examenes_completados=Count(
                "visita_examenes", filter=Q(visita_examenes__estado="completado")
            ),
        )
        .filter(total_examenes__gt=0, total_examenes=F("examenes_completados"))
        .select_related("paciente", "Tipo_visita", "Tipo_visita__proyecto", "evaluador")
        .order_by("-fecha")
    )

    return render(
        request,
        "home/visitas_pendientes_firma.html",
        {"visitas": visitas_candidatas},
    )


@login_required
def editar_notas_aclaratorias(request, visita_id):
    """
    Update notas_aclaratorias on a visit.
    Allowed even when firmado=True — this is by design so clinicians
    can add post-signature clarifying notes.
    """
    if request.method != "POST":
        messages.error(request, "Método no permitido.")
        return redirect("index")

    visita = get_object_or_404(Visita, id=visita_id)
    visita.notas_aclaratorias = request.POST.get("notas_aclaratorias", "")
    visita.save()
    messages.success(request, "Notas aclaratorias actualizadas correctamente.")
    return redirect("detalle_paciente", paciente_id=visita.paciente.id)


# proyectos ############################################################
