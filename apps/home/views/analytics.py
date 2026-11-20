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
from django.db.models import Max, Count, Q, Avg, F
from datetime import datetime, timedelta
from ..models import *
from ..forms import ProyectoForm, RegistroDemograficoForm
from ..services import recuerdame_analytics, recuerdame_anosognosia_cruce
import csv
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

from .auth import is_superuser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RANGOS_EDAD = [
    (18, 30, "18-30"),
    (31, 45, "31-45"),
    (46, 60, "46-60"),
    (61, 200, "60+"),
]


def _build_project_stats(proyecto, genero=None, edad_min=None, edad_max=None):
    """Return a dict with participant & exam stats for one Proyecto, applying
    optional gender / age filters."""
    patients = DatosDemograficos.objects.filter(proyectos=proyecto)

    if genero:
        patients = patients.filter(genero__iexact=genero)
    if edad_min is not None:
        patients = patients.filter(edad__gte=edad_min)
    if edad_max is not None:
        patients = patients.filter(edad__lte=edad_max)

    total = patients.count()

    # Gender distribution
    hombres = patients.filter(genero__iexact="M").count()
    mujeres = patients.filter(genero__iexact="F").count()
    otros = patients.filter(genero__iexact="O").count()

    # Age distribution
    age_dist = []
    for lo, hi, label in RANGOS_EDAD:
        c = patients.filter(edad__gte=lo, edad__lte=hi).count()
        age_dist.append({"rango": label, "count": c})

    # Escolaridad
    esc_dist = []
    for nivel, _ in DatosDemograficos.ESCOLARIDAD_CHOICES:
        c = patients.filter(escolaridad__iexact=nivel).count()
        esc_dist.append({"nivel": nivel, "count": c})

    # Exams completed
    exams_completed = VisitaExamen.objects.filter(
        visita__Tipo_visita__proyecto=proyecto,
        estado="completado",
    ).count()

    return {
        "proyecto_id": proyecto.id,
        "proyecto_nombre": proyecto.nombre,
        "participantes": total,
        "exams_completed": exams_completed,
        "genero": {"M": hombres, "F": mujeres, "O": otros},
        "edad": age_dist,
        "escolaridad": esc_dist,
    }


