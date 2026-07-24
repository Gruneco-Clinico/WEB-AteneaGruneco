# -*- encoding: utf-8 -*-
"""
Contexto de precarga para editar exámenes legacy (B-11).

Centraliza el armado de ``datos_examen`` (campos + relaciones hijas) para que
``realizar_examen`` no dependa de ramas muertas / fallbacks frágiles.
"""
from __future__ import annotations

import json
from datetime import date, datetime

from django.forms.models import model_to_dict

from apps.home.models import (
    AnalisisGeneralResult,
    AntecedentesResult,
    AntecedentesVisitaLink,
    CognitivoAnamnesisResult,
    DetalleRevisionSistemas,
    ExamenFisicoResult,
    ExamenNeurologicoResult,
    MedicamentosResult,
    RevisionSistemasResult,
    SuenoAnamnesisResult,
)


def _convert_dates(obj):
    if isinstance(obj, dict):
        return {k: _convert_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_dates(i) for i in obj]
    if isinstance(obj, (datetime, date)):
        return obj.strftime("%Y-%m-%d")
    return obj


def _base_dict(resultado, drop_keys=("id", "visita_examen", "paciente")):
    datos = model_to_dict(resultado)
    for key in drop_keys:
        datos.pop(key, None)
    # Normalizar None → "" para inputs de texto en templates
    for field_name, field_value in list(datos.items()):
        if field_value is None:
            datos[field_name] = ""
    return datos


