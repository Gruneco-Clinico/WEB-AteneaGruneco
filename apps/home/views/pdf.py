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

def _extraer_informacion_resultado(resultado):
    """
    Extrae información relevante de un resultado de examen dinamicamente
    Itera sobre TODOS los campos del modelo y extrae aquellos con valores
    """
    if not resultado:
        return None
    
    info = []
    
    try:
        # Extraer todos los campos del modelo dinámicamente
        from django.db import models
        
        # Obtener todos los campos del modelo
        fields = resultado._meta.get_fields()
        
        for field in fields:
            # Ignorar campos de relación, campos internos e id
            if isinstance(field, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
                continue
            if field.name.startswith('_') or field.name in ['id', 'created_at', 'updated_at']:
                continue
            
            try:
                valor = getattr(resultado, field.name, None)
                
                # Ignorar valores completamente vacíos o None
                if valor is None or valor == '':
                    continue
                
                # Para booleanos, solo incluir si es True
                if isinstance(valor, bool):
                    if not valor:
                        continue
                    valor_formateado = 'Sí'
                # Para números, incluir aunque sean 0 (pueden ser válidos)
                # pero ignorar si están vacíos
                elif isinstance(valor, (int, float)):
                    if valor == 0:
                        # Incluir 0 solo si es un campo numérico de datos importantes
                        if field.name not in ['id']:
                            valor_formateado = '0'
                        else:
                            continue
                    else:
                        # Formatear floats con un decimal
                        if isinstance(valor, float):
                            valor_formateado = f'{valor:.1f}'
                        else:
                            valor_formateado = str(valor)
                # Formatear datetime
                elif hasattr(valor, 'strftime'):
                    valor_formateado = valor.strftime('%d/%m/%Y')
                # Convertir a string los demás valores
                else:
                    valor_str = str(valor).strip()
                    if not valor_str:
                        continue
                    valor_formateado = valor_str
                
                # Formatear el nombre del campo
                # Usar verbose_name si está disponible, sino convertir snake_case a Title Case
                if hasattr(field, 'verbose_name') and field.verbose_name:
                    nombre_campo = field.verbose_name.capitalize()
                else:
                    nombre_campo = field.name.replace('_', ' ').title()
                
                # Agregar a la lista
                info.append(f"{nombre_campo}: {valor_formateado}")
            
            except Exception as field_error:
                # Continuar con el siguiente campo si hay error
                continue
        
        return "<br/>".join(info) if info else None
    
    except Exception as e:
        logging.error(f"Error extrayendo información de resultado: {str(e)}")
        return None


# GENERACIÓN DE PDF - HISTORIA CLÍNICA POR VISITA ################################
@login_required
def generar_pdf_historia_clinica_visita(request, visita_id):
    """
    Genera un PDF con la historia clínica de una visita específica,
    incluyendo los exámenes realizados
    """
    try:
        visita = get_object_or_404(Visita, id=visita_id)
        paciente = visita.paciente
        
        # Crear el objeto BytesIO para almacenar el PDF
        buffer = BytesIO()
        
        # Crear el documento PDF
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
            ['Nombre Completo:', f"{paciente.primer_nombre} {paciente.segundo_nombre} {paciente.primer_apellido} {paciente.segundo_apellido}"],
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
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (1, 0), 8),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(datos_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # INFORMACIÓN DE LA VISITA
        visita_info = Paragraph(f"<b>Información de la Visita</b>", heading_style)
        elements.append(visita_info)
        
        visita_tabla = [
            ['Fecha de Visita:', visita.fecha.strftime('%d de %B de %Y') if visita.fecha else 'N/A'],
            ['Tipo de Visita:', visita.Tipo_visita.nombre if visita.Tipo_visita else 'N/A'],
            ['Evaluador:', visita.evaluador or 'N/A'],
            ['Proyecto:', visita.Tipo_visita.proyecto.nombre if visita.Tipo_visita and visita.Tipo_visita.proyecto else 'N/A'],
            ['Estado:', 'Firmada' if visita.firmado else 'Abierta'],
        ]
        
        visita_table = Table(visita_tabla, colWidths=[2*inch, 4*inch])
        visita_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(visita_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # EXÁMENES REALIZADOS
        examenes_realizados = visita.visita_examenes.filter(estado='completado')
        
        if examenes_realizados.exists():
            examenes_titulo = Paragraph(f"<b>Exámenes Realizados ({examenes_realizados.count()})</b>", heading_style)
            elements.append(examenes_titulo)
            
            for i, visita_examen in enumerate(examenes_realizados, 1):
                # Obtener el resultado del examen
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
        
    
        
        # Agregar firma guardada del profesional si existe
        if visita.firmado_por:
            try:
                from apps.home.models import UserProfile
                perfil = UserProfile.objects.filter(user=visita.firmado_por).first()
                
                if perfil and perfil.firma:
                    elements.append(Spacer(1, 0.15*inch))
                    
                    # Crear tabla para la firma del profesional
                    tabla_firma_prof = [
                        ['Firma del Profesional:', ''],
                    ]
                    
                    # Si es una imagen en base64
                    if perfil.firma.startswith('data:'):
                        elements.append(Paragraph(
                            f"<b>Firma del Profesional: {visita.firmado_por.get_full_name() or visita.firmado_por.username}</b>",
                            ParagraphStyle('FirmaProf', parent=styles['Normal'], fontSize=9)
                        ))
                        elements.append(Spacer(1, 0.08*inch))
                        # Nota: La firma en base64 se muestra como una imagen
                        # En un PDF real, podrías decodificarla y insertarla con Image
                        elements.append(Paragraph(
                            f"<i>Firma registrada digitalmente</i>",
                            ParagraphStyle('FirmaNota', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
                        ))
                    else:
                        # Es texto
                        elements.append(Paragraph(
                            f"<b>Firma: {perfil.firma}</b>",
                            ParagraphStyle('FirmaProf', parent=styles['Normal'], fontSize=9)
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
        
        # Obtener el contenido del buffer
        buffer.seek(0)
        
        # Crear la respuesta HTTP con el PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Historia_Clinica_Visita_{visita_id}_{datetime.now().strftime("%Y%m%d")}.pdf"'
        
        return response
        
    except Exception as e:
        import traceback
        logging.error(f"Error generando PDF: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, f"Error al generar el PDF: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', 'home'))

