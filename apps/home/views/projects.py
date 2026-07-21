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


def _build_examenes_por_categoria(examenes_qs):
    categorias = dict(Examen.CATEGORIA_CHOICES)
    agrupados = []
    for codigo, nombre in Examen.CATEGORIA_CHOICES:
        exams_cat = list(examenes_qs.filter(categoria=codigo).order_by("nombre"))
        if exams_cat:
            agrupados.append(
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "examenes": exams_cat,
                }
            )
    return agrupados


def _normalizar_examenes_tipo_visita(examenes_data):
    if not isinstance(examenes_data, list):
        return []

    ids = []
    for examen in examenes_data:
        try:
            ids.append(int(examen.get("id")))
        except (TypeError, ValueError, AttributeError):
            continue

    examenes_db = Examen.objects.filter(id__in=ids)
    examenes_map = {e.id: e for e in examenes_db}
    cat_label = dict(Examen.CATEGORIA_CHOICES)

    salida = []
    for examen in examenes_data:
        try:
            eid = int(examen.get("id"))
        except (TypeError, ValueError, AttributeError):
            continue

        exam_db = examenes_map.get(eid)
        categoria_codigo = (
            exam_db.categoria if exam_db else examen.get("categoria", "OTROS")
        )
        salida.append(
            {
                "id": eid,
                "nombre": exam_db.nombre if exam_db else examen.get("nombre", f"Examen {eid}"),
                "categoria": categoria_codigo,
                "categoria_nombre": cat_label.get(categoria_codigo, "Otros"),
            }
        )

    return salida

