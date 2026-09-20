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
    Exporta un CSV con datos demográficos y campos seleccionados por examen (C-15).
    GET: formulario con catálogo tipado por examen.
    POST: genera CSV con selección namespaced `campos_examen_<id>`.
    """
    from apps.home.services.project_csv_export import (
        DEMOGRAPHIC_FIELDS,
        build_csv_headers,
        build_exam_export_catalog,
        extract_exam_value,
        parse_export_selection,
        serialize_demographic_value,
    )

    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    visitas_base = Visita.objects.filter(Tipo_visita__proyecto=proyecto).exclude(
        estado_visita="programada"
    )
    examenes_ids = (
        VisitaExamen.objects.filter(visita__Tipo_visita__proyecto=proyecto)
        .values_list("examen_id", flat=True)
        .distinct()
    )
    examenes_proyecto = Examen.objects.filter(id__in=examenes_ids).order_by("nombre")
    exam_catalog = build_exam_export_catalog(examenes_proyecto)

    if request.method == "GET":
        context = {
            "proyecto": proyecto,
            "campos_demograficos": DEMOGRAPHIC_FIELDS,
            "exam_catalog": exam_catalog,
            "examenes_proyecto": examenes_proyecto,
        }
        return render(request, "home/exportar_proyecto_form.html", context)

    demograficos_selected = request.POST.getlist("demograficos")
    selection = parse_export_selection(request.POST, exam_catalog)

    visitas = (
        visitas_base.select_related("paciente", "Tipo_visita")
        .prefetch_related("visita_examenes__examen")
        .order_by("paciente__primer_apellido", "fecha")
    )

    if not visitas.exists():
        messages.warning(request, "No hay visitas registradas en este proyecto.")
        return redirect("proyectos")

    codigos = {
        extra.paciente_id: extra.codigo_proyecto
        for extra in ProyectoPacienteExtra.objects.filter(proyecto=proyecto)
    }

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="Proyecto_{proyecto.nombre}_{datetime.now().strftime("%Y%m%d")}.csv"'
    )
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")
    headers = build_csv_headers(demograficos_selected, selection, exam_catalog)
    writer.writerow(headers)

    # Orden estable de columnas de examen = orden de selection.items() (Python 3.7+)
    exam_column_order = list(selection.items())

    for visita in visitas:
        paciente = visita.paciente
        if not paciente:
            continue

        codigo = codigos.get(paciente.id, "")
        nombre_paciente = f"{paciente.primer_nombre} {paciente.primer_apellido}"
        tipo_visita = visita.Tipo_visita.nombre if visita.Tipo_visita else ""
        fecha = visita.fecha.strftime("%d/%m/%Y") if visita.fecha else ""
        estado = "Firmada" if visita.firmado else "Abierta"

        row = [codigo, nombre_paciente, tipo_visita, fecha, estado]
        for campo in demograficos_selected:
            row.append(serialize_demographic_value(paciente, campo))

        ve_by_exam = {ve.examen_id: ve for ve in visita.visita_examenes.all()}
        for exam_id, fields in exam_column_order:
            ve = ve_by_exam.get(exam_id)
            for spec in fields:
                if ve is None or ve.estado != "completado":
                    row.append("")
                else:
                    row.append(extract_exam_value(ve, spec))

        writer.writerow(row)

    return response


# exámenes #######################
