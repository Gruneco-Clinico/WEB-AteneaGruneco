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

        r1 = requests.post(url_query, headers=headers, json={"query": query_dau}, timeout=10)
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

        r2 = requests.post(url_query, headers=headers, json={"query": query_growth}, timeout=10)
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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        # 2. Ejecutar la query del insight
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        # 2. Ejecutar la query del insight
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        # Ejecutar query
        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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
        r = requests.get(url_insight, headers=headers, timeout=10)
        r.raise_for_status()
        insight = r.json()

        query = insight.get("query")
        r = requests.post(url_query, headers=headers, json={"query": query}, timeout=10)
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