@login_required
@user_passes_test(is_superuser, login_url="/login/")
def proyectos(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect(
            "index"
        )  # Cambia 'home' por la vista a la que quieras redirigir

    proyectos = Proyecto.objects.all()
    examenes = Examen.objects.all().order_by("categoria", "nombre")
    examenes_por_categoria = _build_examenes_por_categoria(examenes)
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

            examenes_info = _normalizar_examenes_tipo_visita(examenes_data)

            visitas_info.append(
                {
                    "id": visita.id,
                    "nombre": visita.nombre,
                    "observaciones": visita.observaciones,
                    "examenes": examenes_info,
                    "examenes_ids": [e["id"] for e in examenes_info],
                }
            )
        proyecto_data[proyecto.id] = visitas_info

    context = {
        "proyectos": proyectos,
        "examenes": examenes,
        "visitas": visitas,
        "proyecto_data": proyecto_data,
        "examenes_por_categoria": examenes_por_categoria,
    }

    if request.method == "POST":
        proyecto_form = ProyectoForm(request.POST, request.FILES)
        if proyecto_form.is_valid():
            proyecto_form.save()
            messages.success(request, "Proyecto creado correctamente.")

        return redirect("proyectos")

    return render(request, "home/proyectos.html", context)


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def editar_proyecto(request, id):
    proyecto = get_object_or_404(Proyecto, id=id)
    if request.method == "POST":
        form = ProyectoForm(request.POST, request.FILES, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request, f"El proyecto '{proyecto.nombre}' ha sido actualizado correctamente.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        messages.error(request, "Método no permitido.")
    return redirect("proyectos")


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
    examenes = Examen.objects.all().order_by("categoria", "nombre")
    examenes_por_categoria = _build_examenes_por_categoria(examenes)
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

            examenes_info = _normalizar_examenes_tipo_visita(examenes_data)
            visitas_info.append(
                {
                    "id": visita.id,
                    "nombre": visita.nombre,
                    "observaciones": visita.observaciones,
                    "examenes": examenes_info,
                    "examenes_ids": [e["id"] for e in examenes_info],
                }
            )
        proyecto_data[proyecto.id] = visitas_info

    context = {
        "proyectos": proyectos,
        "examenes": examenes,
        "visitas": visitas,
        "proyecto_data": proyecto_data,
        "examenes_por_categoria": examenes_por_categoria,
    }

    if request.method == "POST":
        proyecto_id = request.POST.get("proyecto_id")
        nombres = request.POST.getlist("nombre_visita[]")  # Varias visitas
        observaciones_list = request.POST.getlist("observaciones[]")

        # Recibir el JSON desde el formulario y decodificarlo
        examenes_json = request.POST.get("examenes_json", "[]")
        examenes_lista_raw = json.loads(examenes_json)  # Convertir a lista de diccionarios
        examenes_lista = []
        categorias_validas = {codigo for codigo, _ in Examen.CATEGORIA_CHOICES}
        for examen in examenes_lista_raw:
            categoria = examen.get("categoria", "OTROS")
            if categoria not in categorias_validas:
                categoria = "OTROS"
            examenes_lista.append(
                {
                    "id": examen.get("id"),
                    "nombre": examen.get("nombre"),
                    "categoria": categoria,
                }
            )

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
        examenes_dict = {str(examen.get("id")): examen for examen in examenes_existentes}

        # Agregar los nuevos exámenes seleccionados
        for examen in examenes_seleccionados:
            if str(examen.id) not in examenes_dict:
                examenes_dict[str(examen.id)] = {
                    "id": examen.id,
                    "nombre": examen.nombre,
                    "categoria": examen.categoria,
                }

        # Convertir el diccionario de vuelta a lista
        examenes_actualizados = list(examenes_dict.values())

        # Guardar los exámenes como JSON
        visita.examenes = examenes_actualizados
        visita.save()

        messages.success(request, "Visita actualizada correctamente.")
        return redirect("proyectos")


# ===== EXPORTACIÓN CSV POR PROYECTO =====

import csv

@login_required
@user_passes_test(is_superuser, login_url="/login/")
def exportar_csv_proyecto(request, proyecto_id):
    """
    Exporta un CSV con los datos de pacientes y puntajes de exámenes
    para un proyecto específico.
    GET: Muestra formulario de selección de campos
    POST: Genera CSV con campos seleccionados
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    # Si es GET, mostrar formulario de selección
    if request.method == "GET":
        # Definir campos demográficos disponibles
        campos_demograficos = [
            ("numero_documento", "Número de Documento"),
            ("tipo_documento", "Tipo de Documento"),
            ("celular", "Celular"),
            ("fecha_nacimiento", "Fecha de Nacimiento"),
            ("edad", "Edad"),
            ("genero", "Género"),
            ("municipio_nacimiento", "Municipio de Nacimiento"),
            ("departamento_nacimiento", "Departamento de Nacimiento"),
            ("pais_nacimiento", "País de Nacimiento"),
            ("estado_civil", "Estado Civil"),
            ("escolaridad", "Escolaridad"),
            ("ocupacion", "Ocupación"),
            ("lateralidad", "Lateralidad"),
            ("grupo_sanguineo", "Grupo Sanguíneo"),
            ("religion", "Religión"),
            ("eps", "EPS"),
            ("regimen", "Régimen"),
            ("direccion", "Dirección"),
            ("municipio_residencia", "Municipio de Residencia"),
            ("departamento_residencia", "Departamento de Residencia"),
            ("pais_residencia", "País de Residencia"),
            ("correo", "Correo Electrónico"),
        ]

        # Obtener exámenes del proyecto
        examenes_proyecto = []
        visitas = Visita.objects.filter(Tipo_visita__proyecto=proyecto)
        examenes_ids = set()
        for visita in visitas:
            for ve in visita.visita_examenes.all():
                examenes_ids.add(ve.examen.id)
        
        examenes_proyecto = Examen.objects.filter(id__in=examenes_ids).order_by("nombre")

        context = {
            "proyecto": proyecto,
            "campos_demograficos": campos_demograficos,
            "examenes_proyecto": examenes_proyecto,
        }
        return render(request, "home/exportar_proyecto_form.html", context)

    # Si es POST, generar CSV con campos seleccionados
    demograficos_selected = request.POST.getlist("demograficos")
    campos_examen_selected = request.POST.getlist("campos_examen")
    examenes_selected = request.POST.getlist("examenes")

    # Obtener visitas del proyecto
    visitas = Visita.objects.filter(
        Tipo_visita__proyecto=proyecto
    ).select_related(
        "paciente", "Tipo_visita"
    ).prefetch_related(
        "visita_examenes__examen"
    ).order_by("paciente__primer_apellido", "fecha")

    if not visitas.exists():
        messages.warning(request, "No hay visitas registradas en este proyecto.")
        return redirect("proyectos")

    # Obtener exámenes a incluir
    examenes_incluir = []
    if examenes_selected:
        examenes_incluir = Examen.objects.filter(id__in=examenes_selected).order_by("nombre")
    else:
        # Si no se seleccionó ninguno, incluir todos
        examenes_unicos = set()
        for visita in visitas:
            for ve in visita.visita_examenes.all():
                examenes_unicos.add(ve.examen.nombre)
        examenes_incluir = sorted(examenes_unicos)

    # Obtener códigos de proyecto para los pacientes
    codigos = {}
    for extra in ProyectoPacienteExtra.objects.filter(proyecto=proyecto):
        codigos[extra.paciente_id] = extra.codigo_proyecto

    # Crear respuesta CSV
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="Proyecto_{proyecto.nombre}_{datetime.now().strftime("%Y%m%d")}.csv"'
    )
    response.write("\ufeff")  # BOM para Excel

    writer = csv.writer(response, delimiter=";")

    # Construir encabezados dinámicamente
    headers = [
        "Código Proyecto",
        "Paciente",
        "Tipo de Visita",
        "Fecha Visita",
        "Estado Visita",
    ]

    # Mapeo de nombres técnicos a nombres legibles
    campo_labels = {
        "numero_documento": "Documento",
        "tipo_documento": "Tipo Documento",
        "celular": "Celular",
        "fecha_nacimiento": "Fecha Nacimiento",
        "edad": "Edad",
        "genero": "Género",
        "municipio_nacimiento": "Municipio Nacimiento",
        "departamento_nacimiento": "Departamento Nacimiento",
        "pais_nacimiento": "País Nacimiento",
        "estado_civil": "Estado Civil",
        "escolaridad": "Escolaridad",
        "ocupacion": "Ocupación",
        "lateralidad": "Lateralidad",
        "grupo_sanguineo": "Grupo Sanguíneo",
        "religion": "Religión",
        "eps": "EPS",
        "regimen": "Régimen",
        "direccion": "Dirección",
        "municipio_residencia": "Municipio Residencia",
        "departamento_residencia": "Departamento Residencia",
        "pais_residencia": "País Residencia",
        "correo": "Correo",
    }

    # Agregar campos demográficos seleccionados
    for campo in demograficos_selected:
        headers.append(campo_labels.get(campo, campo))

    # Agregar columnas de exámenes según campos seleccionados
    campo_examen_labels = {
        "motivo_consulta": "Motivo Consulta",
        "puntaje_total": "Puntaje",
        "suma_cajas": "Suma de cajas",
        "cdr_global": "CDR Global",
        "puntaje_autocuidado": "RedLat Autocuidado",
        "puntaje_cuidado_hogar": "RedLat Cuidado hogar",
        "puntaje_trabajo_recreacion": "RedLat Trabajo/recreación",
        "puntaje_compras_dinero": "RedLat Compras/dinero",
        "puntaje_viajes": "RedLat Viajes",
        "puntaje_comunicacion": "RedLat Comunicación",
        "puntaje_tecnologia": "RedLat Tecnología",
        "interpretacion": "Interpretación",
        "observaciones": "Observaciones",
        "notas_aclaratorias": "Notas",
    }

    if isinstance(examenes_incluir, list):
        # Si examenes_incluir es lista de strings (nombres)
        for examen_nombre in examenes_incluir:
            for campo_exam in campos_examen_selected:
                label = campo_examen_labels.get(campo_exam, campo_exam)
                headers.append(f"{examen_nombre} - {label}")
    else:
        # Si examenes_incluir es queryset de objetos Examen
        for examen in examenes_incluir:
            for campo_exam in campos_examen_selected:
                label = campo_examen_labels.get(campo_exam, campo_exam)
                headers.append(f"{examen.nombre} - {label}")

    writer.writerow(headers)

    # Escribir filas de datos
    examenes_nombres = []
    if isinstance(examenes_incluir, list):
        examenes_nombres = examenes_incluir
    else:
        examenes_nombres = [e.nombre for e in examenes_incluir]

    for visita in visitas:
        paciente = visita.paciente
        if not paciente:
            continue

        codigo = codigos.get(paciente.id, "")
        nombre_paciente = f"{paciente.primer_nombre} {paciente.primer_apellido}"

        tipo_visita = visita.Tipo_visita.nombre if visita.Tipo_visita else ""
        fecha = visita.fecha.strftime("%d/%m/%Y") if visita.fecha else ""
        estado = "Firmada" if visita.firmado else "Abierta"

        # Construir fila base
        row = [
            codigo,
            nombre_paciente,
            tipo_visita,
            fecha,
            estado,
        ]

        # Agregar campos demográficos seleccionados
        for campo in demograficos_selected:
            valor = getattr(paciente, campo, "")
            if campo == "fecha_nacimiento" and valor:
                valor = valor.strftime("%d/%m/%Y")
            elif campo == "tipo_documento":
                valor = paciente.get_tipo_documento_display() if hasattr(paciente, 'get_tipo_documento_display') else valor
            elif campo == "genero":
                valor = paciente.get_genero_display() if hasattr(paciente, 'get_genero_display') else valor
            elif campo == "estado_civil":
                valor = paciente.get_estado_civil_display() if hasattr(paciente, 'get_estado_civil_display') else valor
            elif campo == "escolaridad":
                valor = paciente.get_escolaridad_display() if hasattr(paciente, 'get_escolaridad_display') else valor
            elif campo == "lateralidad":
                valor = paciente.get_lateralidad_display() if hasattr(paciente, 'get_lateralidad_display') else valor
            elif campo == "regimen":
                valor = paciente.get_regimen_display() if hasattr(paciente, 'get_regimen_display') else valor
            row.append(valor if valor else "")

        # Obtener datos de exámenes
        examenes_data = {}
        for ve in visita.visita_examenes.all():
            if ve.examen.nombre not in examenes_nombres:
                continue
            
            datos = {}
            if ve.estado == "completado":
                try:
                    resultado = ve.get_resultado_instance()
                    if resultado:
                        for campo in campos_examen_selected:
                            if campo == "puntaje_total":
                                valor = getattr(resultado, "puntaje_total", None)
                                if valor is None:
                                    valor = getattr(resultado, "puntuacion_total", None)
                                if valor is None:
                                    valor = getattr(resultado, "puntuacion", None)
                            else:
                                valor = getattr(resultado, campo, None)
                            datos[campo] = valor if valor is not None else ""
                except Exception:
                    pass
            
            examenes_data[ve.examen.nombre] = datos

        # Agregar columnas de exámenes
        for examen_nombre in examenes_nombres:
            datos = examenes_data.get(examen_nombre, {})
            for campo_exam in campos_examen_selected:
                row.append(datos.get(campo_exam, ""))

        writer.writerow(row)

    return response


# exámenes #######################
