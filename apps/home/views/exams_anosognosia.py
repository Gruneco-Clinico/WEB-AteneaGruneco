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
from ..forms import (
    EuroQol5D5LForm, EuroQolEVASaludForm, LawtonBrodyForm, CuidadorNPIForm,
    AQDCuidadorForm, AQDParticipanteForm, CDRParticipanteForm, CDRCuidadorForm,
    PuntajeCDRForm, MoCAForm, ParticipanteYesavageForm, ZaritForm,
    RedLatSpanishForm, BettyFerrelForm, ConsentimientoParticipanteForm,
    ConsentimientoCuidadorForm, AnamnesisCuidadorForm, AnamnesisParticipanteForm,
    SeguimientoIntervencionesForm,
)
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

@login_required
def guardar_examen_Participante_EuroQoL(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = EuroQol5D5LForm(request.POST)
            if form.is_valid():
                EuroQol5D5LResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Cuestionario EuroQol-5D-5L guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en EuroQol-5D-5L: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario EuroQol-5D-5L: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_LawtonBrody(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = LawtonBrodyForm(request.POST)
            if form.is_valid():
                LawtonBrodyResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala de Lawton y Brody guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Lawton y Brody: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el examen Lawton y Brody: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_Yesavage(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = ParticipanteYesavageForm(request.POST)
            if form.is_valid():
                ParticipanteYesavageResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala de Depresión Geriátrica de Yesavage guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Yesavage: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el examen de Yesavage: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_EVA_EuroQoL(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = EuroQolEVASaludForm(request.POST)
            if form.is_valid():
                EuroQolEVASaludResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Autovaloración del Estado de Salud (EVA EuroQol) guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en EVA EuroQol: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la Autovaloración del Estado de Salud (EVA EuroQol): {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_NPI(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = CuidadorNPIForm(request.POST)
            if form.is_valid():
                CuidadorNPIResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Inventario Neuropsiquiátrico (NPI) guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en NPI: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el Inventario Neuropsiquiátrico (NPI): {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_AQD(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = AQDCuidadorForm(request.POST)
            if form.is_valid():
                AQDCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala AQ-D Cuidador guardada correctamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en AQ-D Cuidador: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la escala AQ-D Cuidador: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_AQD(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = AQDParticipanteForm(request.POST)
            if form.is_valid():
                AQDParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala AQ-D Participante guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en AQ-D Participante: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la escala AQ-D Participante: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = CDRParticipanteForm(request.POST)
            if form.is_valid():
                CDRParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Cuestionario CDR - Participante guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en CDR Participante: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario CDR - Participante: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_MoCA(request):
    if request.method != "POST":
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")

    try:
        visita_id = request.POST.get("visita_id")
        paciente_id = request.POST.get("paciente_id")
        examen_id = request.POST.get("examen_id")

        visita_examen = get_object_or_404(
            VisitaExamen, visita_id=visita_id, examen_id=examen_id
        )

        if visita_examen.estado == "pendiente":
            visita_examen.estado = "en_progreso"
            visita_examen.fecha_inicio = timezone.now()
            visita_examen.save()

        form = MoCAForm(request.POST)
        if form.is_valid():
            MoCAResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults=form.cleaned_data,
            )

            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            pt = form.cleaned_data.get("puntaje_total", 0)
            messages.success(request, f"✅ Escala MoCA guardada correctamente | Puntaje: {pt}/30")
            return redirect("detalle_paciente", paciente_id=paciente_id)
        else:
            error_msgs = "; ".join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items()
            )
            messages.error(request, f"❌ Error de validación en MoCA: {error_msgs}")
            return redirect("detalle_paciente", paciente_id=paciente_id)

    except Exception as e:
        messages.error(request, f"❌ Error al guardar MoCA: {str(e)}")
        return redirect("detalle_paciente", paciente_id=paciente_id)


@login_required
def guardar_examen_Cuidador_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = CDRCuidadorForm(request.POST)
            if form.is_valid():
                CDRCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala CDR (Cuidador) guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en CDR Cuidador: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario CDR (Cuidador): {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_RedLatSpanish(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = RedLatSpanishForm(request.POST)
            if form.is_valid():
                RedLatSpanishResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Evaluación RedLat Spanish guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en RedLat Spanish: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la Evaluación RedLat Spanish: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_BettyFerrel(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = BettyFerrelForm(request.POST)
            if form.is_valid():
                BettyFerrelResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Examen Calidad de Vida Betty Ferrel guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Betty Ferrel: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el cuestionario Betty Ferrel: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_evaluacion_clinica_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = PuntajeCDRForm(request.POST)
            if form.is_valid():
                PuntajeCDRResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Evaluación clínica CDR guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en CDR: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la evaluación clínica CDR: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_consentimiento_participante(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = ConsentimientoParticipanteForm(request.POST)
            if form.is_valid():
                ConsentimientoInformadoParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Consentimiento Informado Participante guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Consentimiento Participante: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el Consentimiento Informado Participante: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_consentimiento_cuidador(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = ConsentimientoCuidadorForm(request.POST)
            if form.is_valid():
                ConsentimientoInformadoCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Consentimiento Informado Cuidador guardado exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Consentimiento Cuidador: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el Consentimiento Informado Cuidador: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_anamnesis_cuidador(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = AnamnesisCuidadorForm(request.POST)
            if form.is_valid():
                AnamnesisCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Anamnesis Cuidador guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Anamnesis Cuidador: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar Anamnesis Cuidador: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_anamnesis_participante(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = AnamnesisParticipanteForm(request.POST)
            if form.is_valid():
                AnamnesisParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Anamnesis Participante guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Anamnesis Participante: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la Anamnesis Participante: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_Zarit(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = ZaritForm(request.POST)
            if form.is_valid():
                ZaritResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Escala de Zarit guardada exitosamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Zarit: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar la escala de Zarit: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_intervenciones(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = SeguimientoIntervencionesForm(request.POST)
            if form.is_valid():
                cleaned = form.cleaned_data.copy()
                numero_sesion = cleaned.pop("numero_sesion")

                sesion, created = SeguimientoIntervencionesResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    numero_sesion=numero_sesion,
                    defaults=cleaned,
                )

                # Mark completed only when all 18 sessions are done
                total_sesiones = SeguimientoIntervencionesResult.objects.filter(
                    visita_examen=visita_examen
                ).count()

                if total_sesiones >= 18:
                    visita_examen.estado = "completado"
                    visita_examen.fecha_completado = timezone.now()
                else:
                    visita_examen.estado = "en_progreso"
                visita_examen.save()

                msg = f"✅ Sesión {numero_sesion} {'guardada' if created else 'actualizada'} exitosamente."
                messages.success(request, msg)
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en Intervenciones: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"❌ Error al guardar la sesión: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def obtener_datos_sesion(request, visita_id, examen_id, num_sesion):
    visita_examen = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )
    try:
        sesion = SeguimientoIntervencionesResult.objects.get(
            visita_examen=visita_examen, numero_sesion=num_sesion
        )
        data = {
            "nombre": sesion.nombre_sesion,
            "fecha": sesion.fecha.strftime("%Y-%m-%d") if sesion.fecha else "",
            "hora_inicio": sesion.hora_inicio.strftime("%H:%M")
            if sesion.hora_inicio
            else "",
            "hora_fin": sesion.hora_fin.strftime("%H:%M") if sesion.hora_fin else "",
            "asistencia": sesion.asistencia,
            "participacion": sesion.participacion,
            "estado": sesion.estado,
            "tematica": sesion.tematica,
            "observaciones": sesion.observaciones,
        }
    except SeguimientoIntervencionesResult.DoesNotExist:
        data = {}

    return JsonResponse(data)


@login_required
def resumen_sesiones(request, visita_id, examen_id):
    visita_examen = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )

    sesiones = SeguimientoIntervencionesResult.objects.filter(
        visita_examen=visita_examen
    ).order_by("numero_sesion")

    if sesiones.count() < 18:
        return JsonResponse({"error": "Aún no se han completado las 18 sesiones."})

    total_sesiones = 18
    asistidas = sesiones.filter(asistencia="Sí").count()

    porcentaje_asistencia = round((asistidas / total_sesiones) * 100, 2)
    conteo_asistencia = f"{asistidas}/{total_sesiones}"

    participaciones = [s.participacion for s in sesiones if s.participacion]
    promedio_participacion = (
        round(sum(map(int, participaciones)) / len(participaciones), 2)
        if participaciones
        else 0
    )

    tendencia_participacion = [
        int(s.participacion) if s.participacion else None for s in sesiones
    ]

    alerta = None
    if porcentaje_asistencia < 70:
        alerta = "⚠️ Riesgo de abandono (asistencia < 70%)"

    data = {
        "porcentaje_asistencia": porcentaje_asistencia,
        "conteo_asistencia": conteo_asistencia,
        "promedio_participacion": promedio_participacion,
        "tendencia_participacion": tendencia_participacion,
        "alerta": alerta,
    }

    return JsonResponse(data)


# Estadísticas - RecuérdaMe