def load_antecedentes_datos(visita_examen, paciente):
    """Carga AntecedentesResult + hijos vía AntecedentesVisitaLink."""
    antecedentes_result = None
    try:
        link = AntecedentesVisitaLink.objects.select_related(
            "antecedentes_result"
        ).get(visita_examen=visita_examen)
        antecedentes_result = link.antecedentes_result
    except AntecedentesVisitaLink.DoesNotExist:
        antecedentes_result = AntecedentesResult.objects.filter(
            paciente=paciente
        ).first()

    if not antecedentes_result:
        return None

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

    datos = _base_dict(antecedentes, drop_keys=("id", "paciente", "ultima_visita_examen"))

    datos["patologicos"] = list(
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
    datos["quirurgicos"] = list(
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
    datos["farmacologicos"] = list(
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
    datos["toxicos"] = list(
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
    datos["familiares"] = list(
        antecedentes.antecedentes_familiares.values(
            "tipo_antecedente", "parentesco", "observaciones"
        )
    )
    datos["alergicos"] = list(
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
    datos["traumaticos"] = list(
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
        gineco = model_to_dict(antecedentes.antecedentes_gineco)
        gineco.pop("id", None)
        gineco.pop("antecedente_result", None)
        datos["gineco_obstetricos"] = gineco
    else:
        datos["gineco_obstetricos"] = {}

    datos["epidemiologicos"] = list(
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
    # Alias para el formulario de captura (name=...[descripcion])
    for row in datos["epidemiologicos"]:
        row["descripcion"] = row.get("tipo_antecedente") or ""

    datos["ets"] = list(
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
    for row in datos["ets"]:
        row["descripcion"] = row.get("tipo_ets") or ""
        row["fecha_inicio"] = row.get("fecha_diagnostico")
    datos["hospitalizaciones"] = list(
        antecedentes.antecedentes_hospitalizaciones.values(
            "motivo_hospitalizacion",
            "fecha_ingreso",
            "fecha_egreso",
            "dias_hospitalizacion",
            "institucion",
            "observaciones",
        )
    )
    datos["inmunizaciones"] = [
        {
            "vacuna_inmunizacion": itm.get("nombre_vacuna"),
            "fecha_ultima_dosis": itm.get("fecha_aplicacion"),
            "numero_dosis": itm.get("dosis_numero"),
            "observaciones": itm.get("observaciones", ""),
        }
        for itm in antecedentes.antecedentes_inmunizaciones.values(
            "nombre_vacuna", "fecha_aplicacion", "dosis_numero", "observaciones"
        )
    ]
    datos["transfusionales"] = [
        {
            "motivo_transfusion": itm.get("motivo_transfusion"),
            "fecha_ultima_transfusion": itm.get("fecha_transfusion"),
            "tipo_componente": itm.get("tipo_componente"),
            "numero_unidades": itm.get("cantidad_unidades"),
            "tuvo_reacciones": itm.get("tuvo_reacciones", False),
            "detalle_reacciones": itm.get("detalle_reacciones", ""),
            "observaciones": itm.get("observaciones", ""),
        }
        for itm in antecedentes.antecedentes_transfusionales.values(
            "motivo_transfusion",
            "fecha_transfusion",
            "tipo_componente",
            "cantidad_unidades",
            "tuvo_reacciones",
            "detalle_reacciones",
            "observaciones",
        )
    ]
    return datos


def load_sueno_anamnesis_datos(resultado: SuenoAnamnesisResult):
    datos = _base_dict(resultado)
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

    datos["sustancias"] = list(
        anamnesis.sustancias.values(
            "tipo", "cantidad", "frecuencia", "tiempo", "observaciones"
        )
    )
    datos["medicamentos"] = list(
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
    datos["pantallas"] = list(
        anamnesis.pantallas.values("tipo", "frecuencia", "tiempo_antes_dormir")
    )
    datos["actividades_en_cama"] = list(
        anamnesis.actividades_en_cama.values("tipo", "frecuencia", "observaciones")
    )
    datos["actividades_fisicas"] = list(
        anamnesis.actividades_fisicas.values(
            "tipo", "otro_texto", "intensidad", "frecuencia", "observaciones"
        )
    )
    datos["sintomas_suenos"] = list(
        anamnesis.sintomas_suenos.values(
            "tipo", "cuando_inicio", "evolucion", "frecuencia", "gravedad", "observaciones"
        )
    )
    datos["sintomas_diurnos"] = list(
        anamnesis.sintomas_diurno.values(
            "tipo", "cuando_inicio", "evolucion", "frecuencia", "gravedad", "observaciones"
        )
    )
    datos["tipos_queja"] = list(
        anamnesis.tipos_queja_detalle.values(
            "nombre", "inicio", "evolucion", "frecuencia", "gravedad"
        )
    )
    return datos


def load_analisis_general_datos(resultado: AnalisisGeneralResult):
    datos = _base_dict(resultado)
    analisis = AnalisisGeneralResult.objects.prefetch_related(
        "diagnosticos_cie10",
        "diagnosticos_dsmv",
        "diagnosticos_no_clasificados",
    ).get(id=resultado.id)

    diag_fields = (
        "codigo",
        "diagnostico",
        "confirmado_nuevo",
        "confirmado_antiguo",
        "en_estudio",
        "orden",
    )
    datos["diagnosticos_cie10"] = list(analisis.diagnosticos_cie10.values(*diag_fields))
    datos["diagnosticos_dsmv"] = list(analisis.diagnosticos_dsmv.values(*diag_fields))
    datos["diagnosticos_no_clasificados"] = list(
        analisis.diagnosticos_no_clasificados.values(
            "diagnostico",
            "confirmado_nuevo",
            "confirmado_antiguo",
            "en_estudio",
            "orden",
        )
    )
    return datos


def load_revision_sistemas_datos(resultado: RevisionSistemasResult):
    datos = _base_dict(resultado)
    detalles = DetalleRevisionSistemas.objects.filter(
        revision_sistemas_result=resultado
    ).order_by("sistema", "sintoma")
    sistemas_detalles = {}
    for detalle in detalles:
        sistemas_detalles.setdefault(detalle.sistema, []).append(
            {
                "sintoma": detalle.sintoma,
                "tiempo": detalle.tiempo,
                "caracteristicas": detalle.caracteristicas,
            }
        )
    datos["sistemas_detalles"] = sistemas_detalles
    return datos


def load_medicamentos_datos(resultado: MedicamentosResult):
    datos = _base_dict(resultado)
    meds = MedicamentosResult.objects.prefetch_related("medicamentos").get(
        id=resultado.id
    )
    datos["medicamentos"] = list(
        meds.medicamentos.values(
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
    return datos


# Prefijos HTML de atención (checkbox value → name de edad/características).
_ATENCION_PREFIX_BY_TIPO = {
    "Quejas atencionales": "quejas",
    "Alteración atención sostenida": "sostenida",
    "Alteración atención dividida": "dividida",
    "Incapacidad para quedarse quieto": "quieto",
    "Dificultad para finalizar una tarea": "tarea",
    "Dificultad para seguir instrucciones": "instrucciones",
    "Distracción con estímulos irrelevantes": "distraccion",
}


def load_cognitivo_anamnesis_datos(resultado: CognitivoAnamnesisResult):
    datos = _base_dict(resultado)
    anamnesis = CognitivoAnamnesisResult.objects.prefetch_related(
        "actitudes",
        "atenciones",
        "errores_lenguaje",
        "actividades_vida_diaria",
        "actividades_complejas",
    ).get(id=resultado.id)
    datos["actitudes"] = list(anamnesis.actitudes.values("tipo"))
    datos["atenciones"] = list(
        anamnesis.atenciones.values("tipo", "edad_inicio", "caracteristicas")
    )
    datos["errores_lenguaje"] = list(anamnesis.errores_lenguaje.values("tipo"))
    datos["actividades_vida_diaria"] = list(
        anamnesis.actividades_vida_diaria.values("tipo")
    )
    datos["actividades_complejas"] = list(
        anamnesis.actividades_complejas.values("tipo")
    )
    # Claves planas para precarga en template/JS (B-11 cognitivo).
    datos["actitudes_tipos"] = [row["tipo"] for row in datos["actitudes"]]
    datos["errores_lenguaje_tipos"] = [
        row["tipo"] for row in datos["errores_lenguaje"]
    ]
    datos["actividades_vida_diaria_tipos"] = [
        row["tipo"] for row in datos["actividades_vida_diaria"]
    ]
    datos["actividades_complejas_tipos"] = [
        row["tipo"] for row in datos["actividades_complejas"]
    ]
    atencion_map = {}
    for row in datos["atenciones"]:
        tipo = row["tipo"]
        prefix = _ATENCION_PREFIX_BY_TIPO.get(tipo)
        atencion_map[tipo] = {
            "edad_inicio": row.get("edad_inicio") or "",
            "caracteristicas": row.get("caracteristicas") or "",
            "prefix": prefix or "",
        }
    datos["atencion_map"] = atencion_map
    datos["atencion_tipos"] = list(atencion_map.keys())
    return datos


def build_datos_examen_edicion(visita_examen, paciente, examen_id, exam_model):
    """
    Devuelve (datos_examen, modo_edicion, extra_context).

    ``extra_context`` puede traer claves adicionales para el template (p. ej. sueño).
    """
    examen_id = int(examen_id)
    extra = {}

    # Antecedentes: puente especial (no hereda ResultadoExamenBase)
    if examen_id == 5:
        datos = load_antecedentes_datos(visita_examen, paciente)
        return (datos, bool(datos), extra)

    # Físico (3) y neurológico (9): defaults de toggles + secciones evaluadas
    if (
        not visita_examen.esta_realizado
        and examen_id in (3, 9)
        and exam_model
    ):
        from apps.home.models.field_toggle_semantics import default_datos_toggles

        datos = default_datos_toggles(exam_model)
        for field in exam_model._meta.fields:
            if field.name.startswith("seccion_") and field.name.endswith("_evaluado"):
                datos[field.name] = True
        return (datos, False, extra)

    if not exam_model or not visita_examen.esta_realizado:
        return (None, False, extra)

    resultado = visita_examen.get_resultado_instance()
    if not resultado or not isinstance(resultado, exam_model):
        return (None, False, extra)

    if examen_id == 10 and isinstance(resultado, SuenoAnamnesisResult):
        datos = load_sueno_anamnesis_datos(resultado)
        extra.update(
            {
                "tipos_queja": datos["tipos_queja"],
                "sustancias": datos["sustancias"],
                "medicamentos": datos["medicamentos"],
                "pantallas": datos["pantallas"],
                "actividades_en_cama": datos["actividades_en_cama"],
                "actividades_fisicas": datos["actividades_fisicas"],
                "sintomas_suenos": datos["sintomas_suenos"],
                "sintomas_diurnos": datos["sintomas_diurnos"],
            }
        )
        return (datos, True, extra)

    if examen_id == 7 and isinstance(resultado, AnalisisGeneralResult):
        return (load_analisis_general_datos(resultado), True, extra)

    if examen_id == 4 and isinstance(resultado, RevisionSistemasResult):
        return (load_revision_sistemas_datos(resultado), True, extra)

    if examen_id == 8 and isinstance(resultado, MedicamentosResult):
        datos = load_medicamentos_datos(resultado)
        # La plantilla espera ``datos_medicamentos`` (JSON), no solo datos_examen.
        try:
            extra["datos_medicamentos"] = json.dumps(
                _convert_dates(datos.get("medicamentos") or []), default=str
            )
        except Exception:
            extra["datos_medicamentos"] = "[]"
        return (datos, True, extra)

    if examen_id == 20 and isinstance(resultado, CognitivoAnamnesisResult):
        return (load_cognitivo_anamnesis_datos(resultado), True, extra)

    # Físico (3), neurológico (9) y resto de modelos planos
    return (_base_dict(resultado), True, extra)


def serialize_datos_examen(datos_examen):
    if not datos_examen:
        return None
    try:
        return json.dumps(_convert_dates(datos_examen), default=str)
    except Exception:
        return None
