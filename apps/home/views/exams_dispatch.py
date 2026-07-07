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
from ..forms import ProyectoForm, RegistroDemograficoForm, CognitivoAnamnesisForm
from .exam_builder import builder_result_response, realizar_examen_builder
from ..exam_legacy import examen_has_builder_schema, is_legacy_examen
from ..exam_registry import get_exam_config, get_exam_model
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
def realizar_examen(request, visita_id, examen_id, paciente_id):
    # Legacy (IDs definidos en exam_legacy): siempre plantilla/registry fijos,
    # nunca builder aunque ``Examen.campos`` esté poblado por error en BD.
    examen = get_object_or_404(Examen, pk=examen_id)
    if is_legacy_examen(examen_id):
        config = get_exam_config(int(examen_id))
        if not config:
            messages.error(
                request,
                "Este examen legacy no tiene configuración de plantilla registrada.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)
    else:
        if examen_has_builder_schema(examen.campos):
            return realizar_examen_builder(request, visita_id, examen_id, paciente_id)
        config = get_exam_config(int(examen_id))
        if not config:
            return realizar_examen_builder(request, visita_id, examen_id, paciente_id)

    exam_model = get_exam_model(int(examen_id))

    # Obtener datos existentes
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    visita = get_object_or_404(Visita, id=visita_id, paciente=paciente)
    
    # BLOQUEAR EDICIÓN SI LA VISITA ESTÁ FIRMADA
    if visita.firmado:
        messages.error(request, "No se puede editar un examen de una visita firmada.")
        return redirect("detalle_paciente", paciente_id=paciente_id)
    
    datos_examen = None
    visita_examen_obj = None
    modo_edicion = False

    try:
        visita_examen_obj = VisitaExamen.objects.get(
            visita_id=visita_id, examen_id=examen_id
        )

        if exam_model and visita_examen_obj.esta_realizado:
            resultado = visita_examen_obj.get_resultado_instance()
            if resultado and isinstance(resultado, exam_model):
                # ===================================================
                # CASO ESPECIAL: ANAMNESIS DE SUEÑO (ID 10)
                # ===================================================
                if int(examen_id) == 10 and isinstance(resultado, SuenoAnamnesisResult):
                    # Obtener datos básicos del modelo principal
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)

                    # Obtener relaciones hijas con prefetch para optimización
                    anamnesis = SuenoAnamnesisResult.objects.prefetch_related(
                        "sustancias",
                        "medicamentos",
                        "pantallas",
                        "actividades_en_cama",
                        "actividades_fisicas",
                        "sintomas_suenos",
                        "sintomas_diurno",
                        "tipos_queja_detalle",
                    ).get(id=resultado.id)

                    # Agregar las relaciones al diccionario de datos
                    datos_examen["sustancias"] = list(
                        anamnesis.sustancias.values(
                            "tipo", "cantidad", "frecuencia", "tiempo", "observaciones"
                        )
                    )

                    datos_examen["medicamentos"] = list(
                        anamnesis.medicamentos.values(
                            "nombre",
                            "dosis",
                            "presentacion",
                            "veces_dia",
                            "frecuencia",
                            "tiempo",
                            "observaciones",
                        )
                    )

                    datos_examen["pantallas"] = list(
                        anamnesis.pantallas.values(
                            "tipo", "frecuencia", "tiempo_antes_dormir"
                        )
                    )

                    datos_examen["actividades_en_cama"] = list(
                        anamnesis.actividades_en_cama.values(
                            "tipo", "frecuencia", "observaciones"
                        )
                    )

                    datos_examen["actividades_fisicas"] = list(
                        anamnesis.actividades_fisicas.values(
                            "tipo",
                            "otro_texto",
                            "intensidad",
                            "frecuencia",
                            "observaciones",
                        )
                    )

                    datos_examen["sintomas_suenos"] = list(
                        anamnesis.sintomas_suenos.values(
                            "tipo",
                            "cuando_inicio",
                            "evolucion",
                            "frecuencia",
                            "gravedad",
                            "observaciones",
                        )
                    )

                    datos_examen["sintomas_diurnos"] = list(
                        anamnesis.sintomas_diurno.values(
                            "tipo",
                            "cuando_inicio",
                            "evolucion",
                            "frecuencia",
                            "gravedad",
                            "observaciones",
                        )
                    )

                    datos_examen["tipos_queja"] = list(
                        anamnesis.tipos_queja_detalle.values(
                            "nombre", "inicio", "evolucion", "frecuencia", "gravedad"
                        )
                    )

                    # AGREGAR ESTAS LÍNEAS PARA PASAR AL CONTEXTO DEL TEMPLATE:
                    tipos_queja = datos_examen["tipos_queja"]
                    sustancias = datos_examen["sustancias"]
                    medicamentos = datos_examen["medicamentos"]
                    pantallas = datos_examen["pantallas"]
                    actividades_en_cama = datos_examen["actividades_en_cama"]
                    actividades_fisicas = datos_examen["actividades_fisicas"]
                    sintomas_suenos = datos_examen["sintomas_suenos"]
                    sintomas_diurnos = datos_examen["sintomas_diurnos"]

                    modo_edicion = True

                # ===================================================
                # CASO ESPECIAL: ANÁLISIS GENERAL (ID 7)
                # ===================================================
                elif int(examen_id) == 7 and isinstance(
                    resultado, AnalisisGeneralResult
                ):
                    # Obtener datos básicos del modelo principal
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)

                    # Obtener relaciones hijas con prefetch para optimización
                    analisis = AnalisisGeneralResult.objects.prefetch_related(
                        "diagnosticos_cie10",
                        "diagnosticos_dsmv",
                        "diagnosticos_no_clasificados",
                    ).get(id=resultado.id)

                    # Agregar las relaciones al diccionario de datos
                    datos_examen["diagnosticos_cie10"] = list(
                        analisis.diagnosticos_cie10.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    datos_examen["diagnosticos_dsmv"] = list(
                        analisis.diagnosticos_dsmv.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                   

                    datos_examen["diagnosticos_no_clasificados"] = list(
                        analisis.diagnosticos_no_clasificados.values(
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    modo_edicion = True

                else:
                    # ===================================================
                    # CASO GENERAL: OTROS EXÁMENES
                    # ===================================================
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)
                    modo_edicion = True

            # CASO ESPECIAL: ANTECEDENTES (ID 5) - FUERA DEL IF ANTERIOR
            # ===================================================
            elif int(examen_id) == 5:
                # Para antecedentes, verificar si existe un AntecedentesVisitaLink
                try:
                    antecedentes_result = None
                    try:
                        antecedentes_link = AntecedentesVisitaLink.objects.get(
                            visita_examen=visita_examen_obj
                        )
                        antecedentes_result = antecedentes_link.antecedentes_result
                    except AntecedentesVisitaLink.DoesNotExist:
                        antecedentes_result = AntecedentesResult.objects.filter(
                            paciente=paciente
                        ).first()

                    if antecedentes_result:
                        # Obtener datos básicos del modelo principal
                        datos_examen = model_to_dict(antecedentes_result)
                        datos_examen.pop("id", None)
                        datos_examen.pop("paciente", None)

                        # Obtener relaciones hijas con prefetch para optimización
                        antecedentes = AntecedentesResult.objects.prefetch_related(
                            "antecedentes_patologicos",
                            "antecedentes_quirurgicos",
                            "antecedentes_farmacologicos",
                            "antecedentes_toxicos",
                            "antecedentes_familiares",
                            "antecedentes_alergicos",
                            "antecedentes_traumaticos",
                            "antecedentes_gineco",
                            "antecedentes_epidemiologicos",
                            "antecedentes_ets",
                            "antecedentes_hospitalizaciones",
                            "antecedentes_inmunizaciones",
                            "antecedentes_transfusionales",
                        ).get(id=antecedentes_result.id)

                        # Agregar las relaciones al diccionario de datos
                        datos_examen["patologicos"] = list(
                            antecedentes.antecedentes_patologicos.values(
                                "tipo_patologia",
                                "descripcion_otros",
                                "fecha_inicio",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["quirurgicos"] = list(
                            antecedentes.antecedentes_quirurgicos.values(
                                "descripcion",
                                "fecha_intervencion",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["farmacologicos"] = list(
                            antecedentes.antecedentes_farmacologicos.values(
                                "id",
                                "nombre_comercial",
                                "nombre_generico",
                                "presentacion",
                                "concentracion",
                                "unidad",
                                "via_administracion",
                                "cantidad",
                                "frecuencia",
                                "fecha_inicio",
                                "fecha_finalizacion",
                                "indicacion",
                                "activo",
                                "adherencia",
                                "efectos_adversos",
                                "descripcion_efectos_adversos",
                                "observaciones",
                            )
                        )

                        datos_examen["toxicos"] = list(
                            antecedentes.antecedentes_toxicos.values(
                                "tipos_toxico",
                                "descripcion_otros",
                                "fecha_inicio",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["familiares"] = list(
                            antecedentes.antecedentes_familiares.values(
                                "tipo_antecedente", "parentesco", "observaciones"
                            )
                        )

                        datos_examen["alergicos"] = list(
                            antecedentes.antecedentes_alergicos.values(
                                "descripcion",
                                "fecha_inicio",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["traumaticos"] = list(
                            antecedentes.antecedentes_traumaticos.values(
                                "descripcion",
                                "fecha_inicio",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        # Gineco-obstétricos (OneToOne)
                        if (
                            hasattr(antecedentes, "antecedentes_gineco")
                            and antecedentes.antecedentes_gineco
                        ):
                            gineco_data = model_to_dict(
                                antecedentes.antecedentes_gineco
                            )
                            gineco_data.pop("id", None)
                            gineco_data.pop("antecedente_result", None)
                            datos_examen["gineco_obstetricos"] = gineco_data
                        else:
                            datos_examen["gineco_obstetricos"] = {}

                        datos_examen["epidemiologicos"] = list(
                            antecedentes.antecedentes_epidemiologicos.values(
                                "tipo_antecedente",
                                "fecha_inicio",
                                "tratamiento_detalle",
                                "complicaciones_asociadas",
                                "detallar_complicaciones",
                                "activo_actualmente",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["ets"] = list(
                            antecedentes.antecedentes_ets.values(
                                "tipo_ets",
                                "fecha_diagnostico",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "detalle_complicaciones",
                                "curado",
                                "fecha_curacion",
                                "observaciones",
                            )
                        )

                        datos_examen["hospitalizaciones"] = list(
                            antecedentes.antecedentes_hospitalizaciones.values(
                                "motivo_hospitalizacion",
                                "fecha_ingreso",
                                "fecha_egreso",
                                "dias_hospitalizacion",
                                "institucion",
                                "observaciones",
                            )
                        )

                        datos_examen["inmunizaciones"] = list(
                            antecedentes.antecedentes_inmunizaciones.values(
                                "nombre_vacuna",
                                "fecha_aplicacion",
                                "dosis_numero",
                                "observaciones",
                            )
                        )

                        # Mapear claves a las que espera el frontend/guardado
                        try:
                            mapped_inmunizaciones = []
                            for itm in datos_examen.get("inmunizaciones", []):
                                mapped_inmunizaciones.append({
                                    "vacuna_inmunizacion": itm.get("nombre_vacuna"),
                                    "fecha_ultima_dosis": itm.get("fecha_aplicacion"),
                                    "numero_dosis": itm.get("dosis_numero"),
                                    "observaciones": itm.get("observaciones", ""),
                                })
                            datos_examen["inmunizaciones"] = mapped_inmunizaciones
                        except Exception:
                            pass

                        datos_examen["transfusionales"] = list(
                            antecedentes.antecedentes_transfusionales.values(
                                "motivo_transfusion",
                                "fecha_transfusion",
                                "tipo_componente",
                                "cantidad_unidades",
                                "tuvo_reacciones",
                                "detalle_reacciones",
                                "observaciones",
                            )
                        )

                        # Mapear claves para transfusionales al formato esperado
                        try:
                            mapped_trans = []
                            for itm in datos_examen.get("transfusionales", []):
                                mapped_trans.append({
                                    "motivo_transfusion": itm.get("motivo_transfusion"),
                                    "fecha_ultima_transfusion": itm.get("fecha_transfusion"),
                                    "tipo_componente": itm.get("tipo_componente"),
                                    "numero_unidades": itm.get("cantidad_unidades"),
                                    "tuvo_reacciones": itm.get("tuvo_reacciones", False),
                                    "detalle_reacciones": itm.get("detalle_reacciones", ""),
                                    "observaciones": itm.get("observaciones", ""),
                                })
                            datos_examen["transfusionales"] = mapped_trans
                        except Exception:
                            pass

                        modo_edicion = True

                        # Convertir fechas y objetos no-serializables a strings para JSON
                        try:
                            def _convert_dates(obj):
                                if isinstance(obj, dict):
                                    return {k: _convert_dates(v) for k, v in obj.items()}
                                if isinstance(obj, list):
                                    return [_convert_dates(i) for i in obj]
                                if hasattr(obj, "strftime"):
                                    try:
                                        return obj.strftime("%Y-%m-%d")
                                    except Exception:
                                        return str(obj)
                                return obj

                            datos_examen = _convert_dates(datos_examen)
                            datos_examen_json = json.dumps(datos_examen)
                        except Exception:
                            datos_examen_json = None
                except AntecedentesVisitaLink.DoesNotExist:
                    # No hay antecedentes previos para esta visita
                    pass

            # ===================================================
            # CASO ESPECIAL: REVISIÓN POR SISTEMAS (ID 4)
            # ===================================================
            elif int(examen_id) == 4 and isinstance(resultado, RevisionSistemasResult):
                # Obtener datos básicos del modelo principal
                datos_examen = model_to_dict(resultado)
                datos_examen.pop("id", None)
                datos_examen.pop("visita_examen", None)

                # Obtener los detalles de síntomas relacionados
                detalles = DetalleRevisionSistemas.objects.filter(
                    revision_sistemas_result=resultado
                ).order_by("sistema", "sintoma")

                # Organizar detalles por sistema para el template
                sistemas_detalles = {}
                for detalle in detalles:
                    if detalle.sistema not in sistemas_detalles:
                        sistemas_detalles[detalle.sistema] = []

                    sistemas_detalles[detalle.sistema].append(
                        {
                            "sintoma": detalle.sintoma,
                            "tiempo": detalle.tiempo,
                            "caracteristicas": detalle.caracteristicas,
                        }
                    )

                datos_examen["sistemas_detalles"] = sistemas_detalles

                modo_edicion = True

            # En la vista realizar_examen, agregar después de los otros casos especiales:

            # ===================================================
            # CASO ESPECIAL: EXAMEN NEUROLÓGICO (ID 5)
            # ===================================================
            elif int(examen_id) == 5 and isinstance(resultado, ExamenNeurologicoResult):
                # Obtener datos básicos del modelo
                datos_examen = model_to_dict(resultado)
                datos_examen.pop("id", None)
                datos_examen.pop("visita_examen", None)

                # Formatear campos None como cadenas vacías para el template
                for field_name, field_value in datos_examen.items():
                    if field_value is None:
                        datos_examen[field_name] = ""
                    elif isinstance(field_value, bool):
                        datos_examen[field_name] = field_value
                    elif hasattr(field_value, "strftime"):  # Es una fecha
                        datos_examen[field_name] = field_value.strftime("%Y-%m-%d")

                # Generar resumen para debug
                resumen = resultado.get_resumen_examen()
                alteraciones_pares = resultado.get_alteraciones_pares_craneales()
                alteraciones_sensibilidad = resultado.get_alteraciones_sensibilidad()
                reflejos_alterados = resultado.get_reflejos_alterados()

                modo_edicion = True

    except VisitaExamen.DoesNotExist:
        messages.error(request, "Visita-examen no encontrada")
        return redirect("detalle_paciente", paciente_id=paciente_id)
    # Asegurar que `datos_examen_json` esté disponible para la plantilla
    datos_examen_json = None
    # Si es el examen de Antecedentes (id 5), asegurar que incluya las relaciones
    if int(examen_id) == 5:
        try:
            if not datos_examen or not datos_examen.get("patologicos"):
                try:
                    antecedentes_result = None
                    try:
                        antecedentes_link = AntecedentesVisitaLink.objects.get(
                            visita_examen=visita_examen_obj
                        )
                        antecedentes_result = antecedentes_link.antecedentes_result
                    except AntecedentesVisitaLink.DoesNotExist:
                        antecedentes_result = AntecedentesResult.objects.filter(
                            paciente=paciente
                        ).first()

                    if not antecedentes_result:
                        raise AntecedentesVisitaLink.DoesNotExist()

                    antecedentes = AntecedentesResult.objects.prefetch_related(
                        "antecedentes_patologicos",
                        "antecedentes_quirurgicos",
                        "antecedentes_farmacologicos",
                        "antecedentes_toxicos",
                        "antecedentes_familiares",
                        "antecedentes_alergicos",
                        "antecedentes_traumaticos",
                        "antecedentes_gineco",
                        "antecedentes_epidemiologicos",
                        "antecedentes_ets",
                        "antecedentes_hospitalizaciones",
                        "antecedentes_inmunizaciones",
                        "antecedentes_transfusionales",
                    ).get(id=antecedentes_result.id)

                    datos_examen = datos_examen or {}
                    datos_examen["patologicos"] = list(
                        antecedentes.antecedentes_patologicos.values(
                            "tipo_patologia",
                            "descripcion_otros",
                            "fecha_inicio",
                            "ha_recibido_tratamiento",
                            "detalle_tratamiento",
                            "tiene_complicaciones",
                            "detalle_complicaciones",
                            "activo",
                            "fecha_finalizacion",
                            "observaciones",
                        )
                    )
                    datos_examen["quirurgicos"] = list(
                        antecedentes.antecedentes_quirurgicos.values(
                            "descripcion",
                            "fecha_intervencion",
                            "ha_recibido_tratamiento",
                            "detalle_tratamiento",
                            "tiene_complicaciones",
                            "detalle_complicaciones",
                            "activo",
                            "fecha_finalizacion",
                            "observaciones",
                        )
                    )
                    datos_examen["farmacologicos"] = list(
                        antecedentes.antecedentes_farmacologicos.values(
                            "id",
                            "nombre_comercial",
                            "nombre_generico",
                            "presentacion",
                            "concentracion",
                            "unidad",
                            "via_administracion",
                            "cantidad",
                            "frecuencia",
                            "fecha_inicio",
                            "fecha_finalizacion",
                            "indicacion",
                            "activo",
                            "adherencia",
                            "efectos_adversos",
                            "descripcion_efectos_adversos",
                            "observaciones",
                        )
                    )
                    datos_examen["toxicos"] = list(
                        antecedentes.antecedentes_toxicos.values(
                            "tipos_toxico",
                            "descripcion_otros",
                            "fecha_inicio",
                            "ha_recibido_tratamiento",
                            "detalle_tratamiento",
                            "tiene_complicaciones",
                            "detalle_complicaciones",
                            "activo",
                            "fecha_finalizacion",
                            "observaciones",
                        )
                    )
                    datos_examen["familiares"] = list(
                        antecedentes.antecedentes_familiares.values(
                            "tipo_antecedente",
                            "parentesco",
                            "observaciones",
                        )
                    )
                    datos_examen["alergicos"] = list(
                        antecedentes.antecedentes_alergicos.values(
                            "descripcion",
                            "fecha_inicio",
                            "tratamiento_recibido",
                            "detalle_tratamiento",
                            "complicaciones",
                            "activo",
                            "fecha_finalizacion",
                            "observaciones",
                        )
                    )
                    datos_examen["traumaticos"] = list(
                        antecedentes.antecedentes_traumaticos.values(
                            "descripcion",
                            "fecha_inicio",
                            "tratamiento_recibido",
                            "detalle_tratamiento",
                            "complicaciones",
                            "activo",
                            "fecha_finalizacion",
                            "observaciones",
                        )
                    )
                    if hasattr(antecedentes, "antecedentes_gineco") and antecedentes.antecedentes_gineco:
                        gineco_data = model_to_dict(antecedentes.antecedentes_gineco)
                        gineco_data.pop("id", None)
                        gineco_data.pop("antecedente_result", None)
                        datos_examen["gineco_obstetricos"] = gineco_data
                    else:
                        datos_examen["gineco_obstetricos"] = {}

                    datos_examen["epidemiologicos"] = list(
                        antecedentes.antecedentes_epidemiologicos.values(
                            "tipo_antecedente",
                            "fecha_inicio",
                            "tratamiento_detalle",
                            "complicaciones_asociadas",
                            "detallar_complicaciones",
                            "activo_actualmente",
                            "fecha_finalizacion",
                            "observaciones",
                        )
                    )
                    datos_examen["ets"] = list(
                        antecedentes.antecedentes_ets.values(
                            "tipo_ets",
                            "fecha_diagnostico",
                            "tratamiento_recibido",
                            "detalle_tratamiento",
                            "complicaciones",
                            "detalle_complicaciones",
                            "curado",
                            "fecha_curacion",
                            "observaciones",
                        )
                    )
                    datos_examen["hospitalizaciones"] = list(
                        antecedentes.antecedentes_hospitalizaciones.values(
                            "motivo_hospitalizacion",
                            "fecha_ingreso",
                            "fecha_egreso",
                            "dias_hospitalizacion",
                            "institucion",
                            "observaciones",
                        )
                    )
                    datos_examen["inmunizaciones"] = list(
                        antecedentes.antecedentes_inmunizaciones.values(
                            "nombre_vacuna",
                            "fecha_aplicacion",
                            "dosis_numero",
                            "observaciones",
                        )
                    )
                    # Mapear claves a las que espera el frontend/guardado
                    try:
                        mapped_inmunizaciones = []
                        for itm in datos_examen.get("inmunizaciones", []):
                            mapped_inmunizaciones.append({
                                "vacuna_inmunizacion": itm.get("nombre_vacuna"),
                                "fecha_ultima_dosis": itm.get("fecha_aplicacion"),
                                "numero_dosis": itm.get("dosis_numero"),
                                "observaciones": itm.get("observaciones", ""),
                            })
                        datos_examen["inmunizaciones"] = mapped_inmunizaciones
                    except Exception:
                        pass
                    datos_examen["transfusionales"] = list(
                        antecedentes.antecedentes_transfusionales.values(
                            "motivo_transfusion",
                            "fecha_transfusion",
                            "tipo_componente",
                            "cantidad_unidades",
                            "tuvo_reacciones",
                            "detalle_reacciones",
                            "observaciones",
                        )
                    )
                    # Mapear claves para transfusionales al formato esperado
                    try:
                        mapped_trans = []
                        for itm in datos_examen.get("transfusionales", []):
                            mapped_trans.append({
                                "motivo_transfusion": itm.get("motivo_transfusion"),
                                "fecha_ultima_transfusion": itm.get("fecha_transfusion"),
                                "tipo_componente": itm.get("tipo_componente"),
                                "numero_unidades": itm.get("cantidad_unidades"),
                                "tuvo_reacciones": itm.get("tuvo_reacciones", False),
                                "detalle_reacciones": itm.get("detalle_reacciones", ""),
                                "observaciones": itm.get("observaciones", ""),
                            })
                        datos_examen["transfusionales"] = mapped_trans
                    except Exception:
                        pass
                    modo_edicion = True
                except AntecedentesVisitaLink.DoesNotExist:
                    pass
        except Exception:
            pass
    if datos_examen:
        try:
            def _convert_dates(obj):
                if isinstance(obj, dict):
                    return {k: _convert_dates(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_convert_dates(i) for i in obj]
                if hasattr(obj, "strftime"):
                    try:
                        return obj.strftime("%Y-%m-%d")
                    except Exception:
                        return str(obj)
                return obj

            safe_obj = _convert_dates(datos_examen)
            datos_examen_json = json.dumps(safe_obj)
        except Exception as e:
            # Registrar en servidor para depuración
            try:
                import logging

                logging.getLogger(__name__).exception(
                    "Error serializando datos_examen: %s", str(e)
                )
            except Exception:
                pass
            datos_examen_json = None

    context = {
        "visita_examen": visita_id,
        "paciente_id": paciente_id,
        "examen_id": examen_id,
        "datos_examen": datos_examen,
        "datos_examen_json": datos_examen_json,
        "modo_edicion": modo_edicion,
        "visita_examen_obj": visita_examen_obj,
        "paciente": paciente,
        "visita": visita,
    }

    # Si es anamnesis de sueño, agregar datos adicionales
    if int(examen_id) == 10 and datos_examen and "tipos_queja" in datos_examen:
        context.update(
            {
                "tipos_queja": datos_examen["tipos_queja"],
                "sustancias": datos_examen["sustancias"],
                "medicamentos": datos_examen["medicamentos"],
                "pantallas": datos_examen["pantallas"],
                "actividades_en_cama": datos_examen["actividades_en_cama"],
                "actividades_fisicas": datos_examen["actividades_fisicas"],
                "sintomas_suenos": datos_examen["sintomas_suenos"],
                "sintomas_diurnos": datos_examen["sintomas_diurnos"],
            }
        )

    return render(request, config["template"], context)


@login_required
def ver_resultado_examen(request, visita_examen_id):
    visita_examen = get_object_or_404(VisitaExamen, id=visita_examen_id)

    if not visita_examen.esta_realizado:
        messages.error(request, "Este examen aún no ha sido completado.")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )

    br = builder_result_response(request, visita_examen)
    if br is not None:
        return br

    from ..services.exam_view_context import get_context_ver_examen

    try:
        template_name, context = get_context_ver_examen(visita_examen)
        return render(request, template_name, context)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )
    except Exception as e:
        messages.error(request, f"Error al cargar el examen: {str(e)}")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )



@login_required
def guardar_examen_cognitivo_anamnesis(request):
    """Vista para guardar el examen cognitivo anamnesis usando CognitivoAnamnesisForm."""
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

            form = CognitivoAnamnesisForm(request.POST)
            if form.is_valid():
                cognitivo_anamnesis, created = (
                    CognitivoAnamnesisResult.objects.update_or_create(
                        visita_examen=visita_examen,
                        defaults=form.cleaned_data,
                    )
                )

                # ==============================
                # Procesar relaciones hijas
                # ==============================
                cognitivo_anamnesis.actitudes.all().delete()
                cognitivo_anamnesis.atenciones.all().delete()
                cognitivo_anamnesis.errores_lenguaje.all().delete()
                cognitivo_anamnesis.actividades_vida_diaria.all().delete()
                cognitivo_anamnesis.actividades_complejas.all().delete()

                # Procesar actitudes
                for actitud in request.POST.getlist("actitud_tipo[]"):
                    if actitud:
                        ActitudCognitiva.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=actitud
                        )

                # Procesar problemas de atención
                atencion_tipos = request.POST.getlist("atencion_tipo[]")
                atencion_edades = request.POST.getlist("atencion_edad_inicio[]")
                atencion_caracteristicas = request.POST.getlist(
                    "atencion_caracteristicas[]"
                )
                for i, tipo in enumerate(atencion_tipos):
                    if tipo:
                        AtencionCognitiva.objects.create(
                            anamnesis=cognitivo_anamnesis,
                            tipo=tipo,
                            edad_inicio=atencion_edades[i]
                            if i < len(atencion_edades)
                            else "",
                            caracteristicas=atencion_caracteristicas[i]
                            if i < len(atencion_caracteristicas)
                            else "",
                        )

                # Procesar errores de lenguaje
                for error in request.POST.getlist("error_lenguaje[]"):
                    if error:
                        ErrorLenguajeCognitivo.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=error
                        )

                # Procesar actividades de vida diaria
                for actividad in request.POST.getlist("actividad_vida_diaria[]"):
                    if actividad:
                        ActividadVidaDiaria.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=actividad
                        )

                # Procesar actividades complejas
                for actividad in request.POST.getlist("actividad_compleja[]"):
                    if actividad:
                        ActividadCompleja.objects.create(
                            anamnesis=cognitivo_anamnesis, tipo=actividad
                        )

                visita_examen.estado = "completado"
                visita_examen.fecha_completado = timezone.now()
                visita_examen.save()

                messages.success(
                    request,
                    "✅ Examen Cognitivo Anamnesis guardado exitosamente.",
                )
                return redirect("detalle_paciente", paciente_id=paciente_id)
            else:
                error_msgs = "; ".join(
                    f"{field}: {', '.join(errs)}"
                    for field, errs in list(form.errors.items())[:5]
                )
                messages.error(
                    request,
                    f"❌ Error de validación en cognitivo anamnesis: {error_msgs}",
                )
                return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except Exception:
                pass

            messages.error(
                request, f"❌ Error al guardar el examen cognitivo: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


# Función auxiliar para enteros opcionales
def safe_int_optional(value):
    """Convierte a int o retorna None si no hay valor"""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


