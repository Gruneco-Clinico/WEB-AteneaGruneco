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
from .auth import is_superuser

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
    Además, envía un correo al paciente con el PDF de la historia clínica
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
                # Buscar el examen de análisis (ID = 7)
                visita_examen_analisis = VisitaExamen.objects.filter(
                    visita=visita,
                    examen_id=7,
                    estado='completado'
                ).first()
                
                if visita_examen_analisis:
                    analisis_result = AnalisisGeneralResult.objects.filter(
                        visita_examen=visita_examen_analisis
                    ).first()
                    
                    if analisis_result and analisis_result.fecha_seguimiento:
                        fecha_seguimiento = analisis_result.fecha_seguimiento
            except Exception as e:
                logging.error(f"Error al buscar fecha de seguimiento: {str(e)}")
            
            # Generar PDF en memoria
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )
            
            # Lista de elementos para el PDF
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#0d5e3a'),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#0d5e3a'),
                spaceAfter=8,
                spaceBefore=12,
                fontName='Helvetica-Bold',
                borderPadding=5,
                backColor=colors.HexColor('#e8f5e9')
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_JUSTIFY,
                spaceAfter=6
            )
            
            # TÍTULO DEL DOCUMENTO
            titulo = Paragraph("HISTORIA CLÍNICA", title_style)
            elements.append(titulo)
            elements.append(Spacer(1, 0.1*inch))
            
            # INFORMACIÓN DEL PACIENTE Y VISITA
            datos_tabla = [
                ['DATOS DEL PACIENTE', ''],
                ['Nombre Completo:', f"{paciente.primer_nombre} {paciente.segundo_nombre or ''} {paciente.primer_apellido} {paciente.segundo_apellido or ''}"],
                ['Tipo de Documento:', paciente.tipo_documento],
                ['Número de Documento:', str(paciente.numero_documento)],
                ['Edad:', str(paciente.edad)],
                ['Fecha de Nacimiento:', str(paciente.fecha_nacimiento)],
                ['EPS:', paciente.eps or 'N/A'],
                ['Teléfono:', paciente.celular or 'N/A'],
            ]
            
            datos_table = Table(datos_tabla, colWidths=[2*inch, 4*inch])
            datos_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#0d5e3a')),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e8f5e9')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#0d5e3a')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(datos_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # INFORMACIÓN DE LA VISITA
            visita_tabla = [
                ['INFORMACIÓN DE LA VISITA', ''],
                ['Nombre de Visita:', visita.nombre],
                ['Tipo de Visita:', visita.Tipo_visita.nombre if visita.Tipo_visita else 'N/A'],
                ['Fecha:', str(visita.fecha)],
                ['Evaluador:', visita.evaluador.get_full_name() if visita.evaluador else 'N/A'],
            ]
            
            # Agregar información del acompañante si existe
            if visita.acompanante_nombre:
                visita_tabla.extend([
                    ['Acompañante:', visita.acompanante_nombre],
                    ['Relación:', visita.acompanante_relacion or 'N/A'],
                ])
            
            visita_table = Table(visita_tabla, colWidths=[2*inch, 4*inch])
            visita_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#0d5e3a')),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e8f5e9')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#0d5e3a')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(visita_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # EXÁMENES REALIZADOS
            examenes_realizados = visita.visita_examenes.filter(estado='completado')
            
            if examenes_realizados.exists():
                examenes_titulo = Paragraph(f"<b>EXÁMENES REALIZADOS ({examenes_realizados.count()})</b>", heading_style)
                elements.append(examenes_titulo)
                elements.append(Spacer(1, 0.1*inch))
                
                for i, visita_examen in enumerate(examenes_realizados, 1):
                    # Obtener el resultado del examen usando el método del modelo
                    resultado = visita_examen.get_resultado_instance()
                    
                    examen_info = f"<b>{i}. {visita_examen.examen.nombre}</b>"
                    if visita_examen.fecha_completado:
                        examen_info += f"<br/>Completado: {visita_examen.fecha_completado.strftime('%d/%m/%Y %H:%M')}"
                    
                    elements.append(Paragraph(examen_info, normal_style))
                    
                    # Extraer información del resultado si existe
                    if resultado:
                        info_resultado = _extraer_informacion_resultado(resultado)
                        if info_resultado:
                            elementos_info = Paragraph(info_resultado, ParagraphStyle(
                                'ResultadoInfo',
                                parent=styles['Normal'],
                                fontSize=9,
                                leftIndent=0.25*inch,
                                textColor=colors.HexColor('#333333'),
                                spaceAfter=4
                            ))
                            elements.append(elementos_info)
                    
                    if visita_examen.notas_examinador:
                        notas = Paragraph(
                            f"<i>Notas: {visita_examen.notas_examinador}</i>",
                            ParagraphStyle(
                                'Notas',
                                parent=styles['Normal'],
                                fontSize=9,
                                leftIndent=0.25*inch,
                                textColor=colors.HexColor('#666666'),
                                spaceAfter=4
                            )
                        )
                        elements.append(notas)
                    
                    elements.append(Spacer(1, 0.08*inch))
            else:
                examenes_titulo = Paragraph(f"<b>EXÁMENES REALIZADOS</b>", heading_style)
                elements.append(examenes_titulo)
                elements.append(Spacer(1, 0.1*inch))
                elements.append(Paragraph("No hay exámenes completados en esta visita.", normal_style))
                elements.append(Spacer(1, 0.1*inch))
            
            
            
            # Agregar firma guardada del profesional si existe
            if visita.firmado_por:
                try:
                    from apps.home.models import UserProfile
                    perfil = UserProfile.objects.filter(user=visita.firmado_por).first()
                    
                    if perfil and perfil.firma:
                        elements.append(Spacer(1, 0.15*inch))
                        elements.append(Paragraph(
                            f"<b>Firma de: {visita.firmado_por.get_full_name() or visita.firmado_por.username}</b>",
                            ParagraphStyle('FirmaProf', parent=styles['Normal'], fontSize=9)
                        ))
                        elements.append(Spacer(1, 0.08*inch))
                        elements.append(Paragraph(
                            f"<i>Firma registrada digitalmente</i>",
                            ParagraphStyle('FirmaNota', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
                        ))
                except Exception as e:
                    logging.error(f"Error al procesar firma del profesional: {str(e)}")
            
            elements.append(Spacer(1, 0.1*inch))
            
            # PIE DE PÁGINA
            pie = Paragraph(
                f"<i>Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</i>",
                ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
            )
            elements.append(pie)
            
            # Construir el PDF
            doc.build(elements)
            buffer.seek(0)
            
            # Construir mensaje del correo
            asunto = f"Historia Clínica - Visita: {visita.nombre}"
            
            mensaje_cuerpo = f"""
Estimado(a) {paciente.primer_nombre} {paciente.primer_apellido},

La visita "{visita.nombre}" realizada el {visita.fecha} ha sido completada y firmada.

Adjunto encontrará el PDF con su historia clínica y los exámenes realizados durante esta visita.
"""
            
            # Agregar recordatorio de próxima cita si existe fecha de seguimiento
            if fecha_seguimiento:
                mensaje_cuerpo += f"""
📅 RECORDATORIO DE PRÓXIMA CITA:
Su próxima cita de seguimiento está programada para el {fecha_seguimiento.strftime('%d de %B de %Y')}.
Por favor, asista puntualmente a su cita.
"""
            
            mensaje_cuerpo += """

Gracias por confiar en nosotros.

Atentamente,
Sistema ATENEA
"""
            
            # Enviar correo
            correo_paciente = paciente.correo
            
            if correo_paciente:
                email = EmailMessage(
                    asunto,
                    mensaje_cuerpo,
                    settings.EMAIL_HOST_USER,
                    [correo_paciente],
                )
                
                # Adjuntar PDF
                nombre_archivo = f"Historia_Clinica_Visita_{visita_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
                email.attach(nombre_archivo, buffer.getvalue(), 'application/pdf')
                
                email.send()
                
                messages.success(
                    request, 
                    f"Visita '{visita.nombre}' firmada y cerrada exitosamente. Se ha enviado un correo a {correo_paciente} con la historia clínica."
                )
            else:
                messages.warning(
                    request,
                    f"Visita '{visita.nombre}' firmada y cerrada exitosamente. No se pudo enviar el correo porque el paciente no tiene correo electrónico registrado."
                )
                
        except Exception as e:
            logging.error(f"Error al enviar correo de visita firmada: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.warning(
                request,
                f"Visita firmada exitosamente, pero hubo un error al enviar el correo: {str(e)}"
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


# proyectos ############################################################
