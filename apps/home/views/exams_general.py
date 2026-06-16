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
from django.db import transaction
from datetime import datetime, timedelta
from ..models import *
from ..forms import (
    ProyectoForm, RegistroDemograficoForm,
    AnalisisGeneralForm, ExamenFisicoForm, ExamenNeurologicoForm,
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
def guardar_examen_analisis(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Parent model via form
            form = AnalisisGeneralForm(request.POST)
            if not form.is_valid():
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en análisis: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

            analisis_result, created = AnalisisGeneralResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults=form.cleaned_data,
            )

            # Limpiar diagnósticos existentes
            analisis_result.diagnosticos_cie10.all().delete()
            analisis_result.diagnosticos_dsmv.all().delete()
            analisis_result.diagnosticos_no_clasificados.all().delete()

            # Procesar diagnósticos CIE-10
            cie10_codigos = request.POST.getlist("cie10_codigo[]")
            cie10_diagnosticos = request.POST.getlist("cie10_diagnostico[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(cie10_codigos, cie10_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    # Crear el diagnóstico
                    diag_cie10 = DiagnosticoCIE10.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    # Marcar estados correspondientes basados en los checkboxes con índice
                    if request.POST.get(f"cie10_confirmado_nuevo_{i}"):
                        diag_cie10.confirmado_nuevo = True
                    if request.POST.get(f"cie10_confirmado_antiguo_{i}"):
                        diag_cie10.confirmado_antiguo = True
                    if request.POST.get(f"cie10_en_estudio_{i}"):
                        diag_cie10.en_estudio = True

                    diag_cie10.save()

            # Procesar diagnósticos DSM-V (similar estructura)
            dsmv_codigos = request.POST.getlist("dsmv_codigo[]")
            dsmv_diagnosticos = request.POST.getlist("dsmv_diagnostico[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(dsmv_codigos, dsmv_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    diag_dsmv = DiagnosticoDSMV.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if request.POST.get(f"dsmv_confirmado_nuevo_{i}"):
                        diag_dsmv.confirmado_nuevo = True
                    if request.POST.get(f"dsmv_confirmado_antiguo_{i}"):
                        diag_dsmv.confirmado_antiguo = True
                    if request.POST.get(f"dsmv_en_estudio_{i}"):
                        diag_dsmv.en_estudio = True

                    diag_dsmv.save()

            # Procesar diagnósticos no clasificados
            noclasi_diagnosticos = request.POST.getlist("noclasi_diagnostico[]")

            for i, diagnostico in enumerate(noclasi_diagnosticos):
                if diagnostico.strip():
                    diag_noclasi = DiagnosticoNoClasificado.objects.create(
                        analisis_result=analisis_result,
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if request.POST.get(f"noclasi_confirmado_nuevo_{i}"):
                        diag_noclasi.confirmado_nuevo = True
                    if request.POST.get(f"noclasi_confirmado_antiguo_{i}"):
                        diag_noclasi.confirmado_antiguo = True
                    if request.POST.get(f"noclasi_en_estudio_{i}"):
                        diag_noclasi.en_estudio = True

                    diag_noclasi.save()

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Contar diagnósticos guardados
            total_diagnosticos = (
                analisis_result.diagnosticos_cie10.count()
                + analisis_result.diagnosticos_dsmv.count()
                + analisis_result.diagnosticos_no_clasificados.count()
            )

            messages.success(
                request,
                f"✅ Análisis y diagnósticos guardados exitosamente.\n"
                f"📋 Total de diagnósticos: {total_diagnosticos}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"❌ Error al guardar el análisis: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_antecedentes(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Obtener el paciente
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # NUEVO: Obtener o crear antecedentes únicos por paciente
            antecedentes_result, created = AntecedentesResult.get_or_create_for_patient(
                paciente=paciente, visita_examen=visita_examen, usuario=request.user
            )

            # Actualizar observaciones generales
            antecedentes_result.observaciones_generales = request.POST.get(
                "observaciones_generales", ""
            )

            # Crear o actualizar el link de la visita
            visita_link, link_created = AntecedentesVisitaLink.objects.get_or_create(
                visita_examen=visita_examen,
                defaults={"antecedentes_result": antecedentes_result},
            )
            visita_link.fue_revisado = True
            visita_link.fue_actualizado = True
            visita_link.revisado_por = request.user.username
            visita_link.save()

            # Variable para controlar si hay algún antecedente
            tiene_antecedentes = False
            antecedentes_guardados = []

            # Envolver en transacción para evitar pérdida de datos si hay error
            with transaction.atomic():
                    # Obtener datos de antecedentes dinámicos (desde JavaScript)
                    patologicos_data = request.POST.get("patologicos_data")
                    quirurgicos_data = request.POST.get("quirurgicos_data")
                    farmacologicos_data = request.POST.get("farmacologicos_data")
                    toxicos_data = request.POST.get("toxicos_data")
                    familiares_data = request.POST.get("familiares_data")
                    alergicos_data = request.POST.get("alergicos_data")
                    traumaticos_data = request.POST.get("traumaticos_data")
                    gineco_data = request.POST.get("gineco_data")
                    epidemiologicos_data = request.POST.get("epidemiologicos_data")
                    ets_data = request.POST.get("ets_data")
                    hospitalizaciones_data = request.POST.get("hospitalizaciones_data")
                    inmunizaciones_data = request.POST.get("inmunizaciones_data")
                    transfusionales_data = request.POST.get("transfusionales_data")

                    # ===== PROCESAR PATOLÓGICOS =====
                    if patologicos_data:
                        patologicos_list = json.loads(patologicos_data)
                        # Limpiar existentes
                        antecedentes_result.antecedentes_patologicos.all().delete()

                        for item in patologicos_list:
                            if item.get("tipo_patologia"):
                                tiene_antecedentes = True
                                AntecedentePatologico.objects.create(
                                    antecedente_result=antecedentes_result,
                                    tipo_patologia=item.get("tipo_patologia", "otros"),
                                    descripcion_otros=item.get("descripcion_otros")
                                    if item.get("tipo_patologia") == "otros"
                                    else None,
                                    fecha_inicio=datetime.strptime(
                                        item.get("fecha_inicio"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_inicio")
                                    else None,
                                    ha_recibido_tratamiento=item.get(
                                        "ha_recibido_tratamiento", False
                                    ),
                                    detalle_tratamiento=item.get("detalle_tratamiento", ""),
                                    tiene_complicaciones=item.get(
                                        "tiene_complicaciones", False
                                    ),
                                    detalle_complicaciones=item.get(
                                        "detalle_complicaciones", ""
                                    ),
                                    activo=item.get("activo", True),
                                    fecha_finalizacion=datetime.strptime(
                                        item.get("fecha_finalizacion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_finalizacion")
                                    else None,
                                    observaciones=item.get("observaciones", ""),
                                )
                        if patologicos_list:
                            antecedentes_guardados.append("Patológicos")

                    # ===== PROCESAR QUIRÚRGICOS =====
                    if quirurgicos_data:
                        quirurgicos_list = json.loads(quirurgicos_data)
                        antecedentes_result.antecedentes_quirurgicos.all().delete()
                        for item in quirurgicos_list:
                            if item.get("descripcion"):
                                tiene_antecedentes = True
                                AntecedenteQuirurgico.objects.create(
                                    antecedente_result=antecedentes_result,
                                    descripcion=item.get("descripcion"),
                                    fecha_intervencion=datetime.strptime(
                                        item.get("fecha_intervencion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_intervencion")
                                    else None,
                                    ha_recibido_tratamiento=item.get(
                                        "ha_recibido_tratamiento", False
                                    ),
                                    detalle_tratamiento=item.get("detalle_tratamiento", ""),
                                    tiene_complicaciones=item.get(
                                        "tiene_complicaciones", False
                                    ),
                                    detalle_complicaciones=item.get(
                                        "detalle_complicaciones", ""
                                    ),
                                    activo=item.get("activo", True),
                                    fecha_finalizacion=datetime.strptime(
                                        item.get("fecha_finalizacion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_finalizacion")
                                    else None,
                                    observaciones=item.get("observaciones", ""),
                                )
                        if quirurgicos_list:
                            antecedentes_guardados.append("Quirúrgicos")

                    # ===== PROCESAR FARMACOLÓGICOS =====
                    if farmacologicos_data:
                        farmacologicos_list = json.loads(farmacologicos_data)
                        antecedentes_result.antecedentes_farmacologicos.all().delete()

                        for item in farmacologicos_list:
                            # Considerar registro válido si tiene nombre comercial o genérico
                            if item.get("nombre_comercial") or item.get("nombre_generico"):
                                tiene_antecedentes = True
                                # Parsear fechas de forma segura
                                fecha_inicio = (
                                    datetime.strptime(item.get("fecha_inicio"), "%Y-%m-%d").date()
                                    if item.get("fecha_inicio")
                                    else None
                                )
                                fecha_finalizacion = (
                                    datetime.strptime(item.get("fecha_finalizacion"), "%Y-%m-%d").date()
                                    if item.get("fecha_finalizacion")
                                    else None
                                )

                                AntecedenteFarmacologico.objects.create(
                                    antecedente_result=antecedentes_result,
                                    nombre_comercial=item.get("nombre_comercial"),
                                    nombre_generico=item.get("nombre_generico", ""),
                                    presentacion=item.get("presentacion") or None,
                                    concentracion=item.get("concentracion", ""),
                                    unidad=item.get("unidad") or None,
                                    via_administracion=item.get("via_administracion") or None,
                                    cantidad=item.get("cantidad", ""),
                                    frecuencia=item.get("frecuencia", ""),
                                    fecha_inicio=fecha_inicio,
                                    fecha_finalizacion=fecha_finalizacion,
                                    indicacion=item.get("indicacion", ""),
                                    activo=item.get("activo", True),
                                    adherencia=item.get("adherencia", ""),
                                    efectos_adversos=item.get("efectos_adversos", False),
                                    descripcion_efectos_adversos=item.get(
                                        "descripcion_efectos_adversos", ""
                                    ),
                                    observaciones=item.get("observaciones", ""),
                                )
                        if farmacologicos_list:
                            antecedentes_guardados.append("Farmacológicos")

                    # ===== PROCESAR TÓXICOS =====
                    if toxicos_data:
                        toxicos_list = json.loads(toxicos_data)
                        antecedentes_result.antecedentes_toxicos.all().delete()

                        for item in toxicos_list:
                            if item.get("tipos_toxico"):
                                tiene_antecedentes = True
                                AntecedenteToxico.objects.create(
                                    antecedente_result=antecedentes_result,
                                    tipos_toxico=item.get("tipos_toxico", []),
                                    descripcion_otros=item.get("descripcion_otros", ""),
                                    fecha_inicio=datetime.strptime(
                                        item.get("fecha_inicio"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_inicio")
                                    else None,
                                    ha_recibido_tratamiento=item.get(
                                        "ha_recibido_tratamiento", False
                                    ),
                                    detalle_tratamiento=item.get("detalle_tratamiento", ""),
                                    tiene_complicaciones=item.get(
                                        "tiene_complicaciones", False
                                    ),
                                    detalle_complicaciones=item.get(
                                        "detalle_complicaciones", ""
                                    ),
                                    activo=item.get("activo", True),
                                    fecha_finalizacion=datetime.strptime(
                                        item.get("fecha_finalizacion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_finalizacion")
                                    else None,
                                    observaciones=item.get("observaciones", ""),
                                )
                        if toxicos_list:
                            antecedentes_guardados.append("Tóxicos")

                    # ===== PROCESAR FAMILIARES =====
                    if familiares_data:
                        familiares_list = json.loads(familiares_data)
                        antecedentes_result.antecedentes_familiares.all().delete()

                        for item in familiares_list:
                            if item.get("tipo_antecedente") and item.get("parentesco"):
                                tiene_antecedentes = True
                                AntecedenteFamiliar.objects.create(
                                    antecedente_result=antecedentes_result,
                                    tipo_antecedente=item.get("tipo_antecedente"),
                                    parentesco=item.get("parentesco"),
                                    observaciones=item.get("observaciones", ""),
                                )
                        if familiares_list:
                            antecedentes_guardados.append("Familiares")

                    # ===== PROCESAR ALÉRGICOS =====
                    if alergicos_data:
                        alergicos_list = json.loads(alergicos_data)
                        antecedentes_result.antecedentes_alergicos.all().delete()

                        for item in alergicos_list:
                            if item.get("descripcion"):
                                tiene_antecedentes = True
                                AntecedenteAlergico.objects.create(
                                    antecedente_result=antecedentes_result,
                                    descripcion=item.get("descripcion"),
                                    fecha_inicio=datetime.strptime(
                                        item.get("fecha_inicio"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_inicio")
                                    else None,
                                    tratamiento_recibido=item.get("tratamiento_recibido", ""),
                                    detalle_tratamiento=item.get("detalle_tratamiento", ""),
                                    complicaciones=item.get("complicaciones", ""),
                                    activo=item.get("activo", True),
                                    fecha_finalizacion=datetime.strptime(
                                        item.get("fecha_finalizacion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_finalizacion")
                                    else None,
                                    observaciones=item.get("observaciones", ""),
                                )
                        if alergicos_list:
                            antecedentes_guardados.append("Alérgicos")

                    # ===== PROCESAR TRAUMÁTICOS =====
                    if traumaticos_data:
                        traumaticos_list = json.loads(traumaticos_data)
                        antecedentes_result.antecedentes_traumaticos.all().delete()

                        for item in traumaticos_list:
                            if item.get("descripcion"):
                                tiene_antecedentes = True
                                AntecedenteTraumatico.objects.create(
                                    antecedente_result=antecedentes_result,
                                    descripcion=item.get("descripcion"),
                                    fecha_inicio=datetime.strptime(
                                        item.get("fecha_inicio"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_inicio")
                                    else None,
                                    tratamiento_recibido=item.get("tratamiento_recibido", ""),
                                    detalle_tratamiento=item.get("detalle_tratamiento", ""),
                                    complicaciones=item.get("complicaciones", ""),
                                    activo=item.get("activo", True),
                                    fecha_finalizacion=datetime.strptime(
                                        item.get("fecha_finalizacion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_finalizacion")
                                    else None,
                                    observaciones=item.get("observaciones", ""),
                                )
                        if traumaticos_list:
                            antecedentes_guardados.append("Traumáticos")

                    # ===== PROCESAR GINECO-OBSTÉTRICOS =====
                    if gineco_data:
                        gineco_dict = json.loads(gineco_data)
                        # Eliminar existente (OneToOne)
                        if hasattr(antecedentes_result, "antecedentes_gineco"):
                            antecedentes_result.antecedentes_gineco.delete()

                        if gineco_dict:
                            tiene_antecedentes = True
                            AntecedenteGinecoObstetrico.objects.create(
                                antecedente_result=antecedentes_result,
                                tiene_menarquia=gineco_dict.get("tiene_menarquia", False),
                                edad_menarquia=gineco_dict.get("edad_menarquia"),
                                tiene_menopausia=gineco_dict.get("tiene_menopausia", False),
                                edad_menopausia=gineco_dict.get("edad_menopausia"),
                                gravidez=gineco_dict.get("gravidez", 0),
                                abortos=gineco_dict.get("abortos", 0),
                                hijos_vivos=gineco_dict.get("hijos_vivos", 0),
                                usa_metodo_planificacion=gineco_dict.get(
                                    "usa_metodo_planificacion", False
                                ),
                                metodo_detalle=gineco_dict.get("metodo_detalle", ""),
                                dosis_planificacion=gineco_dict.get("dosis_planificacion", ""),
                                adherencia_planificacion=gineco_dict.get(
                                    "adherencia_planificacion", ""
                                ),
                                tolerancia_planificacion=gineco_dict.get(
                                    "tolerancia_planificacion", ""
                                ),
                                observaciones=gineco_dict.get("observaciones", ""),
                            )
                            antecedentes_guardados.append("Gineco-Obstétricos")

                    # ===== PROCESAR EPIDEMIOLÓGICOS (NUEVO) =====
                    if epidemiologicos_data:
                        epidemiologicos_list = json.loads(epidemiologicos_data)
                        antecedentes_result.antecedentes_epidemiologicos.all().delete()

                        for item in epidemiologicos_list:
                            if item.get("descripcion"):
                                tiene_antecedentes = True
                                AntecedenteEpidemiologico.objects.create(
                                    antecedente_result=antecedentes_result,
                                    tipo_antecedente=item.get("descripcion"),
                                    fecha_inicio=datetime.strptime(
                                        item.get("fecha_inicio"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_inicio")
                                    else None,
                                    tratamiento_detalle=item.get("tratamiento_detalle", ""),
                                    complicaciones_asociadas=item.get(
                                        "complicaciones_asociadas", False
                                    ),
                                    detallar_complicaciones=item.get(
                                        "detallar_complicaciones", ""
                                    ),
                                    activo_actualmente=item.get("activo_actualmente", True),
                                    fecha_finalizacion=datetime.strptime(
                                        item.get("fecha_finalizacion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_finalizacion")
                                    else None,
                                    observaciones=item.get("observaciones", ""),
                                )
                        if epidemiologicos_list:
                            antecedentes_guardados.append("Epidemiológicos")

                    # ===== PROCESAR ETS (NUEVO) =====
                    if ets_data:
                        ets_list = json.loads(ets_data)
                        antecedentes_result.antecedentes_ets.all().delete()

                        for item in ets_list:
                            if item.get("descripcion"):
                                tiene_antecedentes = True
                                AntecedenteETS.objects.create(
                                    antecedente_result=antecedentes_result,
                                    tipo_ets=item.get("descripcion"),
                                    fecha_diagnostico=datetime.strptime(
                                        item.get("fecha_inicio"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_inicio")
                                    else None,
                                    tratamiento_recibido=item.get(
                                        "ha_recibido_tratamiento", False
                                    ),
                                    detalle_tratamiento=item.get("tratamiento_detalle", ""),
                                    complicaciones=item.get("complicaciones_asociadas", False),
                                    detalle_complicaciones=item.get(
                                        "detallar_complicaciones", ""
                                    ),
                                    curado=not item.get("activo_actualmente", True),
                                    fecha_curacion=datetime.strptime(
                                        item.get("fecha_finalizacion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_finalizacion")
                                    else None,
                                    observaciones=item.get("observaciones", ""),
                                )
                        if ets_list:
                            antecedentes_guardados.append("ETS")

                    # ===== PROCESAR HOSPITALIZACIONES (NUEVO) =====
                    # ...existing code...
                    if hospitalizaciones_data:
                        hospitalizaciones_list = json.loads(hospitalizaciones_data)
                        antecedentes_result.antecedentes_hospitalizaciones.all().delete()

                        for item in hospitalizaciones_list:
                            if item.get(
                                "motivo_hospitalizacion"
                            ):  # Cambio: usar el nombre correcto del campo
                                tiene_antecedentes = True

                                # Manejar fecha_egreso de forma segura
                                fecha_egreso = None
                                if item.get("fecha_egreso"):
                                    try:
                                        fecha_egreso = datetime.strptime(
                                            item.get("fecha_egreso"), "%Y-%m-%d"
                                        ).date()
                                    except (ValueError, TypeError):
                                        fecha_egreso = None

                                # Manejar fecha_ingreso de forma segura
                                fecha_ingreso = None
                                if item.get("fecha_ingreso"):
                                    try:
                                        fecha_ingreso = datetime.strptime(
                                            item.get("fecha_ingreso"), "%Y-%m-%d"
                                        ).date()
                                    except (ValueError, TypeError):
                                        fecha_ingreso = None

                                # Convertir días_hospitalizacion a entero de forma segura
                                dias_hospitalizacion = None
                                if item.get("dias_hospitalizacion"):
                                    try:
                                        dias_hospitalizacion = int(
                                            item.get("dias_hospitalizacion")
                                        )
                                    except (ValueError, TypeError):
                                        dias_hospitalizacion = None

                                AntecedenteHospitalizacion.objects.create(
                                    antecedente_result=antecedentes_result,
                                    motivo_hospitalizacion=item.get("motivo_hospitalizacion"),
                                    fecha_ingreso=fecha_ingreso,
                                    fecha_egreso=fecha_egreso,
                                    institucion=item.get("institucion", ""),
                                    dias_hospitalizacion=dias_hospitalizacion,
                                    complicaciones_durante=item.get(
                                        "complicaciones_durante", False
                                    ),
                                    detalle_complicaciones=item.get(
                                        "detalle_complicaciones", ""
                                    ),
                                    secuelas=item.get("secuelas", False),
                                    detalle_secuelas=item.get("detalle_secuelas", ""),
                                    observaciones=item.get("observaciones", ""),
                                )
                        if hospitalizaciones_list:
                            antecedentes_guardados.append("Hospitalizaciones")
                    # ===== PROCESAR INMUNIZACIONES (NUEVO) =====
                    if inmunizaciones_data:
                        inmunizaciones_list = json.loads(inmunizaciones_data)
                        antecedentes_result.antecedentes_inmunizaciones.all().delete()

                        for item in inmunizaciones_list:
                            if item.get("vacuna_inmunizacion"):
                                tiene_antecedentes = True
                                AntecedenteInmunizacion.objects.create(
                                    antecedente_result=antecedentes_result,
                                    nombre_vacuna=item.get("vacuna_inmunizacion"),
                                    fecha_aplicacion=datetime.strptime(
                                        item.get("fecha_ultima_dosis"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_ultima_dosis")
                                    else None,
                                    dosis_numero=item.get("numero_dosis", 1),
                                    observaciones=item.get("observaciones", ""),
                                )
                        if inmunizaciones_list:
                            antecedentes_guardados.append("Inmunizaciones")

                    # ===== PROCESAR TRANSFUSIONALES (NUEVO) =====
                    if transfusionales_data:
                        transfusionales_list = json.loads(transfusionales_data)
                        antecedentes_result.antecedentes_transfusionales.all().delete()

                        for item in transfusionales_list:
                            if item.get("motivo_transfusion"):
                                tiene_antecedentes = True
                                AntecedenteTransfusional.objects.create(
                                    antecedente_result=antecedentes_result,
                                    motivo_transfusion=item.get("motivo_transfusion"),
                                    fecha_transfusion=datetime.strptime(
                                        item.get("fecha_ultima_transfusion"), "%Y-%m-%d"
                                    ).date()
                                    if item.get("fecha_ultima_transfusion")
                                    else None,
                                    tipo_componente=item.get("tipo_componente", "sangre_total"),
                                    cantidad_unidades=item.get("numero_unidades", 1),
                                    tuvo_reacciones=item.get("tuvo_reacciones", False),
                                    detalle_reacciones=item.get("detalle_reacciones", ""),
                                    observaciones=item.get("observaciones", ""),
                                )
                        if transfusionales_list:
                            antecedentes_guardados.append("Transfusionales")

                    # Actualizar el campo principal
                    antecedentes_result.tiene_antecedentes = tiene_antecedentes
                    antecedentes_result.save()

                    # Marcar el examen como completado
                    visita_examen.estado = "completado"
                    visita_examen.fecha_completado = timezone.now()
                    visita_examen.save()

            # Mensaje de éxito personalizado
            if antecedentes_guardados:
                tipos_guardados = ", ".join(antecedentes_guardados)
                messages.success(
                    request,
                    f"✅ Antecedentes médicos guardados exitosamente.\n"
                    f"📋 Tipos registrados: {tipos_guardados}",
                )
            else:
                messages.success(
                    request,
                    "✅ Antecedentes médicos guardados exitosamente.\n"
                    "📋 Sin antecedentes registrados.",
                )

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar los antecedentes médicos: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_medicamentos(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # 🔧 CORRECCIÓN: Obtener o crear MedicamentosResult de forma correcta
            try:
                medicamentos_result = MedicamentosResult.objects.get(
                    visita_examen=visita_examen
                )
            except MedicamentosResult.DoesNotExist:
                medicamentos_result = MedicamentosResult.objects.create(
                    visita_examen=visita_examen
                )

            # Actualizar observaciones generales
            observaciones_generales = request.POST.get("observaciones_generales", "")
            medicamentos_result.observaciones_generales = observaciones_generales
            medicamentos_result.save()

            # Obtener arrays de datos de medicamentos
            nombres_comerciales = request.POST.getlist("nombre_comercial[]")
            nombres_genericos = request.POST.getlist("nombre_generico[]")
            presentaciones = request.POST.getlist("presentacion[]")
            concentraciones = request.POST.getlist("concentracion[]")
            unidades = request.POST.getlist("unidad[]")
            vias_administracion = request.POST.getlist("via_administracion[]")
            cantidades = request.POST.getlist("cantidad[]")
            frecuencias = request.POST.getlist("frecuencia[]")
            fechas_inicio = request.POST.getlist("fecha_inicio[]")
            fechas_finalizacion = request.POST.getlist("fecha_finalizacion[]")
            indicaciones = request.POST.getlist("indicacion[]")

            # Campos adicionales
            adherencias = request.POST.getlist("adherencia[]")
            efectos_adversos = request.POST.getlist("efectos_adversos[]")
            descripciones_efectos = request.POST.getlist(
                "descripcion_efectos_adversos[]"
            )
            observaciones_medicamentos = request.POST.getlist("observaciones[]")

            # 🔧 CORRECCIÓN: Eliminar medicamentos existentes antes de crear nuevos
            medicamentos_existentes = medicamentos_result.medicamentos.all()
            count_eliminados = medicamentos_existentes.count()
            medicamentos_existentes.delete()

            medicamentos_guardados = 0

            # Procesar cada medicamento
            for i in range(len(nombres_comerciales)):
                nombre_comercial = (
                    nombres_comerciales[i].strip()
                    if i < len(nombres_comerciales)
                    else ""
                )

                # Validar que al menos el nombre comercial esté presente
                if nombre_comercial:
                    # Manejar fechas de forma segura
                    fecha_inicio = None
                    if i < len(fechas_inicio) and fechas_inicio[i]:
                        try:
                            fecha_inicio = datetime.strptime(
                                fechas_inicio[i], "%Y-%m-%d"
                            ).date()
                        except (ValueError, TypeError) as e:
                            fecha_inicio = None

                    fecha_finalizacion = None
                    if i < len(fechas_finalizacion) and fechas_finalizacion[i]:
                        try:
                            fecha_finalizacion = datetime.strptime(
                                fechas_finalizacion[i], "%Y-%m-%d"
                            ).date()
                        except (ValueError, TypeError) as e:
                            fecha_finalizacion = None

                    # Manejar efectos adversos
                    tiene_efectos_adversos = False
                    if i < len(efectos_adversos):
                        tiene_efectos_adversos = efectos_adversos[i] == "true"

                    # 🔧 CORRECCIÓN: Verificar que el campo 'presentacion' es obligatorio
                    presentacion = (
                        presentaciones[i]
                        if i < len(presentaciones) and presentaciones[i]
                        else "tableta"
                    )
                    concentracion = (
                        concentraciones[i]
                        if i < len(concentraciones) and concentraciones[i]
                        else "No especificada"
                    )
                    unidad = (
                        unidades[i]
                        if i < len(unidades) and unidades[i]
                        else "miligramos"
                    )
                    via_administracion = (
                        vias_administracion[i]
                        if i < len(vias_administracion) and vias_administracion[i]
                        else "oral"
                    )
                    cantidad = (
                        cantidades[i] if i < len(cantidades) and cantidades[i] else "1"
                    )
                    frecuencia = (
                        frecuencias[i]
                        if i < len(frecuencias) and frecuencias[i]
                        else "No especificada"
                    )
                    indicacion = (
                        indicaciones[i]
                        if i < len(indicaciones) and indicaciones[i]
                        else "No especificada"
                    )

                    # Crear el medicamento
                    try:
                        medicamento = Medicamento.objects.create(
                            medicamentos_result=medicamentos_result,
                            nombre_comercial=nombre_comercial,
                            nombre_generico=nombres_genericos[i].strip()
                            if i < len(nombres_genericos)
                            else "",
                            presentacion=presentacion,
                            concentracion=concentracion,
                            unidad=unidad,
                            via_administracion=via_administracion,
                            cantidad=cantidad,
                            frecuencia=frecuencia,
                            fecha_inicio=fecha_inicio,
                            fecha_finalizacion=fecha_finalizacion,
                            indicacion=indicacion,
                            adherencia=adherencias[i]
                            if i < len(adherencias)
                            else "no_evaluada",
                            efectos_adversos=tiene_efectos_adversos,
                            descripcion_efectos_adversos=descripciones_efectos[i]
                            if i < len(descripciones_efectos)
                            else "",
                            observaciones=observaciones_medicamentos[i]
                            if i < len(observaciones_medicamentos)
                            else "",
                            activo=True,  # Por defecto activo
                        )
                        medicamentos_guardados += 1

                    except Exception as e:
                        # Continuar con el siguiente medicamento
                        continue
                else:
                    print(f"⚠️ Medicamento {i + 1} omitido - sin nombre comercial")

            # Marcar el examen como completado solo si se guardó al menos un medicamento
            if medicamentos_guardados > 0:
                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(
                    request,
                    f"✅ Se guardaron {medicamentos_guardados} medicamento(s) correctamente.",
                )
            else:
                # Revertir el estado si no se guardó nada
                visita_examen.estado = "pendiente"
                visita_examen.save()
                messages.warning(request, "⚠️ No se guardó ningún medicamento válido.")

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar los medicamentos: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_fisico(request):
    """Vista para guardar el examen físico general usando ExamenFisicoForm."""
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            if not visita_id or not paciente_id or not examen_id:
                raise ValueError("Faltan datos requeridos")

            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=int(visita_id), examen_id=int(examen_id)
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = ExamenFisicoForm(request.POST)
            if form.is_valid():
                ExamenFisicoResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(request, "✅ Examen físico general guardado correctamente.")
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in form.errors.items()
                )
                messages.error(request, f"❌ Error de validación en examen físico: {error_msgs}")
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except ValueError as ve:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error de datos: {str(ve)}")
            return redirect("detalle_paciente", paciente_id=paciente_id if paciente_id else 1)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass
            messages.error(request, f"❌ Error al guardar el examen físico: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id if paciente_id else 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


# === FUNCIONES AUXILIARES ===
def safe_float_required(value, default=0.0):
    """Convierte a float con valor por defecto obligatorio"""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_required(value, default=0):
    """Convierte a int con valor por defecto obligatorio"""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float_optional(value):
    """Convierte a float o retorna None si no hay valor"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


@login_required
def guardar_revision_sistemas(request):
    """Vista específica para guardar el examen de Revisión por Sistemas"""
    if request.method == "POST":
        visita_id = request.POST.get("visita_id")
        paciente_id = request.POST.get("paciente_id")
        examen_id = request.POST.get("examen_id")

        try:
            # ===================================================
            # 1. OBTENER OBJETOS PRINCIPALES
            # ===================================================
            visita = get_object_or_404(Visita, id=visita_id)
            examen = get_object_or_404(Examen, id=examen_id)
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)

            # Obtener o crear VisitaExamen
            visita_examen, created = VisitaExamen.objects.get_or_create(
                visita=visita, examen=examen, defaults={"estado": "pendiente"}
            )

            # ===================================================
            # 2. OBTENER O CREAR EL RESULTADO PRINCIPAL
            # ===================================================
            resultado, resultado_created = RevisionSistemasResult.objects.get_or_create(
                visita_examen=visita_examen, defaults={}
            )

            accion = "creado" if resultado_created else "actualizado"

            # ===================================================
            # 3. ACTUALIZAR CAMPOS DE CONTROL DE SISTEMAS
            # ===================================================
            sistemas = [
                "general",
                "cabeza_cuello",
                "cardiopulmonar",
                "gastrointestinal",
                "genitourinario",
                "vascular_periferico",
                "osteomuscular",
                "piel_faneras",
                "otros",
            ]

            sistemas_activados = []
            for sistema in sistemas:
                campo_sintoma = f"sintoma_{sistema}"
                valor_sintoma = request.POST.get(campo_sintoma, "no")

                # Actualizar campo en el modelo principal
                setattr(resultado, campo_sintoma, valor_sintoma)

                if valor_sintoma == "si":
                    sistemas_activados.append(sistema)

            resultado.save()

            # ===================================================
            # 4. PROCESAR SÍNTOMAS DETALLADOS
            # ===================================================
            # Eliminar detalles existentes para actualización completa
            DetalleRevisionSistemas.objects.filter(
                revision_sistemas_result=resultado
            ).delete()

            total_sintomas_guardados = 0

            for sistema in sistemas_activados:
                # Obtener arrays del formulario
                sintomas = request.POST.getlist(f"{sistema}_sintoma[]")
                tiempos = request.POST.getlist(f"{sistema}_tiempo[]")
                caracteristicas_list = request.POST.getlist(
                    f"{sistema}_caracteristicas[]"
                )

                # Crear detalles para cada síntoma del sistema
                for i in range(len(sintomas)):
                    sintoma = sintomas[i].strip() if i < len(sintomas) else ""
                    tiempo = tiempos[i].strip() if i < len(tiempos) else ""
                    caracteristica = (
                        caracteristicas_list[i].strip()
                        if i < len(caracteristicas_list)
                        else ""
                    )

                    # Solo guardar si hay contenido en el síntoma
                    if sintoma:
                        detalle = DetalleRevisionSistemas.objects.create(
                            revision_sistemas_result=resultado,
                            sistema=sistema,
                            sintoma=sintoma,
                            tiempo=tiempo,
                            caracteristicas=caracteristica,
                        )
                        total_sintomas_guardados += 1

            # ===================================================
            # 5. ACTUALIZAR ESTADO DE LA VISITA-EXAMEN
            # ===================================================
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # ===================================================
            # 6. MENSAJE DE ÉXITO Y REDIRECCIÓN
            # ===================================================
            mensaje_resumen = (
                f"Revisión por Sistemas {accion} correctamente. "
                f"Sistemas evaluados: {len(sistemas_activados)}, "
                f"Síntomas registrados: {total_sintomas_guardados}"
            )

            messages.success(request, mensaje_resumen)

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(
                request, f"Error al procesar Revisión por Sistemas: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

    # Si no es POST, redirigir al home
    return redirect("home")


@login_required
def guardar_examen_neurologico(request):
    """Vista para guardar el examen neurológico usando ExamenNeurologicoForm."""
    if request.method == "POST":
        visita_id = request.POST.get("visita_examen")
        paciente_id = request.POST.get("paciente_id")
        examen_id = request.POST.get("examen_id")

        try:
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            form = ExamenNeurologicoForm(request.POST)
            if form.is_valid():
                ExamenNeurologicoResult.objects.update_or_create(
                    visita_examen=visita_examen,
                    defaults=form.cleaned_data,
                )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(
                    request, "✅ Examen Neurológico guardado correctamente."
                )
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in list(form.errors.items())[:5]
                )
                messages.error(
                    request,
                    f"❌ Error de validación en examen neurológico: {error_msgs}",
                )
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(
                request, f"❌ Error al procesar Examen Neurológico: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

    return redirect("home")




# FUNCIÓN AUXILIAR PARA EXTRAER INFORMACIÓN DE RESULTADOS
