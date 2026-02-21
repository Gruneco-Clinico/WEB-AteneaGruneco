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

from .auth import is_superuser

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