def _build_evaluator_stats(proyecto):
    """Return a list of evaluator dicts for one Proyecto."""
    visitas = Visita.objects.filter(
        Tipo_visita__proyecto=proyecto,
        evaluador__isnull=False,
    ).exclude(estado_visita="programada")

    evaluadores = (
        visitas.values("evaluador__id", "evaluador__first_name", "evaluador__last_name", "evaluador__username")
        .annotate(
            num_pacientes=Count("paciente", distinct=True),
            num_consultas=Count("id"),
            exams_completados=Count(
                "visita_examenes",
                filter=Q(visita_examenes__estado="completado"),
            ),
        )
        .order_by("-num_consultas")
    )

    result = []
    for ev in evaluadores:
        nombre = f"{ev['evaluador__first_name']} {ev['evaluador__last_name']}".strip()
        if not nombre:
            nombre = ev["evaluador__username"]
        result.append({
            "id": ev["evaluador__id"],
            "nombre": nombre,
            "num_pacientes": ev["num_pacientes"],
            "num_consultas": ev["num_consultas"],
            "exams_completados": ev["exams_completados"],
        })

    return result


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def api_dashboard_data(request):
    """JSON endpoint that returns all dashboard KPIs, demographics, and exam
    statistics in a single request for the Chart.js-powered dashboard."""

    proyecto_id = request.GET.get("proyecto")

    # Base patient queryset
    pacientes = DatosDemograficos.objects.all()
    exams_qs = VisitaExamen.objects.filter(estado="completado")

    if proyecto_id:
        try:
            proyecto_id = int(proyecto_id)
            pacientes = pacientes.filter(proyectos__id=proyecto_id)
            exams_qs = exams_qs.filter(visita__Tipo_visita__proyecto_id=proyecto_id)
        except (ValueError, TypeError):
            pass

    # --- KPIs ---
    total_participantes = pacientes.count()
    edad_promedio = pacientes.aggregate(avg=Avg("edad"))["avg"] or 0
    total_examenes = exams_qs.count()

    # --- Gender distribution ---
    genero_data = (
        pacientes.values("genero")
        .annotate(count=Count("id"))
        .order_by("genero")
    )
    genero_labels = []
    genero_values = []
    GENERO_MAP = {"F": "Femenino", "M": "Masculino", "O": "Otro"}
    for item in genero_data:
        g = item["genero"] or "Sin dato"
        genero_labels.append(GENERO_MAP.get(g, g))
        genero_values.append(item["count"])

    # --- Escolaridad ---
    esc_data = (
        pacientes.exclude(escolaridad__isnull=True)
        .exclude(escolaridad__exact="")
        .values("escolaridad")
        .annotate(count=Count("id"))
        .order_by("escolaridad")
    )
    esc_labels = []
    esc_values = []
    for item in esc_data:
        esc_labels.append(item["escolaridad"].capitalize())
        esc_values.append(item["count"])

    # --- Age distribution (histogram buckets) ---
    edad_labels = []
    edad_values = []
    for lo, hi, label in RANGOS_EDAD:
        c = pacientes.filter(edad__gte=lo, edad__lte=hi).count()
        edad_labels.append(label)
        edad_values.append(c)

    # --- Estado civil ---
    ecivil_data = (
        pacientes.exclude(estado_civil__exact="")
        .values("estado_civil")
        .annotate(count=Count("id"))
        .order_by("estado_civil")
    )
    ecivil_labels = [item["estado_civil"] for item in ecivil_data]
    ecivil_values = [item["count"] for item in ecivil_data]

    # --- Grupo sanguíneo ---
    gs_data = (
        pacientes.exclude(grupo_sanguineo__isnull=True)
        .exclude(grupo_sanguineo__exact="")
        .values("grupo_sanguineo")
        .annotate(count=Count("id"))
        .order_by("grupo_sanguineo")
    )
    gs_labels = [item["grupo_sanguineo"] for item in gs_data]
    gs_values = [item["count"] for item in gs_data]

    # --- Exams by project ---
    exams_por_proyecto = (
        VisitaExamen.objects.filter(estado="completado")
        .values(nombre_proyecto=F("visita__Tipo_visita__proyecto__nombre"))
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    ep_labels = [item["nombre_proyecto"] or "Sin proyecto" for item in exams_por_proyecto]
    ep_values = [item["count"] for item in exams_por_proyecto]

    # --- Exams by visit type ---
    exams_por_tipo = (
        exams_qs
        .values(nombre_tipo=F("visita__Tipo_visita__nombre"))
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    et_labels = [item["nombre_tipo"] or "Sin tipo" for item in exams_por_tipo]
    et_values = [item["count"] for item in exams_por_tipo]

    return JsonResponse({
        "kpis": {
            "total_participantes": total_participantes,
            "edad_promedio": round(edad_promedio, 1),
            "total_examenes": total_examenes,
        },
        "genero": {"labels": genero_labels, "values": genero_values},
        "escolaridad": {"labels": esc_labels, "values": esc_values},
        "edad": {"labels": edad_labels, "values": edad_values},
        "estado_civil": {"labels": ecivil_labels, "values": ecivil_values},
        "grupo_sanguineo": {"labels": gs_labels, "values": gs_values},
        "examenes_por_proyecto": {"labels": ep_labels, "values": ep_values},
        "examenes_por_tipo_visita": {"labels": et_labels, "values": et_values},
    })


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def atenea_estadisticas(request):
    """Página principal de estadísticas con filtros dinámicos por proyecto."""
    proyectos = Proyecto.objects.all().order_by("nombre")

    # Obtener filtros de query params (para carga inicial con filtro)
    proyecto_id = request.GET.get("proyecto")
    genero = request.GET.get("genero")
    edad_min = request.GET.get("edad_min")
    edad_max = request.GET.get("edad_max")

    try:
        edad_min = int(edad_min) if edad_min else None
    except (ValueError, TypeError):
        edad_min = None
    try:
        edad_max = int(edad_max) if edad_max else None
    except (ValueError, TypeError):
        edad_max = None

    proyectos_info = []
    if proyecto_id:
        # Solo el proyecto seleccionado
        try:
            proy = Proyecto.objects.get(id=int(proyecto_id))
            proyectos_info.append(_build_project_stats(proy, genero, edad_min, edad_max))
        except Proyecto.DoesNotExist:
            pass
    else:
        # Todos los proyectos
        for proy in proyectos:
            proyectos_info.append(_build_project_stats(proy, genero, edad_min, edad_max))

    context = {
        "segment": "atenea_estadisticas",
        "proyectos": proyectos,
        "proyectos_info": proyectos_info,
        "filtro_proyecto": proyecto_id or "",
        "filtro_genero": genero or "",
        "filtro_edad_min": edad_min or "",
        "filtro_edad_max": edad_max or "",
    }
    return render(request, "home/statistics_atenea.html", context)


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def api_estadisticas_proyecto(request):
    """JSON API for AJAX-driven project stats filtering."""
    proyecto_id = request.GET.get("proyecto")
    genero = request.GET.get("genero")
    edad_min = request.GET.get("edad_min")
    edad_max = request.GET.get("edad_max")

    try:
        edad_min = int(edad_min) if edad_min else None
    except (ValueError, TypeError):
        edad_min = None
    try:
        edad_max = int(edad_max) if edad_max else None
    except (ValueError, TypeError):
        edad_max = None

    if proyecto_id:
        try:
            proy = Proyecto.objects.get(id=int(proyecto_id))
            data = [_build_project_stats(proy, genero, edad_min, edad_max)]
        except Proyecto.DoesNotExist:
            data = []
    else:
        data = [
            _build_project_stats(p, genero, edad_min, edad_max)
            for p in Proyecto.objects.all().order_by("nombre")
        ]

    return JsonResponse({"proyectos": data}, safe=False)


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def api_estadisticas_evaluadores(request):
    """JSON API for evaluator stats per project."""
    proyecto_id = request.GET.get("proyecto")

    if proyecto_id:
        try:
            proy = Proyecto.objects.get(id=int(proyecto_id))
            data = [{
                "proyecto_id": proy.id,
                "proyecto_nombre": proy.nombre,
                "evaluadores": _build_evaluator_stats(proy),
            }]
        except Proyecto.DoesNotExist:
            data = []
    else:
        data = []
        for proy in Proyecto.objects.all().order_by("nombre"):
            evals = _build_evaluator_stats(proy)
            if evals:
                data.append({
                    "proyecto_id": proy.id,
                    "proyecto_nombre": proy.nombre,
                    "evaluadores": evals,
                })

    return JsonResponse({"proyectos": data}, safe=False)


# pacientes
@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def estadisticas(request):
    """Dashboard de biomarcadores digitales de RecuérdaMe (endpoint de cohorte)."""
    dias = recuerdame_analytics.normalizar_dias(request.GET.get("dias"))
    date_from, date_to = recuerdame_analytics.rango_fechas(dias)

    cohorte = None
    error = None
    try:
        cohorte = recuerdame_analytics.obtener_cohorte(date_from, date_to)
    except recuerdame_analytics.RecuerdameAnalyticsError as exc:
        error = str(exc)

    cruce = None
    try:
        cruce = recuerdame_anosognosia_cruce.construir_cruce()
    except Exception:
        logger.exception("Error al construir el cruce Anosognosia × RecuérdaMe")
        cruce = None

    return render(
        request,
        "home/statistics_recuerdame.html",
        {
            "segment": "estadisticas",
            "cohorte": cohorte,
            "error": error,
            "dias": dias,
            "rangos": recuerdame_analytics.RANGOS_DIAS,
            "date_from": date_from,
            "date_to": date_to,
            "cruce": cruce,
        },
    )


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def estadisticas_biomarcadores_csv(request):
    """Descarga UN CSV con el biomarcador de todas las personas del periodo."""
    dias = recuerdame_analytics.normalizar_dias(request.GET.get("dias"))
    date_from, date_to = recuerdame_analytics.rango_fechas(dias)

    try:
        usuarios = recuerdame_analytics.obtener_usuarios(date_from, date_to)
    except recuerdame_analytics.RecuerdameAnalyticsError as exc:
        messages.error(request, str(exc))
        return redirect("estadisticas")

    encabezados, filas = recuerdame_analytics.construir_tabla_csv(usuarios)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="Recuerdame_biomarcadores_{datetime.now().strftime("%Y%m%d")}.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(encabezados)
    writer.writerows(filas)
    return response


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def estadisticas_anosognosia_cruce_csv(request):
    """Un CSV con todas las sesiones Anosognosia (examen 56) enriquecidas con PostHog."""
    try:
        cruce = recuerdame_anosognosia_cruce.construir_cruce()
    except Exception:
        logger.exception("Error al exportar el cruce Anosognosia × RecuérdaMe")
        messages.error(
            request,
            "No fue posible generar el cruce Anosognosia × RecuérdaMe.",
        )
        return redirect("estadisticas")

    if cruce.get("error_posthog"):
        messages.warning(request, cruce["error_posthog"])

    encabezados, filas = recuerdame_anosognosia_cruce.construir_tabla_csv(cruce)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="Anosognosia_Recuerdame_cruce_'
        f'{datetime.now().strftime("%Y%m%d")}.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(encabezados)
    writer.writerows(filas)
    return response


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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        # Ejecutar query
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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
    """Biomarcadores de una persona: su fila del mismo conjunto de usuarios
    que alimenta el CSV (una sola llamada a PostHog, sin escrituras en BD)."""
    dias = recuerdame_analytics.normalizar_dias(request.GET.get("dias"))
    date_from, date_to = recuerdame_analytics.rango_fechas(dias)

    usuario = None
    error = None
    try:
        usuarios = recuerdame_analytics.obtener_usuarios(date_from, date_to)
        fila = recuerdame_analytics.buscar_usuario_por_email(usuarios, email)
        if fila is not None:
            usuario = recuerdame_analytics.detalle_usuario(fila)
    except recuerdame_analytics.RecuerdameAnalyticsError as exc:
        error = str(exc)

    return render(
        request,
        "home/statistics_per_user_recuerdame.html",
        {
            "email": email,
            "usuario": usuario,
            "error": error,
            "dias": dias,
            "rangos": recuerdame_analytics.RANGOS_DIAS,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


#######################################################################################


