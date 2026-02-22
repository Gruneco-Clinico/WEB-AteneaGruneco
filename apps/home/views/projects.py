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
def editar_proyecto(request, id):
    proyecto = get_object_or_404(Proyecto, id=id)
    if request.method == "POST":
        form = ProyectoForm(request.POST, instance=proyecto)
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


# ===== EXPORTACIÓN CSV POR PROYECTO =====

import csv

@login_required
@user_passes_test(is_superuser, login_url="/login/")
def exportar_csv_proyecto(request, proyecto_id):
    """
    Exporta un CSV con los datos de pacientes y puntajes de exámenes
    para un proyecto específico.
    Columnas: Código Proyecto, Paciente, Edad, Tipo Visita, Fecha Visita,
              y una columna por cada examen con su puntaje_total.
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

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

    # Recopilar todos los nombres de exámenes únicos del proyecto
    examenes_unicos = set()
    for visita in visitas:
        for ve in visita.visita_examenes.all():
            examenes_unicos.add(ve.examen.nombre)
    examenes_ordenados = sorted(examenes_unicos)

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

    # Encabezados
    headers = [
        "Código Proyecto",
        "Paciente",
        "Documento",
        "Edad",
        "Tipo de Visita",
        "Fecha Visita",
        "Estado Visita",
    ]
    for examen_nombre in examenes_ordenados:
        headers.append(f"Puntaje - {examen_nombre}")
    writer.writerow(headers)

    # Fila por cada visita
    for visita in visitas:
        paciente = visita.paciente
        if not paciente:
            continue

        codigo = codigos.get(paciente.id, "")
        nombre_paciente = (
            f"{paciente.primer_nombre} {paciente.primer_apellido}"
        )
        edad = getattr(paciente, "edad", "")

        tipo_visita = visita.Tipo_visita.nombre if visita.Tipo_visita else ""
        fecha = visita.fecha.strftime("%d/%m/%Y") if visita.fecha else ""
        estado = "Firmada" if visita.firmado else "Abierta"

        # Obtener puntajes por examen
        puntajes = {}
        for ve in visita.visita_examenes.all():
            puntaje = ""
            if ve.estado == "completado":
                try:
                    resultado = ve.get_resultado_instance()
                    if resultado and hasattr(resultado, "puntaje_total"):
                        puntaje = resultado.puntaje_total
                        if puntaje is None:
                            puntaje = ""
                except Exception:
                    pass
            puntajes[ve.examen.nombre] = puntaje

        row = [
            codigo,
            nombre_paciente,
            paciente.numero_documento,
            edad,
            tipo_visita,
            fecha,
            estado,
        ]
        for examen_nombre in examenes_ordenados:
            row.append(puntajes.get(examen_nombre, ""))

        writer.writerow(row)

    return response


# exámenes #######################
